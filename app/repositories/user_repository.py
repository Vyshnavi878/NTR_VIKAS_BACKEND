from typing import Optional
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class UserRepository:
    """
    Async database repository for User entity operations.
    """

    @staticmethod
    async def get_by_email(db: AsyncSession, email: str) -> Optional[User]:
        stmt = select(User).where(User.email == email.lower().strip())
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_email_with_profile(db: AsyncSession, email: str) -> Optional[User]:
        stmt = (
            select(User)
            .options(
                selectinload(User.candidate_profile),
                selectinload(User.recruiter_profile),
                selectinload(User.admin_profile),
            )
            .where(User.email == email.lower().strip())
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_id(db: AsyncSession, user_id: str) -> Optional[User]:
        stmt = (
            select(User)
            .options(
                selectinload(User.candidate_profile),
                selectinload(User.recruiter_profile),
                selectinload(User.admin_profile),
            )
            .where(User.id == user_id)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

