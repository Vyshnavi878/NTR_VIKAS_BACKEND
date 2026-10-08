"""
Admin Platform Analytics Endpoints
GET /api/v1/admin/analytics
GET /api/v1/admin/analytics/export
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_database, get_current_admin
from app.models.user import User
from app.schemas.admin_analytics import AdminAnalyticsResponse
from app.services.admin_analytics_service import AdminAnalyticsService

router = APIRouter(
    prefix="/admin/analytics",
    tags=["Admin Platform Performance & Recruitment Analytics"],
)


@router.get(
    "",
    response_model=AdminAnalyticsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get platform-wide hiring analytics and KPIs",
    description="Retrieve live aggregated platform KPIs, industry sector demand distribution, and monthly placement trajectory across time ranges (7d, 30d, 90d, 1y, custom). Requires Administrator privileges.",
)
async def get_platform_analytics(
    period: Optional[str] = Query("30d", description="Time range: 7d, 30d, 90d, 1y, custom"),
    start_date: Optional[str] = Query(None, description="Custom start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="Custom end date YYYY-MM-DD"),
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_database),
) -> AdminAnalyticsResponse:
    """Returns platform-wide real-time metrics and historical trajectory."""
    return await AdminAnalyticsService.get_analytics(
        db=db,
        current_admin=current_admin,
        period=period,
        start_date=start_date,
        end_date=end_date,
    )


@router.get(
    "/export",
    status_code=status.HTTP_200_OK,
    summary="Export platform analytics report as CSV",
    description="Generates and streams a downloadable CSV report of platform KPIs, sector demand, and placement trajectory for the selected time range. Requires Administrator privileges.",
)
async def export_platform_analytics_csv(
    period: Optional[str] = Query("30d", description="Time range: 7d, 30d, 90d, 1y, custom"),
    start_date: Optional[str] = Query(None, description="Custom start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="Custom end date YYYY-MM-DD"),
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_database),
) -> Response:
    """Exports platform analytics report as CSV stream and logs an audit trail event."""
    csv_content = await AdminAnalyticsService.export_analytics_csv(
        db=db,
        current_admin=current_admin,
        period=period,
        start_date=start_date,
        end_date=end_date,
    )
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=platform_analytics_report.csv",
            "Content-Type": "text/csv; charset=utf-8",
        },
    )
