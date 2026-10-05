import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import hash_password
from app.repositories.password_reset_repository import PasswordResetRepository
from app.schemas.auth import (
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    ResetPasswordRequest,
    ResetPasswordResponse,
)
from app.services.email_service import EmailService


class PasswordResetService:
    @staticmethod
    def hash_token(raw_token: str) -> str:
        """Deterministically hash the raw token using SHA-256 for secure DB storage."""
        return hashlib.sha256(raw_token.strip().encode("utf-8")).hexdigest()

    @classmethod
    async def request_password_reset(
        cls,
        payload: ForgotPasswordRequest,
        db: AsyncSession,
    ) -> ForgotPasswordResponse:
        """
        Forgot password workflow:
        1. Normalize and lookup email in MySQL.
        2. If user exists:
           - Invalidate previous unused reset tokens.
           - Generate cryptographically secure random token (secrets.token_urlsafe).
           - Store SHA-256 hashed token with 30-minute expiration in MySQL.
           - Dispatch professional reset email containing the secure link.
        3. Always return generic response to prevent email enumeration.
        """
        clean_email = payload.email.lower().strip()
        user = await PasswordResetRepository.get_user_by_email(db, clean_email)

        if user and user.is_active:
            # Invalidate any prior active tokens for this user
            await PasswordResetRepository.invalidate_active_tokens(db, user.id)

            # Generate cryptographically secure random token
            raw_token = secrets.token_urlsafe(32)
            token_hash = cls.hash_token(raw_token)
            expires_at = datetime.now(timezone.utc) + timedelta(
                minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES
            )

            # Persist hashed token in MySQL
            await PasswordResetRepository.create_reset_token(
                db=db,
                user_id=user.id,
                token_hash=token_hash,
                expires_at=expires_at,
            )

            # Construct one-time reset link
            reset_url = f"{settings.FRONTEND_URL.rstrip('/')}/reset-password?token={raw_token}"

            # Send reset email
            EmailService.send_password_reset_email(to_email=user.email, reset_url=reset_url)

        # Constant generic response regardless of whether user exists
        return ForgotPasswordResponse(
            message="If an account exists with this email, a password reset link has been sent."
        )

    @classmethod
    async def reset_password(
        cls,
        payload: ResetPasswordRequest,
        db: AsyncSession,
    ) -> ResetPasswordResponse:
        """
        Reset password workflow:
        1. Hash incoming token and query MySQL.
        2. Verify token existence, expiration, and single-use status.
        3. Securely hash new password with bcrypt.
        4. Update user password in MySQL.
        5. Invalidate / mark reset token as used.
        6. Return confirmation message.
        """
        if not payload.token or not payload.token.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password reset link is invalid or has expired.",
            )

        token_hash = cls.hash_token(payload.token)
        token_record = await PasswordResetRepository.get_by_token_hash(db, token_hash)

        # Security check: Must exist, not used, not expired
        if not token_record:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password reset link is invalid or has expired.",
            )

        if token_record.used_at is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password reset link is invalid or has expired.",
            )

        # Normalize timezone-naive datetime from MySQL if needed
        record_expires_at = token_record.expires_at
        if record_expires_at.tzinfo is None:
            record_expires_at = record_expires_at.replace(tzinfo=timezone.utc)

        if record_expires_at < datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password reset link is invalid or has expired.",
            )

        # Fetch associated user
        user = await PasswordResetRepository.get_user_by_id(db, token_record.user_id)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password reset link is invalid or has expired.",
            )

        # Hash new password securely with bcrypt
        new_hashed_pwd = hash_password(payload.new_password)

        # Update user password in MySQL
        await PasswordResetRepository.update_user_password(db, user, new_hashed_pwd)

        # Mark token as used immediately
        await PasswordResetRepository.mark_token_used(db, token_record)

        return ResetPasswordResponse(message="Password reset successfully.")
