from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.password_reset_token import PasswordResetToken


class PasswordResetRepository:
    """
    Async database repository for Password Reset operations via AsyncSession.
    """

    @staticmethod
    async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
        stmt = select(User).where(User.email == email.lower().strip())
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_by_id(db: AsyncSession, user_id: str) -> Optional[User]:
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def create_reset_token(
        db: AsyncSession,
        user_id: str,
        token_hash: str,
        expires_at: datetime,
    ) -> PasswordResetToken:
        token_record = PasswordResetToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            created_at=datetime.now(timezone.utc),
        )
        db.add(token_record)
        await db.commit()
        await db.refresh(token_record)
        return token_record

    @staticmethod
    async def get_by_token_hash(
        db: AsyncSession,
        token_hash: str,
    ) -> Optional[PasswordResetToken]:
        stmt = select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def mark_token_used(
        db: AsyncSession,
        token_record: PasswordResetToken,
    ) -> None:
        token_record.used_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(token_record)

    @staticmethod
    async def update_user_password(
        db: AsyncSession,
        user: User,
        hashed_password: str,
    ) -> None:
        user.hashed_password = hashed_password
        await db.commit()
        await db.refresh(user)

    @staticmethod
    async def invalidate_active_tokens(
        db: AsyncSession,
        user_id: str,
    ) -> None:
        now = datetime.now(timezone.utc)
        stmt = (
            update(PasswordResetToken)
            .where(
                PasswordResetToken.user_id == user_id,
                PasswordResetToken.used_at.is_(None),
            )
            .values(used_at=now)
        )
        await db.execute(stmt)
        await db.commit()
