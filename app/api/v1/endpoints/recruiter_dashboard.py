"""
Recruiter Dashboard Endpoint
GET /api/v1/recruiter/dashboard

Authentication: Bearer JWT (RECRUITER role only)
Authorization: Recruiter identity strictly derived from verified token — never from query/body params.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_database, get_current_recruiter
from app.models.user import User
from app.schemas.recruiter_dashboard import RecruiterDashboardResponse
from app.services.recruiter_dashboard_service import RecruiterDashboardService

router = APIRouter(
    prefix="/recruiter",
    tags=["Recruiter Dashboard"],
)


@router.get(
    "/dashboard",
    response_model=RecruiterDashboardResponse,
    summary="Get Recruiter Dashboard",
    description=(
        "Returns unified recruiter dashboard metrics including summary counts, "
        "recruitment pipeline funnel, recent applications, active jobs, and upcoming interviews. "
        "Strictly requires a valid RECRUITER Bearer JWT access token."
    ),
)
async def get_recruiter_dashboard(
    current_user: User = Depends(get_current_recruiter),
    db: AsyncSession = Depends(get_database),
) -> RecruiterDashboardResponse:
    """
    GET /api/v1/recruiter/dashboard

    Scoped strictly to the authenticated recruiter. Candidate tokens will receive 403 Forbidden.
    Unauthenticated requests will receive 401 Unauthorized.
    """
    return await RecruiterDashboardService.get_dashboard(db, current_user)
