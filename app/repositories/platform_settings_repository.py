import json
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.platform_settings import PlatformSettings
from app.models.internship import AuditLog
from app.schemas.platform_settings import PlatformSettingsUpdate


class PlatformSettingsRepository:
    """Async database repository for centralized Platform Settings operations."""

    @staticmethod
    async def get_settings(db: AsyncSession) -> PlatformSettings:
        """
        Fetch the global singleton PlatformSettings record (id=1).
        If no record exists, automatically initializes and commits default settings.
        """
        stmt = select(PlatformSettings).where(PlatformSettings.id == 1)
        result = await db.execute(stmt)
        settings = result.scalar_one_or_none()

        if not settings:
            now = datetime.now(timezone.utc)
            settings = PlatformSettings(
                id=1,
                platform_display_name="NTR VIKASA State Job Portal Administration",
                primary_support_email="support@ntrvikasa.com",
                grievance_redressal_email="grievance@ntrvikasa.com",
                mandatory_recruiter_legal_verification=True,
                pre_publish_job_moderation_queue=True,
                strict_zero_fee_candidate_rule=True,
                platform_maintenance_mode=False,
                created_at=now,
                updated_at=now,
                updated_by="System Initializer",
            )
            db.add(settings)
            await db.commit()
            await db.refresh(settings)

        return settings

    @staticmethod
    async def update_settings(
        db: AsyncSession,
        settings: PlatformSettings,
        payload: PlatformSettingsUpdate,
        updated_by_email: str,
    ) -> PlatformSettings:
        """Apply partial updates to PlatformSettings and persist to MySQL."""
        # 1. Platform Display Name
        p_name = payload.platform_display_name if payload.platform_display_name is not None else payload.platformName
        if p_name is not None:
            settings.platform_display_name = p_name.strip()

        # 2. Support Email
        s_email = payload.primary_support_email if payload.primary_support_email is not None else payload.supportEmail
        if s_email is not None:
            settings.primary_support_email = str(s_email).strip().lower()

        # 3. Grievance Redressal Email
        g_email = payload.grievance_redressal_email if payload.grievance_redressal_email is not None else payload.grievanceEmail
        if g_email is not None:
            settings.grievance_redressal_email = str(g_email).strip().lower()

        # 4. Mandatory Recruiter Legal Verification
        m_rec = payload.mandatory_recruiter_legal_verification if payload.mandatory_recruiter_legal_verification is not None else payload.requireRecruiterVerification
        if m_rec is not None:
            settings.mandatory_recruiter_legal_verification = bool(m_rec)

        # 5. Pre-Publish Job Moderation Queue
        p_mod = payload.pre_publish_job_moderation_queue if payload.pre_publish_job_moderation_queue is not None else payload.requireJobModeration
        if p_mod is not None:
            settings.pre_publish_job_moderation_queue = bool(p_mod)

        # 6. Strict Zero-Fee Candidate Rule
        z_fee = payload.strict_zero_fee_candidate_rule if payload.strict_zero_fee_candidate_rule is not None else payload.enforceZeroCandidateFee
        if z_fee is not None:
            settings.strict_zero_fee_candidate_rule = bool(z_fee)

        # 7. Platform Maintenance Mode
        m_mode = payload.platform_maintenance_mode if payload.platform_maintenance_mode is not None else payload.enableMaintenanceMode
        if m_mode is not None:
            settings.platform_maintenance_mode = bool(m_mode)

        settings.updated_by = updated_by_email
        settings.updated_at = datetime.now(timezone.utc)

        db.add(settings)
        await db.commit()
        await db.refresh(settings)
        return settings

    @staticmethod
    async def log_audit(
        db: AsyncSession,
        actor: str,
        action: str,
        metadata_json: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        """Record an audit trail log entry for administrative settings changes."""
        log = AuditLog(
            id=f"audit-{uuid.uuid4().hex[:10]}",
            actor=actor,
            action=action,
            entity="PLATFORM_SETTINGS",
            entity_id="1",
            target_name="System Settings",
            result="SUCCESS",
            metadata_json=json.dumps(metadata_json) if metadata_json else None,
            timestamp=datetime.now(timezone.utc),
        )
        db.add(log)
        await db.commit()
        return log
