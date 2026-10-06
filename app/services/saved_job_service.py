import json
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.candidate import CandidateProfile
from app.models.saved_job import SavedJob
from app.repositories.saved_job_repository import SavedJobRepository
from app.repositories.candidate_dashboard_repository import CandidateDashboardRepository
from app.schemas.saved_job import (
    CandidateSummaryBrief,
    SavedJobItem,
    SavedJobsListResponse,
    SaveJobRequest,
    SavedJobDeleteResponse,
    SavedJobActionResponse,
)


def _serialize_saved_job(job: SavedJob) -> SavedJobItem:
    """Helper to convert SavedJob ORM model to SavedJobItem Pydantic schema."""
    skills_list: List[str] = []
    if job.skills:
        try:
            parsed = json.loads(job.skills)
            if isinstance(parsed, list):
                skills_list = [str(s) for s in parsed]
            else:
                skills_list = [str(parsed)]
        except Exception:
            skills_list = [s.strip() for s in job.skills.split(",") if s.strip()]

    saved_at_str = job.saved_at.strftime("%Y-%m-%d") if job.saved_at else datetime.now(timezone.utc).strftime("%Y-%m-%d")

    return SavedJobItem(
        saved_job_id=job.id,
        job_id=job.job_id,
        id=job.job_id,
        title=job.title,
        company_name=job.company_name,
        company=job.company_name,
        company_verified=job.company_verified,
        location=job.location,
        salary=job.salary or "₹14 - ₹22 LPA",
        experience=job.experience or "3-5 years",
        employment_type=job.employment_type or "Full-time",
        type=job.employment_type or "Full-time",
        work_mode=job.work_mode or "Hybrid",
        mode=job.work_mode or "Hybrid",
        skills=skills_list,
        tags=skills_list,
        saved_at=saved_at_str,
        is_applied=job.is_applied,
    )


class SavedJobService:
    @staticmethod
    async def get_candidate_profile(
        db: AsyncSession, user_id: str
    ) -> CandidateProfile:
        """Retrieve candidate profile for the given user, or raise 404."""
        profile = await CandidateDashboardRepository.get_candidate_profile(db, user_id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Candidate profile not found. Please complete your registration first.",
            )
        return profile

    @staticmethod
    async def get_saved_jobs(
        db: AsyncSession,
        current_user: User,
        search: Optional[str] = None,
    ) -> SavedJobsListResponse:
        """Fetch all saved jobs belonging to the authenticated candidate."""
        profile = await SavedJobService.get_candidate_profile(db, current_user.id)

        saved_jobs_orm = await SavedJobRepository.list_saved_jobs(
            db, candidate_profile_id=profile.id, search=search
        )
        total_count = await SavedJobRepository.count_saved_jobs(
            db, candidate_profile_id=profile.id
        )

        job_items = [_serialize_saved_job(j) for j in saved_jobs_orm]

        return SavedJobsListResponse(
            candidate=CandidateSummaryBrief(
                id=profile.id,
                full_name=profile.name,
            ),
            saved_jobs_count=total_count,
            saved_jobs=job_items,
        )

    @staticmethod
    async def save_job(
        db: AsyncSession,
        current_user: User,
        payload: SaveJobRequest,
    ) -> SavedJobActionResponse:
        """Save/bookmark a job for the authenticated candidate."""
        profile = await SavedJobService.get_candidate_profile(db, current_user.id)

        # Check for duplicate save
        existing = await SavedJobRepository.get_by_candidate_and_job_id(
            db, candidate_profile_id=profile.id, job_id=payload.job_id
        )
        if existing:
            return SavedJobActionResponse(
                message="Job is already saved.",
                saved_job=_serialize_saved_job(existing),
            )

        skills_json = json.dumps(payload.skills or [])

        new_saved_job = SavedJob(
            candidate_profile_id=profile.id,
            job_id=payload.job_id,
            title=payload.title or "Senior Software Engineer",
            company_name=payload.company_name or "TechCorp India",
            company_verified=payload.company_verified if payload.company_verified is not None else True,
            location=payload.location or "Bengaluru, Karnataka",
            salary=payload.salary or "₹14 - ₹22 LPA",
            experience=payload.experience or "3-5 years",
            employment_type=payload.employment_type or "Full-time",
            work_mode=payload.work_mode or "Hybrid",
            skills=skills_json,
            is_applied=False,
            saved_at=datetime.now(timezone.utc),
        )

        created = await SavedJobRepository.create(db, new_saved_job)
        return SavedJobActionResponse(
            message="Job saved successfully.",
            saved_job=_serialize_saved_job(created),
        )

    @staticmethod
    async def save_job_by_identifier(
        db: AsyncSession,
        current_user: User,
        identifier: str,
    ) -> SavedJobActionResponse:
        """Save a job by identifier (job_id, job_number, or UUID)."""
        from app.repositories.job_repository import JobRepository
        job = await JobRepository.get_job_by_id(db, identifier)
        if job:
            skills_list = [s.skill_name for s in job.job_skills]
            if not skills_list and job.skills:
                skills_list = [s.strip() for s in job.skills.split(",") if s.strip()]
            payload = SaveJobRequest(
                job_id=job.job_id or job.id,
                title=job.title,
                company_name=job.company_name,
                company_verified=True,
                location=job.location,
                salary=job.salary or "Competitive",
                experience=job.experience or "3-5 years",
                employment_type=job.job_type or "Full-time",
                work_mode=job.work_mode or "Hybrid",
                skills=skills_list,
            )
        else:
            payload = SaveJobRequest(job_id=identifier)
        return await SavedJobService.save_job(db, current_user, payload)

    @staticmethod
    async def delete_saved_job(
        db: AsyncSession,
        current_user: User,
        identifier: str,
    ) -> SavedJobDeleteResponse:
        """
        Delete a saved job by saved_job_id or job_id.
        Verifies ownership: candidate can only delete their own saved jobs.
        """
        profile = await SavedJobService.get_candidate_profile(db, current_user.id)

        # Look for record belonging to this candidate
        saved_job = await SavedJobRepository.get_by_identifier_and_candidate(
            db, identifier=identifier, candidate_profile_id=profile.id
        )

        if not saved_job:
            # Check if record exists for another candidate to return 403 Forbidden
            other_candidate_job = await SavedJobRepository.get_by_id(db, identifier)
            if other_candidate_job and other_candidate_job.candidate_profile_id != profile.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You are not authorized to delete another candidate's saved job.",
                )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Saved job not found.",
            )

        await SavedJobRepository.delete(db, saved_job)
        return SavedJobDeleteResponse(message="Job removed from saved jobs.")
