from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_database, get_current_admin
from app.models.user import User
from app.schemas.internship import (
    AdminInternshipDetail,
    AdminRejectInternshipRequest,
)
from app.services.internship_service import InternshipService

router = APIRouter(
    prefix="/admin/internships",
    tags=["Admin Internships"],
)


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    summary="List all internships for governance",
    description="Retrieve paginated list of all company internships with status filters (ALL, PENDING, PUBLISHED, REJECTED, CLOSED).",
)
async def list_admin_internships(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    status: Optional[str] = Query("ALL", description="Filter by status"),
    search: Optional[str] = Query(None, description="Search keyword"),
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_database),
) -> Dict[str, Any]:
    """
    GET /api/v1/admin/internships
    Requires Bearer JWT token with ADMIN role.
    """
    return await InternshipService.get_admin_internships(
        db=db,
        status_filter=status,
        search=search,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{internship_id}",
    response_model=AdminInternshipDetail,
    status_code=status.HTTP_200_OK,
    summary="Get full internship details for review",
    description="Retrieve comprehensive internship data including employer and applicant count.",
)
async def get_admin_internship_detail(
    internship_id: str,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_database),
) -> AdminInternshipDetail:
    """
    GET /api/v1/admin/internships/{internship_id}
    Requires Bearer JWT token with ADMIN role.
    """
    return await InternshipService.get_admin_internship_detail(
        db=db,
        internship_id=internship_id,
    )


@router.post(
    "/{internship_id}/approve",
    status_code=status.HTTP_200_OK,
    summary="Approve internship program",
    description="Administrator approves a pending internship program, transitioning it to PUBLISHED.",
)
async def approve_internship(
    internship_id: str,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_database),
) -> Dict[str, Any]:
    """
    POST /api/v1/admin/internships/{internship_id}/approve
    Requires Bearer JWT token with ADMIN role.
    """
    return await InternshipService.approve_internship(
        db=db,
        current_admin=current_admin,
        internship_id=internship_id,
    )


@router.post(
    "/{internship_id}/reject",
    status_code=status.HTTP_200_OK,
    summary="Reject internship program",
    description="Administrator rejects an internship program with a mandatory explanation.",
)
async def reject_internship(
    internship_id: str,
    payload: AdminRejectInternshipRequest,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_database),
) -> Dict[str, Any]:
    """
    POST /api/v1/admin/internships/{internship_id}/reject
    Requires Bearer JWT token with ADMIN role.
    """
    return await InternshipService.reject_internship(
        db=db,
        current_admin=current_admin,
        internship_id=internship_id,
        reason=payload.reason,
    )


# ── Alias Router for /admin/internship-approvals ────────────────────────────
admin_internship_approvals_router = APIRouter(
    prefix="/admin/internship-approvals",
    tags=["Admin Internships"],
)
admin_internship_approvals_router.add_api_route(
    "",
    list_admin_internships,
    methods=["GET"],
    status_code=status.HTTP_200_OK,
    summary="List Internships (/admin/internship-approvals)",
)
admin_internship_approvals_router.add_api_route(
    "/{internship_id}",
    get_admin_internship_detail,
    methods=["GET"],
    response_model=AdminInternshipDetail,
    status_code=status.HTTP_200_OK,
    summary="Get Internship Detail (/admin/internship-approvals/{internship_id})",
)
admin_internship_approvals_router.add_api_route(
    "/{internship_id}/approve",
    approve_internship,
    methods=["POST"],
    status_code=status.HTTP_200_OK,
    summary="Approve Internship (/admin/internship-approvals/{internship_id}/approve)",
)
admin_internship_approvals_router.add_api_route(
    "/{internship_id}/reject",
    reject_internship,
    methods=["POST"],
    status_code=status.HTTP_200_OK,
    summary="Reject Internship (/admin/internship-approvals/{internship_id}/reject)",
)

