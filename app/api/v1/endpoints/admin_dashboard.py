"""
Admin Dashboard Endpoint
GET /api/v1/admin/dashboard

Authentication: Bearer JWT (ADMIN role only)
Authorization: Admin identity strictly derived from verified token — never from query/body params.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_database, get_current_admin
from app.models.user import User
from app.schemas.admin_dashboard import AdminDashboardResponse
from app.services.admin_dashboard_service import AdminDashboardService

router = APIRouter(
    prefix="/admin",
    tags=["Admin Dashboard"],
)


@router.get(
    "/dashboard",
    response_model=AdminDashboardResponse,
    summary="Get Admin Platform Command Center Dashboard",
    description=(
        "Returns comprehensive platform-wide analytics, pending moderation queues, "
        "live stream items, and recent security audit trail. "
        "Strictly requires an authenticated Administrator Bearer token."
    ),
)
async def get_admin_dashboard(
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_database),
) -> AdminDashboardResponse:
    """
    GET /api/v1/admin/dashboard

    Scoped strictly to authenticated administrators. Candidates and recruiters receive 403 Forbidden.
    """
    return await AdminDashboardService.get_dashboard(db, current_admin)
