from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User
from app.models.recruiter import RecruiterProfile


class RecruiterRepository:
    """
    Async repository layer for Recruiter & Company Registration operations.
    Direct persistence to MySQL via AsyncSession and asyncmy.
    """

    @staticmethod
    async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
        stmt = select(User).where(User.email == email.lower().strip())
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_by_phone(db: AsyncSession, phone: str) -> Optional[User]:
        stmt = select(User).where(User.phone == phone.strip())
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_profile_by_work_email(db: AsyncSession, work_email: str) -> Optional[RecruiterProfile]:
        stmt = select(RecruiterProfile).where(RecruiterProfile.work_email == work_email.lower().strip())
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_profile_by_mobile(db: AsyncSession, mobile_phone: str) -> Optional[RecruiterProfile]:
        stmt = select(RecruiterProfile).where(RecruiterProfile.mobile_phone == mobile_phone.strip())
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_profile_by_company_name(db: AsyncSession, company_name: str) -> Optional[RecruiterProfile]:
        stmt = select(RecruiterProfile).where(RecruiterProfile.company_name == company_name.strip())
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_profile_by_user_id(db: AsyncSession, user_id: str) -> Optional[RecruiterProfile]:
        # 1. Direct owner profile
        stmt = select(RecruiterProfile).where(RecruiterProfile.user_id == user_id)
        result = await db.execute(stmt)
        profile = result.scalar_one_or_none()
        if profile:
            return profile

        # 2. Check if user is an active team member of a company
        from app.models.company_team import CompanyMember
        m_stmt = select(CompanyMember).where(
            CompanyMember.user_id == user_id,
            CompanyMember.status != "DEACTIVATED",
        )
        m_res = await db.execute(m_stmt)
        member = m_res.scalar_one_or_none()
        if member:
            c_stmt = select(RecruiterProfile).where(RecruiterProfile.id == member.company_id)
            c_res = await db.execute(c_stmt)
            return c_res.scalar_one_or_none()

        return None

    @staticmethod
    async def update_profile(
        db: AsyncSession,
        recruiter_profile: RecruiterProfile,
    ) -> RecruiterProfile:
        await db.commit()
        await db.refresh(recruiter_profile)
        return recruiter_profile

    @staticmethod
    async def create_recruiter(
        db: AsyncSession,
        user: User,
        recruiter_profile: RecruiterProfile,
    ) -> Tuple[User, RecruiterProfile]:
        db.add(user)
        db.add(recruiter_profile)
        await db.commit()
        await db.refresh(user)
        await db.refresh(recruiter_profile)
        return user, recruiter_profile
