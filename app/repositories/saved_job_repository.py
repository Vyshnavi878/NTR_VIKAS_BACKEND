import json
from typing import List, Optional
from sqlalchemy import select, func, or_, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.saved_job import SavedJob


class SavedJobRepository:
    @staticmethod
    async def get_by_id(db: AsyncSession, saved_job_id: str) -> Optional[SavedJob]:
        """Fetch saved job by primary key ID."""
        result = await db.execute(select(SavedJob).where(SavedJob.id == saved_job_id))
        return result.scalars().first()

    @staticmethod
    async def get_by_candidate_and_job_id(
        db: AsyncSession, candidate_profile_id: str, job_id: str
    ) -> Optional[SavedJob]:
        """Fetch saved job by candidate profile ID and job ID."""
        result = await db.execute(
            select(SavedJob).where(
                SavedJob.candidate_profile_id == candidate_profile_id,
                SavedJob.job_id == str(job_id),
            )
        )
        return result.scalars().first()

    @staticmethod
    async def get_by_identifier_and_candidate(
        db: AsyncSession, identifier: str, candidate_profile_id: str
    ) -> Optional[SavedJob]:
        """Fetch saved job matching either saved_job_id or job_id for candidate."""
        result = await db.execute(
            select(SavedJob).where(
                SavedJob.candidate_profile_id == candidate_profile_id,
                or_(SavedJob.id == identifier, SavedJob.job_id == str(identifier)),
            )
        )
        return result.scalars().first()

    @staticmethod
    async def list_saved_jobs(
        db: AsyncSession,
        candidate_profile_id: str,
        search: Optional[str] = None,
    ) -> List[SavedJob]:
        """List candidate saved jobs, newest first, with optional search filter."""
        stmt = (
            select(SavedJob)
            .where(SavedJob.candidate_profile_id == candidate_profile_id)
            .order_by(SavedJob.saved_at.desc())
        )
        if search and search.strip():
            term = f"%{search.strip()}%"
            stmt = stmt.where(
                or_(
                    SavedJob.title.ilike(term),
                    SavedJob.company_name.ilike(term),
                    SavedJob.location.ilike(term),
                )
            )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def count_saved_jobs(db: AsyncSession, candidate_profile_id: str) -> int:
        """Count total saved jobs for candidate."""
        result = await db.execute(
            select(func.count(SavedJob.id)).where(
                SavedJob.candidate_profile_id == candidate_profile_id
            )
        )
        return result.scalar() or 0

    @staticmethod
    async def create(db: AsyncSession, saved_job: SavedJob) -> SavedJob:
        """Add and commit a new saved job."""
        db.add(saved_job)
        await db.commit()
        await db.refresh(saved_job)
        return saved_job

    @staticmethod
    async def delete(db: AsyncSession, saved_job: SavedJob) -> None:
        """Delete and commit removal of a saved job."""
        await db.delete(saved_job)
        await db.commit()
