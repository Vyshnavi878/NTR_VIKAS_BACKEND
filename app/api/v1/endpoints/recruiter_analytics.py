from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_database, get_current_recruiter
from app.models.user import User
from app.schemas.recruiter_analytics import RecruiterAnalyticsResponse
from app.services.recruiter_analytics_service import RecruiterAnalyticsService

router = APIRouter(
    prefix="/recruiter/analytics",
    tags=["Recruiter Analytics"],
)


@router.get(
    "",
    response_model=RecruiterAnalyticsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get recruiter hiring analytics",
    description="Retrieve comprehensive hiring KPIs, recruitment funnel, application velocity, job posting performance, and candidate sourcing for the authenticated recruiter.",
)
async def get_analytics(
    date_range: Optional[str] = Query(
        "30d",
        description="Filter range: 7d, 30d, 90d, 1y, or custom",
    ),
    start_date: Optional[str] = Query(
        None,
        description="Start date in YYYY-MM-DD format (used when date_range=custom)",
    ),
    end_date: Optional[str] = Query(
        None,
        description="End date in YYYY-MM-DD format (used when date_range=custom)",
    ),
    current_user: User = Depends(get_current_recruiter),
    db: AsyncSession = Depends(get_database),
) -> RecruiterAnalyticsResponse:
    """
    GET /api/v1/recruiter/analytics
    Requires Bearer JWT token with RECRUITER role.
    Derives company and recruiter scope strictly from access token.
    """
    return await RecruiterAnalyticsService.get_analytics(
        db=db,
        current_user=current_user,
        date_range=date_range,
        start_date=start_date,
        end_date=end_date,
    )


@router.get(
    "/export",
    status_code=status.HTTP_200_OK,
    summary="Export recruiter hiring analytics report",
    description="Export full recruitment analytics report as a downloadable CSV.",
)
async def export_analytics(
    date_range: Optional[str] = Query(
        "30d",
        description="Filter range: 7d, 30d, 90d, 1y, or custom",
    ),
    start_date: Optional[str] = Query(
        None,
        description="Start date in YYYY-MM-DD format (used when date_range=custom)",
    ),
    end_date: Optional[str] = Query(
        None,
        description="End date in YYYY-MM-DD format (used when date_range=custom)",
    ),
    format: str = Query(
        "csv",
        description="Export format, defaults to csv",
    ),
    current_user: User = Depends(get_current_recruiter),
    db: AsyncSession = Depends(get_database),
):
    """
    GET /api/v1/recruiter/analytics/export
    Requires Bearer JWT token with RECRUITER role.
    Returns downloadable CSV with all analytics sections.
    """
    csv_content, filename = await RecruiterAnalyticsService.export_analytics_csv(
        db=db,
        current_user=current_user,
        date_range=date_range,
        start_date=start_date,
        end_date=end_date,
    )

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )
