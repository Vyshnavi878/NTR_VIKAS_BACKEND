import re
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Tuple
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select, func, and_

from app.models.user import User
from app.models.internship import Internship
from app.repositories.internship_repository import InternshipRepository
from app.schemas.internship import (
    InternshipCreate,
    InternshipRead,
    PaginatedInternshipResponse,
    AdminInternshipDetail,
)


class InternshipService:
    """
    Business service layer for recruiter internships, governance approvals, and candidate views.
    """

    @staticmethod
    def _parse_stipend(stipend_val: Optional[Any], stipend_str: Optional[str]) -> Tuple[int, str]:
        """Normalize numeric stipend and display label."""
        if stipend_val and isinstance(stipend_val, (int, float)):
            amount = int(stipend_val)
            label = stipend_str or f"₹{amount:,} / month"
            return amount, label

        if stipend_str:
            clean = re.sub(r"[^\d]", "", str(stipend_str))
            if clean:
                amount = int(clean)
                return amount, stipend_str.strip()

        return 15000, "₹15,000 / month"

    @classmethod
    async def create_internship(
        cls,
        db: AsyncSession,
        current_user: User,
        payload: InternshipCreate,
        initial_status: str = "PENDING",
    ) -> InternshipRead:
        """
        Recruiter creates a new internship opportunity.
        Sets status strictly to PENDING (or DRAFT if explicitly requested).
        """
        # 1. Recruiter Profile check
        profile = await InternshipRepository.get_recruiter_profile_by_user_id(db, current_user.id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recruiter profile not found. Please complete company registration.",
            )

        # 2. Field validations
        title = payload.title.strip()
        if len(title) < 3:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Internship title must be at least 3 characters long.",
            )

        stipend_monthly, stipend_label = cls._parse_stipend(
            payload.stipend_monthly, payload.stipend
        )
        if stipend_monthly < 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Stipend amount cannot be negative.",
            )

        duration = payload.duration or "6 Months"
        work_mode = payload.work_mode or payload.workMode or "Hybrid"
        location = payload.location or "Bengaluru, Karnataka"
        interns_count = payload.number_of_interns or payload.openings or 1
        description = (payload.description or "").strip()

        # 3. Create internship in database
        internship = await InternshipRepository.create_internship(
            db=db,
            company_id=profile.id,
            created_by=current_user.id,
            title=title,
            stipend_monthly=stipend_monthly,
            stipend=stipend_label,
            duration=duration,
            work_mode=work_mode,
            location=location,
            number_of_interns=interns_count,
            description=description,
            status=initial_status,
        )

        # 4. Audit Log
        action_name = "INTERNSHIP_CREATED" if initial_status == "DRAFT" else "INTERNSHIP_SUBMITTED_FOR_APPROVAL"
        await InternshipRepository.create_audit_log(
            db=db,
            actor=current_user.email,
            action=action_name,
            entity="INTERNSHIP",
            entity_id=internship.id,
            metadata_json={
                "internship_number": internship.internship_number,
                "title": internship.title,
                "status": internship.status,
            },
        )

        return InternshipRead(
            id=internship.id,
            internship_number=internship.internship_number,
            company_id=profile.id,
            company_name=profile.company_name,
            title=internship.title,
            stipend_monthly=internship.stipend_monthly,
            stipend=internship.stipend,
            duration=internship.duration,
            work_mode=internship.work_mode,
            workMode=internship.work_mode,
            location=internship.location,
            number_of_interns=internship.number_of_interns,
            openings=internship.number_of_interns,
            description=internship.description,
            status=internship.status,
            applicantsCount=0,
            candidate_count=0,
            candidates_count=0,
            postedOn=internship.created_at.strftime("%Y-%m-%d"),
            created_at=internship.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            updated_at=internship.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
        )

    @classmethod
    async def get_recruiter_internships(
        cls,
        db: AsyncSession,
        current_user: User,
        status_filter: Optional[str] = "ALL",
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> PaginatedInternshipResponse:
        """Fetch paginated internships for the authenticated recruiter's company."""
        profile = await InternshipRepository.get_recruiter_profile_by_user_id(db, current_user.id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recruiter profile not found. Please complete company registration.",
            )

        items_dict, total = await InternshipRepository.get_recruiter_internships(
            db=db,
            company_id=profile.id,
            status_filter=status_filter,
            search=search,
            page=page,
            page_size=page_size,
        )

        total_pages = (total + page_size - 1) // page_size if total > 0 else 1

        return PaginatedInternshipResponse(
            items=[InternshipRead(**item) for item in items_dict],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    @classmethod
    async def close_internship(
        cls,
        db: AsyncSession,
        current_user: User,
        internship_id: str,
    ) -> InternshipRead:
        """Recruiter or Admin closes an active published internship."""
        internship = await InternshipRepository.get_internship_by_id(db, internship_id)
        if not internship:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Internship not found.",
            )

        # Enforce recruiter ownership unless admin
        if current_user.role.upper() != "ADMIN":
            profile = await InternshipRepository.get_recruiter_profile_by_user_id(db, current_user.id)
            if not profile or internship.company_id != profile.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You do not have permission to close this internship.",
                )

        now = datetime.now(timezone.utc)
        internship.status = "CLOSED"
        internship.closed_at = now
        internship.updated_at = now
        await db.commit()
        await db.refresh(internship)

        await InternshipRepository.create_audit_log(
            db=db,
            actor=current_user.email,
            action="INTERNSHIP_CLOSED",
            entity="INTERNSHIP",
            entity_id=internship.id,
            metadata_json={"internship_number": internship.internship_number},
        )

        app_count = await InternshipRepository.get_applicant_count_for_internship(
            db, internship.id, internship.internship_number
        )

        return InternshipRead(
            id=internship.id,
            internship_number=internship.internship_number,
            company_id=internship.company_id,
            company_name=internship.company.company_name if internship.company else None,
            title=internship.title,
            stipend_monthly=internship.stipend_monthly,
            stipend=internship.stipend,
            duration=internship.duration,
            work_mode=internship.work_mode,
            workMode=internship.work_mode,
            location=internship.location,
            number_of_interns=internship.number_of_interns,
            openings=internship.number_of_interns,
            description=internship.description,
            status=internship.status,
            applicantsCount=app_count,
            candidate_count=app_count,
            candidates_count=app_count,
            closed_at=internship.closed_at.strftime("%Y-%m-%d %H:%M:%S") if internship.closed_at else None,
            postedOn=internship.created_at.strftime("%Y-%m-%d") if internship.created_at else None,
            created_at=internship.created_at.strftime("%Y-%m-%d %H:%M:%S") if internship.created_at else None,
            updated_at=internship.updated_at.strftime("%Y-%m-%d %H:%M:%S") if internship.updated_at else None,
        )

    # ── Admin Governance ──────────────────────────────────────────────────────────

    @classmethod
    async def get_admin_internships(
        cls,
        db: AsyncSession,
        status_filter: Optional[str] = "ALL",
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> Dict[str, Any]:
        """Fetch all company internships for Administrator review."""
        items_dict, total = await InternshipRepository.get_admin_internships(
            db=db,
            status_filter=status_filter,
            search=search,
            page=page,
            page_size=page_size,
        )
        total_pages = (total + page_size - 1) // page_size if total > 0 else 1
        return {
            "items": [AdminInternshipDetail(**item) for item in items_dict],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }

    @classmethod
    async def get_admin_internship_detail(
        cls, db: AsyncSession, internship_id: str
    ) -> AdminInternshipDetail:
        """Fetch full details of an internship for administrator."""
        internship = await InternshipRepository.get_internship_by_id(db, internship_id)
        if not internship:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Internship not found.",
            )

        app_count = await InternshipRepository.get_applicant_count_for_internship(
            db, internship.id, internship.internship_number
        )
        rec = internship.company

        return AdminInternshipDetail(
            id=internship.id,
            internship_number=internship.internship_number,
            title=internship.title,
            company_id=internship.company_id,
            company_name=rec.company_name if rec else "N/A",
            company=rec.company_name if rec else "N/A",
            recruiter_name=rec.recruiter_name if rec else None,
            recruiter=rec.recruiter_name if rec else None,
            recruiter_email=rec.work_email if rec else None,
            recruiter_phone=rec.mobile_phone if rec else None,
            stipend_monthly=internship.stipend_monthly,
            stipend=internship.stipend or f"₹{internship.stipend_monthly:,} / month",
            duration=internship.duration,
            work_mode=internship.work_mode,
            location=internship.location,
            number_of_interns=internship.number_of_interns,
            description=internship.description,
            status=internship.status,
            applicants_count=app_count,
            rejection_reason=internship.rejection_reason,
            approved_by=internship.approved_by,
            approved_at=internship.approved_at.strftime("%Y-%m-%d %H:%M:%S") if internship.approved_at else None,
            published_at=internship.published_at.strftime("%Y-%m-%d %H:%M:%S") if internship.published_at else None,
            created_at=internship.created_at.strftime("%Y-%m-%d %H:%M:%S") if internship.created_at else "",
        )

    @classmethod
    async def approve_internship(
        cls,
        db: AsyncSession,
        current_admin: User,
        internship_id: str,
    ) -> Dict[str, Any]:
        """Admin approves an internship: PENDING -> PUBLISHED."""
        internship = await InternshipRepository.get_internship_by_id(db, internship_id)
        if not internship:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Internship not found.",
            )

        now = datetime.now(timezone.utc)
        internship.status = "PUBLISHED"
        internship.published_at = now
        internship.approved_by = current_admin.email
        internship.approved_at = now
        internship.updated_at = now

        await db.commit()
        await db.refresh(internship)

        await InternshipRepository.create_audit_log(
            db=db,
            actor=current_admin.email,
            action="INTERNSHIP_APPROVED",
            entity="INTERNSHIP",
            entity_id=internship.id,
            metadata_json={"internship_number": internship.internship_number},
        )

        return {
            "id": internship.id,
            "internship_number": internship.internship_number,
            "status": "PUBLISHED",
            "published_at": internship.published_at.strftime("%Y-%m-%d %H:%M:%S"),
            "message": f"Internship '{internship.title}' has been approved and published successfully.",
        }

    @classmethod
    async def reject_internship(
        cls,
        db: AsyncSession,
        current_admin: User,
        internship_id: str,
        reason: str,
    ) -> Dict[str, Any]:
        """Admin rejects an internship with mandatory reason."""
        internship = await InternshipRepository.get_internship_by_id(db, internship_id)
        if not internship:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Internship not found.",
            )

        now = datetime.now(timezone.utc)
        internship.status = "REJECTED"
        internship.rejection_reason = reason.strip()
        internship.rejected_by = current_admin.email
        internship.rejected_at = now
        internship.updated_at = now

        await db.commit()
        await db.refresh(internship)

        await InternshipRepository.create_audit_log(
            db=db,
            actor=current_admin.email,
            action="INTERNSHIP_REJECTED",
            entity="INTERNSHIP",
            entity_id=internship.id,
            metadata_json={"internship_number": internship.internship_number, "reason": reason.strip()},
        )

        return {
            "id": internship.id,
            "internship_number": internship.internship_number,
            "status": "REJECTED",
            "rejection_reason": internship.rejection_reason,
            "message": f"Internship '{internship.title}' has been rejected.",
        }

    # ── Candidate Portal ──────────────────────────────────────────────────────────

    @classmethod
    async def get_published_internships(
        cls,
        db: AsyncSession,
        search: Optional[str] = None,
        location: Optional[str] = None,
        work_mode: Optional[str] = None,
        duration: Optional[str] = None,
        stipend_min: Optional[int] = None,
        stipend_max: Optional[int] = None,
        company_id: Optional[str] = None,
        sort: Optional[str] = "latest",
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedInternshipResponse:
        """
        Candidate / public API. ONLY returns internships with status = PUBLISHED.
        Strictly excludes PENDING, DRAFT, and REJECTED internships.
        Supports: search, location, work_mode, duration, stipend range, company_id, sort, pagination.
        """
        from sqlalchemy import and_, or_, func, select

        conds = [
            Internship.status == "PUBLISHED",
            Internship.closed_at.is_(None),  # Exclude closed internships
        ]

        # Full-text search across title, description, internship number, company name
        if search and search.strip():
            q = f"%{search.strip()}%"
            conds.append(
                or_(
                    Internship.title.ilike(q),
                    Internship.internship_number.ilike(q),
                    Internship.description.ilike(q),
                    Internship.location.ilike(q),
                )
            )

        # Location filter
        if location and location.strip() and location.upper() not in ("ALL", "ALL LOCATIONS"):
            conds.append(Internship.location.ilike(f"%{location.strip()}%"))

        # Work mode filter
        if work_mode and work_mode.strip() and work_mode.upper() not in ("ALL", "ALL MODES"):
            conds.append(Internship.work_mode.ilike(f"%{work_mode.strip()}%"))

        # Duration filter — partial match (e.g. "3 Months" matches "3 Months")
        if duration and duration.strip() and duration.upper() not in ("ALL", "ALL DURATIONS"):
            conds.append(Internship.duration.ilike(f"%{duration.strip()}%"))

        # Stipend range filters (numeric monthly stipend)
        if stipend_min is not None and stipend_min > 0:
            conds.append(Internship.stipend_monthly >= stipend_min)
        if stipend_max is not None and stipend_max > 0:
            conds.append(Internship.stipend_monthly <= stipend_max)

        # Company filter
        if company_id and company_id.strip():
            conds.append(Internship.company_id == company_id.strip())

        filter_clause = and_(*conds)

        count_stmt = select(func.count(Internship.id)).where(filter_clause)
        total = (await db.execute(count_stmt)).scalar() or 0

        # Sort ordering
        sort_key = (sort or "latest").lower()
        if sort_key in ("stipend_high", "stipendhigh"):
            order_col = Internship.stipend_monthly.desc()
        elif sort_key in ("stipend_low", "stipendlow"):
            order_col = Internship.stipend_monthly.asc()
        elif sort_key == "oldest":
            order_col = Internship.published_at.asc()
        else:  # "latest" (default)
            order_col = Internship.published_at.desc()

        stmt = (
            select(Internship)
            .options(selectinload(Internship.company))
            .where(filter_clause)
            .order_by(order_col, Internship.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await db.execute(stmt)
        internships = result.scalars().all()

        items = []
        for i in internships:
            app_count = await InternshipRepository.get_applicant_count_for_internship(
                db, i.id, i.internship_number
            )
            items.append(
                InternshipRead(
                    id=i.id,
                    internship_number=i.internship_number,
                    company_id=i.company_id,
                    company_name=i.company.company_name if i.company else None,
                    title=i.title,
                    stipend_monthly=i.stipend_monthly,
                    stipend=i.stipend,
                    duration=i.duration,
                    work_mode=i.work_mode,
                    workMode=i.work_mode,
                    location=i.location,
                    number_of_interns=i.number_of_interns,
                    openings=i.number_of_interns,
                    description=i.description,
                    status=i.status,
                    applicantsCount=app_count,
                    candidate_count=app_count,
                    candidates_count=app_count,
                    published_at=i.published_at.strftime("%Y-%m-%d %H:%M:%S") if i.published_at else None,
                    postedOn=i.created_at.strftime("%Y-%m-%d") if i.created_at else None,
                    created_at=i.created_at.strftime("%Y-%m-%d %H:%M:%S") if i.created_at else None,
                    updated_at=i.updated_at.strftime("%Y-%m-%d %H:%M:%S") if i.updated_at else None,
                )
            )

        total_pages = (total + page_size - 1) // page_size if total > 0 else 1

        return PaginatedInternshipResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    @classmethod
    async def submit_draft_internship(
        cls,
        db: AsyncSession,
        current_user: User,
        internship_id: str,
    ) -> InternshipRead:
        """
        Transition a DRAFT or REJECTED internship to PENDING for administrator review.
        """
        internship = await InternshipRepository.get_internship_by_id(db, internship_id)
        if not internship:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Internship not found.",
            )

        if current_user.role != "ADMIN":
            profile = await InternshipRepository.get_recruiter_profile_by_user_id(db, current_user.id)
            if not profile or internship.company_id != profile.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You are not authorized to submit another organization's internship.",
                )

        now = datetime.now(timezone.utc)
        internship.status = "PENDING"
        internship.rejection_reason = None
        internship.updated_at = now
        await db.commit()
        await db.refresh(internship)

        await InternshipRepository.create_audit_log(
            db=db,
            actor=current_user.email,
            action="INTERNSHIP_SUBMITTED_FOR_APPROVAL",
            entity="INTERNSHIP",
            entity_id=internship.id,
            metadata_json={"internship_number": internship.internship_number, "status": "PENDING"},
        )

        app_count = await InternshipRepository.get_applicant_count_for_internship(
            db, internship.id, internship.internship_number
        )

        return InternshipRead(
            id=internship.id,
            internship_number=internship.internship_number,
            company_id=internship.company_id,
            company_name=internship.company.company_name if internship.company else None,
            title=internship.title,
            stipend_monthly=internship.stipend_monthly,
            stipend=internship.stipend,
            duration=internship.duration,
            work_mode=internship.work_mode,
            workMode=internship.work_mode,
            location=internship.location,
            number_of_interns=internship.number_of_interns,
            openings=internship.number_of_interns,
            description=internship.description,
            status=internship.status,
            rejection_reason=None,
            applicantsCount=app_count,
            candidate_count=app_count,
            candidates_count=app_count,
            published_at=internship.published_at.strftime("%Y-%m-%d %H:%M:%S") if internship.published_at else None,
            postedOn=internship.created_at.strftime("%Y-%m-%d") if internship.created_at else None,
            created_at=internship.created_at.strftime("%Y-%m-%d %H:%M:%S") if internship.created_at else None,
            updated_at=internship.updated_at.strftime("%Y-%m-%d %H:%M:%S") if internship.updated_at else None,
        )

