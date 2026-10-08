import json
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin_profile import AdminProfile
from app.models.internship import AuditLog


class AdminProfileRepository:
    """Async database repository for Admin Profile operations."""

    @staticmethod
    async def get_by_user_id(db: AsyncSession, user_id: str) -> Optional[AdminProfile]:
        """Fetch admin profile by user_id."""
        stmt = select(AdminProfile).where(AdminProfile.user_id == user_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def create(db: AsyncSession, profile: AdminProfile) -> AdminProfile:
        """Persist a new admin profile."""
        db.add(profile)
        await db.commit()
        await db.refresh(profile)
        return profile

    @staticmethod
    async def update(db: AsyncSession, profile: AdminProfile) -> AdminProfile:
        """Update existing admin profile."""
        profile.updated_at = datetime.now(timezone.utc)
        db.add(profile)
        await db.commit()
        await db.refresh(profile)
        return profile

    @staticmethod
    async def log_audit(
        db: AsyncSession,
        actor: str,
        action: str,
        entity_id: str,
        metadata_json: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        """Record an audit trail log entry for administrative profile changes."""
        log = AuditLog(
            id=f"audit-{uuid.uuid4().hex[:10]}",
            actor=actor,
            action=action,
            entity="ADMIN_PROFILE",
            entity_id=entity_id,
            target_name="Admin Profile Settings",
            result="SUCCESS",
            metadata_json=json.dumps(metadata_json) if metadata_json else None,
            timestamp=datetime.now(timezone.utc),
        )
        db.add(log)
        await db.commit()
        return log
