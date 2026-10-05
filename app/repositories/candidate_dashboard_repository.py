"""
Candidate Dashboard Repository
Responsible for all database queries needed by the dashboard service.

Current tables available:
  - users                (email, role, is_active)
  - candidate_profiles   (name, phone, headline, bio, district, mandal,
                          village, qualification_level, profile_completion)

Tables that will be added in future phases (return empty/0 now):
  - applications
  - saved_jobs
  - interviews
"""
from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.candidate import CandidateProfile
from app.models.saved_job import SavedJob
from app.models.application import CandidateApplication


class CandidateDashboardRepository:
    """All database operations required by the dashboard aggregation."""

    # ── Profile ────────────────────────────────────────────────────────────────

    @staticmethod
    async def get_candidate_profile(
        db: AsyncSession, user_id: str
    ) -> Optional[CandidateProfile]:
        """Return the CandidateProfile linked to this user_id, or None."""
        stmt = select(CandidateProfile).where(CandidateProfile.user_id == user_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    # ── Statistics (placeholders until tables exist) ───────────────────────────
    # These will be replaced with real aggregate queries when the
    # applications / saved_jobs / interviews tables are added.

    @staticmethod
    async def get_applied_jobs_count(db: AsyncSession, candidate_profile_id: str) -> int:
        """Count total applications submitted by this candidate."""
        result = await db.execute(
            select(func.count(CandidateApplication.id)).where(
                CandidateApplication.candidate_profile_id == candidate_profile_id
            )
        )
        return result.scalar() or 0

    @staticmethod
    async def get_shortlisted_count(db: AsyncSession, candidate_profile_id: str) -> int:
        """Count applications that are SHORTLISTED."""
        result = await db.execute(
            select(func.count(CandidateApplication.id)).where(
                CandidateApplication.candidate_profile_id == candidate_profile_id,
                CandidateApplication.status == "SHORTLISTED",
            )
        )
        return result.scalar() or 0

    @staticmethod
    async def get_interviews_count(db: AsyncSession, candidate_profile_id: str) -> int:
        """Count upcoming scheduled interviews or applications in INTERVIEW status."""
        result = await db.execute(
            select(func.count(CandidateApplication.id)).where(
                CandidateApplication.candidate_profile_id == candidate_profile_id,
                CandidateApplication.status == "INTERVIEW",
            )
        )
        return result.scalar() or 0

    @staticmethod
    async def get_saved_jobs_count(db: AsyncSession, candidate_profile_id: str) -> int:
        """Count bookmarked/saved jobs from database."""
        result = await db.execute(
            select(func.count(SavedJob.id)).where(
                SavedJob.candidate_profile_id == candidate_profile_id
            )
        )
        return result.scalar() or 0

    # ── Recent Applications ────────────────────────────────────────────────────

    @staticmethod
    async def get_recent_applications(
        db: AsyncSession, candidate_profile_id: str, limit: int = 5
    ) -> list:
        """Return up to `limit` most-recent applications (newest first)."""
        stmt = (
            select(CandidateApplication)
            .where(CandidateApplication.candidate_profile_id == candidate_profile_id)
            .order_by(CandidateApplication.applied_at.desc())
            .limit(limit)
        )
        result = await db.execute(stmt)
        apps = result.scalars().all()
        return [
            {
                "application_id": a.application_number,
                "job_title": a.job_title,
                "company_name": a.company_name,
                "location": a.location,
                "applied_at": a.applied_date or a.applied_at.strftime("%Y-%m-%d"),
                "status": a.status,
            }
            for a in apps
        ]

    # ── Recommended Jobs ───────────────────────────────────────────────────────

    @staticmethod
    async def get_recommended_jobs(
        db: AsyncSession,
        candidate_profile_id: str,
        qualification: Optional[str] = None,
        district: Optional[str] = None,
        limit: int = 6,
    ) -> list:
        """Return recommended active job postings for this candidate."""
        return []

    # ── Upcoming Interviews ────────────────────────────────────────────────────

    @staticmethod
    async def get_upcoming_interviews(
        db: AsyncSession, candidate_profile_id: str
    ) -> list:
        """Return future-dated interviews that are SCHEDULED/CONFIRMED."""
        return []
