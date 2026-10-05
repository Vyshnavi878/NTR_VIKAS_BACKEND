from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.security import verify_password, hash_password
from app.models.user import User
from app.models.candidate import CandidateProfile
from app.repositories.candidate_settings_repository import CandidateSettingsRepository
from app.schemas.candidate_settings import (
    CandidateSettingsResponse,
    NotificationSettingsUpdate,
    PrivacySettingsUpdate,
    ChangePasswordRequest,
    MessageResponse,
)


class CandidateSettingsService:
    """
    Service handling candidate settings:
    - Notification preferences retrieval and persistence
    - Profile privacy & recruiter visibility
    - Secure password change with verification
    - Secure account deactivation/deletion
    """

    @staticmethod
    async def get_candidate_profile(
        db: AsyncSession,
        user_id: str,
    ) -> CandidateProfile:
        stmt = select(CandidateProfile).where(CandidateProfile.user_id == user_id)
        result = await db.execute(stmt)
        profile = result.scalar_one_or_none()
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Candidate profile not found.",
            )
        return profile

    @classmethod
    async def get_settings(
        cls,
        db: AsyncSession,
        current_user: User,
    ) -> CandidateSettingsResponse:
        """
        Retrieve settings for the authenticated candidate.
        If no settings record exists, creates one with default preferences.
        """
        profile = await cls.get_candidate_profile(db, current_user.id)
        settings = await CandidateSettingsRepository.get_or_create_by_candidate_id(db, profile.id)
        return CandidateSettingsResponse.model_validate(settings)

    @classmethod
    async def update_notifications(
        cls,
        db: AsyncSession,
        current_user: User,
        payload: NotificationSettingsUpdate,
    ) -> CandidateSettingsResponse:
        """
        Update notification preferences for the authenticated candidate.
        """
        profile = await cls.get_candidate_profile(db, current_user.id)
        settings = await CandidateSettingsRepository.update_notifications(db, profile.id, payload)
        return CandidateSettingsResponse.model_validate(settings)

    @classmethod
    async def update_privacy(
        cls,
        db: AsyncSession,
        current_user: User,
        payload: PrivacySettingsUpdate,
    ) -> CandidateSettingsResponse:
        """
        Update privacy and recruiter visibility preferences for the authenticated candidate.
        """
        profile = await cls.get_candidate_profile(db, current_user.id)
        settings = await CandidateSettingsRepository.update_privacy(db, profile.id, payload)
        return CandidateSettingsResponse.model_validate(settings)

    @classmethod
    async def change_password(
        cls,
        db: AsyncSession,
        current_user: User,
        payload: ChangePasswordRequest,
    ) -> MessageResponse:
        """
        Secure candidate password change:
        1. Verify current password hash (401 on mismatch).
        2. Validate new password length (minimum 8 characters).
        3. Validate new password confirmation match (422 on mismatch).
        4. Validate that new password differs from current password (400 on reuse).
        5. Hash and persist new password.
        """
        # 1. Verify current password
        if not verify_password(payload.current_password, current_user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Current password is incorrect.",
            )

        # 2. Confirm new password matches confirmation
        if payload.new_password != payload.confirm_password:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="New password and confirmation password do not match.",
            )

        # 3. Minimum length validation
        if len(payload.new_password) < 8:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="New password must be at least 8 characters long.",
            )

        # 4. Reject same password
        if verify_password(payload.new_password, current_user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password must be different from the current password.",
            )

        # 5. Hash and update
        current_user.hashed_password = hash_password(payload.new_password)
        await db.commit()

        return MessageResponse(
            status="success",
            message="Password updated successfully.",
        )

    @classmethod
    async def delete_account(
        cls,
        db: AsyncSession,
        current_user: User,
    ) -> MessageResponse:
        """
        Secure account deactivation/deletion:
        - Sets user.is_active = False so candidate cannot authenticate or access endpoints.
        - Preserves existing applications, timelines, and audit history.
        """
        current_user.is_active = False
        await db.commit()

        return MessageResponse(
            status="success",
            message="Candidate account deleted successfully.",
        )
