from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.admin_dashboard_repository import AdminDashboardRepository
from app.schemas.admin_dashboard import (
    AdminModerationQueueResponse,
    AdminPlatformOverviewResponse,
    AdminModerationStreamItemResponse,
    AdminRecentAuditLogItemResponse,
    AdminDashboardResponse,
)


class AdminDashboardService:
    """Service orchestrating calculations and data assembly for the Admin Command Center."""

    @classmethod
    async def get_dashboard(cls, db: AsyncSession, current_admin: User) -> AdminDashboardResponse:
        """Fetch unified admin dashboard statistics, queues, streams, and recent audit activity."""
        if current_admin.role.upper() not in ["ADMIN", "PLATFORM_ADMINISTRATOR", "SUPER_ADMIN"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required.",
            )

        queue_data = await AdminDashboardRepository.get_moderation_queue_counts(db)
        overview_data = await AdminDashboardRepository.get_platform_overview_counts(db)
        stream_data = await AdminDashboardRepository.get_pending_moderation_stream(db, limit=10)
        logs_data = await AdminDashboardRepository.get_recent_audit_logs(db, limit=5)

        return AdminDashboardResponse(
            moderation_queue=AdminModerationQueueResponse(**queue_data),
            platform_overview=AdminPlatformOverviewResponse(**overview_data),
            pending_moderation_stream=[AdminModerationStreamItemResponse(**item) for item in stream_data],
            recent_audit_logs=[AdminRecentAuditLogItemResponse(**log) for log in logs_data],
        )
