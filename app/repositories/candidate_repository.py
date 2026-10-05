import uuid
from typing import Optional, Tuple, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload

from app.models.user import User
from app.models.candidate import CandidateProfile
from app.models.candidate_settings import CandidateSettings


class CandidateRepository:
    """
    Async repository layer for Candidate & User operations.
    Direct persistence to MySQL via AsyncSession and asyncmy.
    """

    @staticmethod
    async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
        stmt = select(User).where(User.email == email)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_by_phone(db: AsyncSession, phone: str) -> Optional[User]:
        stmt = select(User).where(User.phone == phone)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_candidate_by_aadhaar(db: AsyncSession, aadhaar_number: str) -> Optional[CandidateProfile]:
        stmt = select(CandidateProfile).where(CandidateProfile.aadhaar_number == aadhaar_number)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def create_candidate(
        db: AsyncSession,
        user: User,
        candidate_profile: CandidateProfile,
    ) -> Tuple[User, CandidateProfile]:
        db.add(user)
        db.add(candidate_profile)
        # Create default candidate settings
        settings = CandidateSettings(
            id=str(uuid.uuid4()),
            candidate_id=candidate_profile.id,
            email_job_application_alerts=True,
            sms_whatsapp_notifications=True,
            upcoming_interview_reminders=True,
            weekly_job_recommendation_digest=False,
            visible_in_recruiter_talent_search=True,
            direct_recruiter_messages=True,
        )
        db.add(settings)
        await db.commit()
        await db.refresh(user)
        await db.refresh(candidate_profile)
        return user, candidate_profile

    @staticmethod
    async def search_candidates_for_recruiters(
        db: AsyncSession,
        search_query: Optional[str] = None,
        location: Optional[str] = None,
        limit: int = 50,
    ) -> List[CandidateProfile]:
        """
        Recruiter Talent Search:
        ONLY returns candidates who have visible_in_recruiter_talent_search = True
        and whose user account is active.
        """
        stmt = (
            select(CandidateProfile)
            .join(User, CandidateProfile.user_id == User.id)
            .outerjoin(CandidateSettings, CandidateProfile.id == CandidateSettings.candidate_id)
            .where(
                User.is_active == True,
                or_(
                    CandidateSettings.visible_in_recruiter_talent_search == True,
                    CandidateSettings.id.is_(None),  # Default is visible
                ),
            )
            .options(selectinload(CandidateProfile.settings))
            .limit(limit)
        )
        if search_query:
            term = f"%{search_query.strip()}%"
            stmt = stmt.where(
                or_(
                    CandidateProfile.name.ilike(term),
                    CandidateProfile.headline.ilike(term),
                    CandidateProfile.preferred_job_roles.ilike(term),
                )
            )
        if location:
            stmt = stmt.where(CandidateProfile.district.ilike(f"%{location.strip()}%"))

        result = await db.execute(stmt)
        return list(result.scalars().all())
