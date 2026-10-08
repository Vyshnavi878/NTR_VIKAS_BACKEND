from typing import Optional
from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_database, get_current_admin
from app.models.user import User
from app.schemas.report import (
    ReportListResponse,
    ReportSummaryResponse,
    ReportDetailResponse,
    ReportResolveRequest,
    ReportDismissRequest,
    ReportActionResponse,
)
from app.services.report_service import ReportService

router = APIRouter(prefix="/admin/reports", tags=["Admin Reports & Moderation"])


@router.get(
    "/summary",
    response_model=ReportSummaryResponse,
    summary="Get grievance moderation summary counts",
    description="Returns aggregate counts for all, pending, resolved, and dismissed reports. Requires Admin privileges.",
)
async def get_reports_summary(
    db: AsyncSession = Depends(get_database),
    current_admin: User = Depends(get_current_admin),
) -> ReportSummaryResponse:
    """Fetch report summary counts for header badges and tabs."""
    return await ReportService.get_summary(db=db, current_admin=current_admin)


@router.get(
    "/export",
    summary="Export moderation complaints as CSV",
    description="Streams a downloadable CSV export of complaints filtered by moderation status, target user type, or search terms.",
)
async def export_reports_csv(
    status: Optional[str] = Query(None, description="Filter by status: ALL, PENDING, RESOLVED, DISMISSED"),
    reported_user_type: Optional[str] = Query(None, description="Filter by user type: ALL, CANDIDATE, RECRUITER"),
    search: Optional[str] = Query(None, description="Search query string"),
    db: AsyncSession = Depends(get_database),
    current_admin: User = Depends(get_current_admin),
):
    """Export filtered moderation reports to CSV."""
    csv_data = await ReportService.export_reports_csv(
        db=db,
        current_admin=current_admin,
        status_filter=status,
        reported_user_type=reported_user_type,
        search=search,
    )
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=reports_and_complaints_export.csv",
        },
    )


@router.get(
    "",
    response_model=ReportListResponse,
    summary="List and filter moderation reports",
    description="Returns paginated platform complaints with status tabs, reported entity filtering, and debounced search.",
)
async def list_reports(
    status: Optional[str] = Query("ALL", description="Filter by status: ALL, PENDING, RESOLVED, DISMISSED"),
    reported_user_type: Optional[str] = Query("ALL", description="Filter by user type: ALL, CANDIDATE, RECRUITER"),
    search: Optional[str] = Query(None, description="Search across ID, entity name, reporter, or narrative"),
    page: int = Query(1, ge=1, description="1-indexed page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    sort_by: str = Query("created_at", description="Field to sort by"),
    sort_order: str = Query("desc", description="Sort direction: asc or desc"),
    db: AsyncSession = Depends(get_database),
    current_admin: User = Depends(get_current_admin),
) -> ReportListResponse:
    """Retrieve filtered and paginated moderation complaints."""
    return await ReportService.list_reports(
        db=db,
        current_admin=current_admin,
        status_filter=status,
        reported_user_type=reported_user_type,
        search=search,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.get(
    "/{report_id}",
    response_model=ReportDetailResponse,
    summary="Get grievance report details",
    description="Fetches full narrative, complainant profile, reported entity details, and audit history.",
)
async def get_report_detail(
    report_id: str,
    db: AsyncSession = Depends(get_database),
    current_admin: User = Depends(get_current_admin),
) -> ReportDetailResponse:
    """Retrieve full details of a single report."""
    return await ReportService.get_report_detail(
        db=db,
        current_admin=current_admin,
        report_id=report_id,
    )


@router.patch(
    "/{report_id}/resolve",
    response_model=ReportActionResponse,
    summary="Resolve a pending moderation report",
    description="Marks a pending complaint as RESOLVED, captures corrective action notes, and writes to audit logs.",
)
async def resolve_report(
    report_id: str,
    payload: ReportResolveRequest,
    db: AsyncSession = Depends(get_database),
    current_admin: User = Depends(get_current_admin),
) -> ReportActionResponse:
    """Enforce corrective action and resolve grievance."""
    return await ReportService.resolve_report(
        db=db,
        current_admin=current_admin,
        report_id=report_id,
        payload=payload,
    )


@router.patch(
    "/{report_id}/dismiss",
    response_model=ReportActionResponse,
    summary="Dismiss a pending moderation report",
    description="Marks a pending complaint as DISMISSED due to lack of evidence or policy compliance.",
)
async def dismiss_report(
    report_id: str,
    payload: ReportDismissRequest,
    db: AsyncSession = Depends(get_database),
    current_admin: User = Depends(get_current_admin),
) -> ReportActionResponse:
    """Dismiss non-actionable grievance report."""
    return await ReportService.dismiss_report(
        db=db,
        current_admin=current_admin,
        report_id=report_id,
        payload=payload,
    )
