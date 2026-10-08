from typing import Optional, Dict, Any
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.platform_settings import PlatformSettings
from app.repositories.platform_settings_repository import PlatformSettingsRepository
from app.schemas.platform_settings import (
    PlatformSettingsResponse,
    PlatformSettingsUpdate,
)


class PlatformSettingsService:
    """Business service layer for Global Platform & System Settings."""

    @classmethod
    def _to_response(cls, settings: PlatformSettings) -> PlatformSettingsResponse:
        """Convert SQLAlchemy PlatformSettings model to full PlatformSettingsResponse."""
        return PlatformSettingsResponse(
            id=settings.id,
            platform_display_name=settings.platform_display_name,
            primary_support_email=settings.primary_support_email,
            grievance_redressal_email=settings.grievance_redressal_email,
            mandatory_recruiter_legal_verification=settings.mandatory_recruiter_legal_verification,
            pre_publish_job_moderation_queue=settings.pre_publish_job_moderation_queue,
            strict_zero_fee_candidate_rule=settings.strict_zero_fee_candidate_rule,
            platform_maintenance_mode=settings.platform_maintenance_mode,
            created_at=settings.created_at,
            updated_at=settings.updated_at,
            updated_by=settings.updated_by,
            # Frontend camelCase compatibility aliases
            platformName=settings.platform_display_name,
            supportEmail=settings.primary_support_email,
            grievanceEmail=settings.grievance_redressal_email,
            requireRecruiterVerification=settings.mandatory_recruiter_legal_verification,
            requireJobModeration=settings.pre_publish_job_moderation_queue,
            enforceZeroCandidateFee=settings.strict_zero_fee_candidate_rule,
            enableMaintenanceMode=settings.platform_maintenance_mode,
        )

    @classmethod
    async def get_settings(
        cls,
        db: AsyncSession,
        current_admin: Optional[User] = None,
    ) -> PlatformSettingsResponse:
        """Retrieve global platform settings."""
        settings = await PlatformSettingsRepository.get_settings(db)
        return cls._to_response(settings)

    @classmethod
    async def update_settings(
        cls,
        db: AsyncSession,
        current_admin: User,
        payload: PlatformSettingsUpdate,
    ) -> PlatformSettingsResponse:
        """
        Update global platform settings by an authorized administrator:
        1. Validates admin authorization (ADMIN role).
        2. Retrieves existing settings.
        3. Tracks changed fields for audit logging.
        4. Persists updates to MySQL.
        5. Logs audit event PLATFORM_SETTINGS_UPDATED.
        6. Returns updated settings.
        """
        if current_admin.role.upper() != "ADMIN":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to update platform settings.",
            )

        settings = await PlatformSettingsRepository.get_settings(db)

        # Track previous values for change audit
        previous_state = {
            "platform_display_name": settings.platform_display_name,
            "primary_support_email": settings.primary_support_email,
            "grievance_redressal_email": settings.grievance_redressal_email,
            "mandatory_recruiter_legal_verification": settings.mandatory_recruiter_legal_verification,
            "pre_publish_job_moderation_queue": settings.pre_publish_job_moderation_queue,
            "strict_zero_fee_candidate_rule": settings.strict_zero_fee_candidate_rule,
            "platform_maintenance_mode": settings.platform_maintenance_mode,
        }

        updated_settings = await PlatformSettingsRepository.update_settings(
            db=db,
            settings=settings,
            payload=payload,
            updated_by_email=current_admin.email,
        )

        new_state = {
            "platform_display_name": updated_settings.platform_display_name,
            "primary_support_email": updated_settings.primary_support_email,
            "grievance_redressal_email": updated_settings.grievance_redressal_email,
            "mandatory_recruiter_legal_verification": updated_settings.mandatory_recruiter_legal_verification,
            "pre_publish_job_moderation_queue": updated_settings.pre_publish_job_moderation_queue,
            "strict_zero_fee_candidate_rule": updated_settings.strict_zero_fee_candidate_rule,
            "platform_maintenance_mode": updated_settings.platform_maintenance_mode,
        }

        # Calculate exact changed diff
        changed_fields = {
            k: {"from": previous_state[k], "to": new_state[k]}
            for k in previous_state
            if previous_state[k] != new_state[k]
        }

        if changed_fields:
            await PlatformSettingsRepository.log_audit(
                db=db,
                actor=current_admin.email,
                action="PLATFORM_SETTINGS_UPDATED",
                metadata_json={
                    "admin_email": current_admin.email,
                    "changes": changed_fields,
                },
            )

        return cls._to_response(updated_settings)
