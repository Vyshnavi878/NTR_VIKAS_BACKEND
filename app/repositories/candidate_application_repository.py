from typing import List, Optional, Dict
from sqlalchemy import select, func, or_, case
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.application import CandidateApplication, ApplicationTimelineEvent


class CandidateApplicationRepository:
    @staticmethod
    async def get_by_id_and_candidate(
        db: AsyncSession, identifier: str, candidate_profile_id: str
    ) -> Optional[CandidateApplication]:
        """Fetch application matching id or application_number belonging to candidate."""
        stmt = (
            select(CandidateApplication)
            .where(
                CandidateApplication.candidate_profile_id == candidate_profile_id,
                or_(
                    CandidateApplication.id == identifier,
                    CandidateApplication.application_number == identifier,
                ),
            )
            .options(selectinload(CandidateApplication.timeline_events))
        )
        result = await db.execute(stmt)
        return result.scalars().first()

    @staticmethod
    async def get_by_id(
        db: AsyncSession, identifier: str
    ) -> Optional[CandidateApplication]:
        """Fetch application matching id or application_number across any candidate."""
        stmt = (
            select(CandidateApplication)
            .where(
                or_(
                    CandidateApplication.id == identifier,
                    CandidateApplication.application_number == identifier,
                )
            )
            .options(selectinload(CandidateApplication.timeline_events))
        )
        result = await db.execute(stmt)
        return result.scalars().first()

    @staticmethod
    async def list_applications(
        db: AsyncSession,
        candidate_profile_id: str,
        status: Optional[str] = None,
        search: Optional[str] = None,
    ) -> List[CandidateApplication]:
        """
        List applications for candidate, newest first, with optional status and search filters.
        Eagerly loads timeline events to avoid N+1 queries.
        """
        stmt = (
            select(CandidateApplication)
            .where(CandidateApplication.candidate_profile_id == candidate_profile_id)
            .options(selectinload(CandidateApplication.timeline_events))
            .order_by(CandidateApplication.applied_at.desc())
        )

        if status and status.strip().upper() != "ALL":
            stmt = stmt.where(CandidateApplication.status == status.strip().upper())

        if search and search.strip():
            term = f"%{search.strip()}%"
            stmt = stmt.where(
                or_(
                    CandidateApplication.job_title.ilike(term),
                    CandidateApplication.company_name.ilike(term),
                    CandidateApplication.location.ilike(term),
                    CandidateApplication.application_number.ilike(term),
                    CandidateApplication.mela_title.ilike(term),
                )
            )

        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_status_counts(
        db: AsyncSession, candidate_profile_id: str
    ) -> Dict[str, int]:
        """
        Compute status counts in a single aggregated MySQL query.
        Avoids loading all rows into Python.
        """
        stmt = (
            select(
                func.count(CandidateApplication.id).label("all_count"),
                func.sum(case((CandidateApplication.status == "APPLIED", 1), else_=0)).label("applied_count"),
                func.sum(case((CandidateApplication.status == "SCREENING", 1), else_=0)).label("screening_count"),
                func.sum(case((CandidateApplication.status == "SHORTLISTED", 1), else_=0)).label("shortlisted_count"),
                func.sum(case((CandidateApplication.status == "INTERVIEW", 1), else_=0)).label("interview_count"),
                func.sum(case((CandidateApplication.status == "SELECTED", 1), else_=0)).label("selected_count"),
                func.sum(case((CandidateApplication.status == "REJECTED", 1), else_=0)).label("rejected_count"),
            )
            .where(CandidateApplication.candidate_profile_id == candidate_profile_id)
        )
        result = await db.execute(stmt)
        row = result.first()
        if not row:
            return {
                "all": 0, "applied": 0, "screening": 0,
                "shortlisted": 0, "interview": 0, "selected": 0, "rejected": 0
            }

        return {
            "all": int(row.all_count or 0),
            "applied": int(row.applied_count or 0),
            "screening": int(row.screening_count or 0),
            "shortlisted": int(row.shortlisted_count or 0),
            "interview": int(row.interview_count or 0),
            "selected": int(row.selected_count or 0),
            "rejected": int(row.rejected_count or 0),
        }

    @staticmethod
    async def get_by_candidate_and_job(
        db: AsyncSession, candidate_profile_id: str, job_id: str
    ) -> Optional[CandidateApplication]:
        """Check if candidate has already applied to this job."""
        stmt = (
            select(CandidateApplication)
            .where(
                CandidateApplication.candidate_profile_id == candidate_profile_id,
                CandidateApplication.job_id == str(job_id),
            )
            .options(selectinload(CandidateApplication.timeline_events))
        )
        res = await db.execute(stmt)
        return res.scalars().first()

    @staticmethod
    async def generate_unique_application_number(
        db: AsyncSession, is_mela: bool = False, mela_event: str = "01", company_seq: str = "01"
    ) -> str:
        """Generate a guaranteed unique application number server-side."""
        stmt = select(func.count(CandidateApplication.id))
        res = await db.execute(stmt)
        total_count = res.scalar() or 0

        offset = 1
        while True:
            if is_mela:
                seq = f"{(total_count + offset):04d}"
                candidate_number = f"NTR-{mela_event}-{company_seq}-{seq}"
            else:
                candidate_number = f"APP-{(total_count + offset):06d}"

            chk = select(CandidateApplication.id).where(
                CandidateApplication.application_number == candidate_number
            )
            chk_res = await db.execute(chk)
            if not chk_res.first():
                return candidate_number
            offset += 1

    @staticmethod
    async def create_application(
        db: AsyncSession, application: CandidateApplication
    ) -> CandidateApplication:
        """Add and commit an application."""
        db.add(application)
        await db.commit()
        await db.refresh(application)
        return application

    @staticmethod
    async def create_timeline_event(
        db: AsyncSession, event: ApplicationTimelineEvent
    ) -> ApplicationTimelineEvent:
        """Add and commit a timeline event."""
        db.add(event)
        await db.commit()
        await db.refresh(event)
        return event

