from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.job_mela_repository import JobMelaRepository
from app.schemas.job_mela import (
    JobMelaRead,
    RecruiterJobMelaItem,
    JobMelaParticipationRequest,
    JobMelaParticipationResponse,
    AdminParticipationItem,
    AdminApproveParticipationRequest,
    AdminRejectParticipationRequest,
    CandidateMelaCompanyItem,
)


class JobMelaService:
    """
    Business logic for Job Melas and Recruiter/Admin Participation workflows.
    """

    @classmethod
    async def get_recruiter_job_melas(
        cls,
        db: AsyncSession,
        current_user: User,
        status_filter: Optional[str] = "ALL",
        search: Optional[str] = None,
    ) -> List[RecruiterJobMelaItem]:
        """
        Retrieve all Job Melas with participation context for the authenticated recruiter.
        """
        profile = await JobMelaRepository.get_recruiter_profile_by_user_id(db, current_user.id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recruiter profile not found. Please complete company registration.",
            )

        events_data = await JobMelaRepository.get_recruiter_job_melas(
            db=db,
            recruiter_id=profile.id,
            status_filter=status_filter,
            search=search,
        )

        return [RecruiterJobMelaItem(**item) for item in events_data]

    @classmethod
    async def get_available_melas(cls, db: AsyncSession) -> List[JobMelaRead]:
        """
        Retrieve all active / published Job Melas for dropdown selection.
        """
        melas = await JobMelaRepository.get_all_published_melas(db)
        return [JobMelaRead.model_validate(m) for m in melas]

    @classmethod
    async def register_company_participation(
        cls,
        db: AsyncSession,
        current_user: User,
        payload: JobMelaParticipationRequest,
    ) -> JobMelaParticipationResponse:
        """
        Recruiter submits a company participation request for a Job Mela.
        Status is created strictly as PENDING awaiting administrative review.
        """
        profile = await JobMelaRepository.get_recruiter_profile_by_user_id(db, current_user.id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recruiter profile not found. Please complete company registration.",
            )

        # 1. Resolve target Job Mela by ID or Title
        target_mela = await JobMelaRepository.get_job_mela_by_id_or_title(
            db, mela_id=payload.job_mela_id, title=payload.title
        )
        if not target_mela:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job Mela event '{payload.job_mela_id or payload.title}' not found.",
            )

        # 2. Check for duplicate registration
        existing = await JobMelaRepository.get_participation(
            db, job_mela_id=target_mela.id, company_id=profile.id
        )
        if existing:
            if existing.status == "PENDING":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="A participation request for this Job Mela has already been submitted and is currently pending administrator approval.",
                )
            elif existing.status == "APPROVED":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Your company is already registered and approved for this Job Mela event.",
                )
            elif existing.status == "REJECTED":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Previous participation request was rejected: {existing.rejection_reason or 'Contact administrator'}.",
                )

        # 3. Create participation record with PENDING status
        openings_text = (payload.openings or payload.positions or "").strip()
        hires_count = payload.target_hires or payload.expectedHires or payload.expected_hires or 1

        participation = await JobMelaRepository.create_participation(
            db=db,
            job_mela_id=target_mela.id,
            company_id=profile.id,
            openings=openings_text,
            target_hires=hires_count,
        )

        return JobMelaParticipationResponse(
            id=participation.id,
            job_mela_id=target_mela.id,
            mela_title=target_mela.title,
            company_id=profile.id,
            company_name=profile.company_name,
            openings=openings_text,
            target_hires=hires_count,
            status=participation.status,
            booth_number=participation.booth_number,
            registered_at=participation.registered_at.strftime("%Y-%m-%d %H:%M:%S"),
            message="Participation request submitted successfully and is pending administrative review.",
        )

    @classmethod
    async def get_admin_participations(
        cls,
        db: AsyncSession,
        status_filter: Optional[str] = "ALL",
        search: Optional[str] = None,
    ) -> List[AdminParticipationItem]:
        """
        Admin reviews all company participation requests across Job Melas.
        """
        rows = await JobMelaRepository.get_admin_participations(
            db=db, status_filter=status_filter, search=search
        )
        return [AdminParticipationItem(**r) for r in rows]

    @classmethod
    async def approve_participation(
        cls,
        db: AsyncSession,
        participation_id: str,
        current_admin: User,
        payload: Optional[AdminApproveParticipationRequest] = None,
    ) -> Dict[str, Any]:
        """
        Administrator approves a company participation and assigns a corporate booth/stall.
        """
        part = await JobMelaRepository.get_participation_by_id(db, participation_id)
        if not part:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job Mela participation request not found.",
            )

        now = datetime.now(timezone.utc)
        stall = (payload.booth_number if payload and payload.booth_number else None) or f"Booth S-{part.id[-4:].upper()} (Hall 2)"
        location = (payload.booth_location if payload and payload.booth_location else None) or "Corporate Enclosure"

        part.status = "APPROVED"
        part.approved_at = now
        part.approved_by = current_admin.email
        part.booth_number = stall
        part.booth_location = location
        part.updated_at = now

        await db.commit()
        await db.refresh(part)

        return {
            "success": True,
            "message": f"Participation approved. Allocated {stall}.",
            "participation_id": part.id,
            "status": part.status,
            "booth_number": part.booth_number,
        }

    @classmethod
    async def reject_participation(
        cls,
        db: AsyncSession,
        participation_id: str,
        current_admin: User,
        payload: AdminRejectParticipationRequest,
    ) -> Dict[str, Any]:
        """
        Administrator rejects a company participation with mandatory reason.
        """
        part = await JobMelaRepository.get_participation_by_id(db, participation_id)
        if not part:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job Mela participation request not found.",
            )

        now = datetime.now(timezone.utc)
        part.status = "REJECTED"
        part.rejected_at = now
        part.rejected_by = current_admin.email
        part.rejection_reason = payload.rejection_reason
        part.updated_at = now

        await db.commit()
        await db.refresh(part)

        return {
            "success": True,
            "message": "Participation request rejected.",
            "participation_id": part.id,
            "status": part.status,
            "rejection_reason": part.rejection_reason,
        }

    @classmethod
    async def get_approved_mela_companies(
        cls, db: AsyncSession, job_mela_id: str
    ) -> List[CandidateMelaCompanyItem]:
        """
        Approved companies participating in a Job Mela (for candidate experience).
        """
        companies = await JobMelaRepository.get_approved_companies_for_mela(db, job_mela_id)
        return [CandidateMelaCompanyItem(**c) for c in companies]
