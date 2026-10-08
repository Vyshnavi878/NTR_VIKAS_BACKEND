"""
Admin Security & System Audit Logs Endpoints
GET /api/v1/admin/audit-logs
GET /api/v1/admin/audit-logs/export
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_database, get_current_admin
from app.models.user import User
from app.schemas.audit_log import PaginatedAuditLogResponse
from app.services.audit_service import AuditService

router = APIRouter(
    prefix="/admin/audit-logs",
    tags=["Admin Security & System Audit Logs"],
)


@router.get(
    "",
    response_model=PaginatedAuditLogResponse,
    status_code=status.HTTP_200_OK,
    summary="Get paginated security & system audit logs",
    description="Query immutable audit trail records with server-side pagination, search, and action/result filtering. Requires Administrator privileges.",
)
async def list_audit_logs(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Records per page"),
    search: Optional[str] = Query(None, description="Search term for action, admin name, target entity"),
    action: Optional[str] = Query(None, description="Action filter e.g. 'Job Approved', 'Admin Login'"),
    result: Optional[str] = Query(None, description="Result filter e.g. 'SUCCESS', 'FAILED'"),
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_database),
) -> PaginatedAuditLogResponse:
    """Returns paginated audit trail logs for administrative review."""
    return await AuditService.get_audit_logs(
        db=db,
        current_admin=current_admin,
        page=page,
        page_size=page_size,
        search=search,
        action=action,
        result=result,
    )


@router.get(
    "/export",
    status_code=status.HTTP_200_OK,
    summary="Export audit logs as CSV",
    description="Exports security & system audit trail records as a CSV file download matching the UI columns. Requires Administrator privileges.",
)
async def export_audit_logs_csv(
    search: Optional[str] = Query(None, description="Search filter query"),
    action: Optional[str] = Query(None, description="Action filter"),
    result: Optional[str] = Query(None, description="Result filter"),
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_database),
) -> Response:
    """Exports audit trail log entries as a downloadable CSV."""
    csv_content = await AuditService.export_audit_csv(
        db=db,
        current_admin=current_admin,
        search=search,
        action=action,
        result=result,
    )
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=security_audit_logs.csv",
            "Content-Type": "text/csv; charset=utf-8",
        },
    )
