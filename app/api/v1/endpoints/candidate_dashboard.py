"""
Candidate Dashboard Endpoint
GET /api/v1/candidate/dashboard

Authentication:  Bearer JWT (CANDIDATE role only)
Authorization:   Identity extracted from verified token — never from query params.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_database, get_current_candidate
from app.models.user import User
from app.schemas.candidate_dashboard import CandidateDashboardResponse
from app.services.candidate_dashboard_service import CandidateDashboardService

router = APIRouter(
    prefix="/candidate",
    tags=["Candidate Dashboard"],
)


@router.get(
    "/dashboard",
    response_model=CandidateDashboardResponse,
    summary="Get Candidate Dashboard",
    description=(
        "Returns a single unified payload containing all data required by the "
        "Candidate Dashboard page: candidate identity, summary statistics, "
        "recent applications, profile strength, recommended jobs, and upcoming "
        "interviews.  Requires a valid CANDIDATE JWT access token."
    ),
)
async def get_candidate_dashboard(
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_database),
) -> CandidateDashboardResponse:
    """
    GET /api/v1/candidate/dashboard

    Identity is derived exclusively from the JWT token — not from any
    query parameter — ensuring a candidate can only view their own data.
    """
    return await CandidateDashboardService.get_dashboard(db, current_user)
