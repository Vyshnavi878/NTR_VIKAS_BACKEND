from typing import Optional, List, Dict, Any, Union
from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_database, get_current_admin
from app.models.user import User
from app.schemas.admin_recruiter import (
    AdminRecruiterItem,
    PaginatedAdminRecruiterResponse,
    AdminCreateRecruiterRequest,
    AdminRecruiterVerificationUpdate,
    AdminRecruiterAccountStatusUpdate,
    AdminRecruiterDetail,
)
from app.services.admin_recruiter_service import AdminRecruiterService

router = APIRouter(
    prefix="/admin/recruiters",
    tags=["Admin Recruiters Management"],
)

alias_router = APIRouter(
    prefix="/admin/recruiter-verifications",
    tags=["Admin Recruiter Verifications"],
)


@router.get(
    "",
    response_model=Union[PaginatedAdminRecruiterResponse, List[AdminRecruiterItem]],
    status_code=status.HTTP_200_OK,
    summary="List recruiters for Admin management table",
    description="Retrieve paginated recruiters with server-side search, status and company filters, and metrics.",
)
async def list_admin_recruiters(
    status: Optional[str] = Query("ALL", description="Filter by status: ALL, VERIFIED, PENDING, SUSPENDED, REJECTED"),
    company: Optional[str] = Query("ALL", description="Filter by company name or ID"),
    search: Optional[str] = Query(None, description="Search by recruiter name, email, company, designation"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Records per page"),
    raw_list: bool = Query(False, description="Return flat list instead of paginated response"),
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_database),
) -> Union[PaginatedAdminRecruiterResponse, List[AdminRecruiterItem]]:
    """GET /api/v1/admin/recruiters"""
    res = await AdminRecruiterService.get_admin_recruiters(
        db=db,
        status_filter=status,
        company_filter=company,
        search=search,
        page=page,
        page_size=page_size,
    )
    if raw_list:
        return res.items
    return res


@router.post(
    "",
    response_model=AdminRecruiterItem,
    status_code=status.HTTP_201_CREATED,
    summary="Direct Register Recruiter / Employer",
    description="Directly register and verify a recruiter account by Administrator, assigned to an existing or new company.",
)
async def create_admin_recruiter(
    payload: AdminCreateRecruiterRequest,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_database),
) -> AdminRecruiterItem:
    """POST /api/v1/admin/recruiters"""
    return await AdminRecruiterService.create_admin_recruiter(
        db=db,
        current_admin=current_admin,
        payload=payload,
    )


@router.get(
    "/{recruiter_id}",
    response_model=AdminRecruiterDetail,
    status_code=status.HTTP_200_OK,
    summary="Get recruiter dossier details",
    description="Retrieve full recruiter profile, contact, company, and posted vacancies.",
)
async def get_admin_recruiter(
    recruiter_id: str,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_database),
) -> AdminRecruiterDetail:
    """GET /api/v1/admin/recruiters/{recruiter_id}"""
    return await AdminRecruiterService.get_admin_recruiter_detail(
        db=db,
        recruiter_id=recruiter_id,
    )


@router.patch(
    "/{recruiter_id}/verification",
    response_model=AdminRecruiterItem,
    status_code=status.HTTP_200_OK,
    summary="Update recruiter verification status",
    description="Admin action to mark a recruiter as VERIFIED, REJECTED, or PENDING.",
)
async def update_recruiter_verification(
    recruiter_id: str,
    payload: AdminRecruiterVerificationUpdate,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_database),
) -> AdminRecruiterItem:
    """PATCH /api/v1/admin/recruiters/{recruiter_id}/verification"""
    return await AdminRecruiterService.update_verification(
        db=db,
        current_admin=current_admin,
        recruiter_id=recruiter_id,
        payload=payload,
    )


@router.patch(
    "/{recruiter_id}/account-status",
    response_model=AdminRecruiterItem,
    status_code=status.HTTP_200_OK,
    summary="Update recruiter account status (Suspend / Activate)",
    description="Admin action to suspend or activate a recruiter account without affecting the entire organization.",
)
async def update_recruiter_account_status(
    recruiter_id: str,
    payload: AdminRecruiterAccountStatusUpdate,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_database),
) -> AdminRecruiterItem:
    """PATCH /api/v1/admin/recruiters/{recruiter_id}/account-status"""
    return await AdminRecruiterService.update_account_status(
        db=db,
        current_admin=current_admin,
        recruiter_id=recruiter_id,
        payload=payload,
    )


@router.post(
    "/{recruiter_id}/verify",
    response_model=AdminRecruiterItem,
    status_code=status.HTTP_200_OK,
    summary="Verify recruiter account",
)
async def verify_recruiter_post(
    recruiter_id: str,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_database),
) -> AdminRecruiterItem:
    """POST /api/v1/admin/recruiters/{recruiter_id}/verify"""
    return await AdminRecruiterService.update_verification(
        db=db,
        current_admin=current_admin,
        recruiter_id=recruiter_id,
        payload=AdminRecruiterVerificationUpdate(status="VERIFIED"),
    )


@router.post(
    "/{recruiter_id}/suspend",
    response_model=AdminRecruiterItem,
    status_code=status.HTTP_200_OK,
    summary="Suspend recruiter account",
)
async def suspend_recruiter_post(
    recruiter_id: str,
    payload: Optional[AdminRecruiterAccountStatusUpdate] = None,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_database),
) -> AdminRecruiterItem:
    """POST /api/v1/admin/recruiters/{recruiter_id}/suspend"""
    reason = payload.reason if payload else "Account suspended by platform administrator."
    return await AdminRecruiterService.update_account_status(
        db=db,
        current_admin=current_admin,
        recruiter_id=recruiter_id,
        payload=AdminRecruiterAccountStatusUpdate(status="SUSPENDED", reason=reason),
    )


@router.post(
    "/{recruiter_id}/activate",
    response_model=AdminRecruiterItem,
    status_code=status.HTTP_200_OK,
    summary="Activate recruiter account",
)
async def activate_recruiter_post(
    recruiter_id: str,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_database),
) -> AdminRecruiterItem:
    """POST /api/v1/admin/recruiters/{recruiter_id}/activate"""
    return await AdminRecruiterService.update_account_status(
        db=db,
        current_admin=current_admin,
        recruiter_id=recruiter_id,
        payload=AdminRecruiterAccountStatusUpdate(status="ACTIVE"),
    )


@router.get(
    "/{recruiter_id}/export",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Export recruiter dossier data",
    description="Returns full export payload for downloading recruiter profile dossier.",
)
async def export_recruiter_dossier(
    recruiter_id: str,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_database),
) -> Dict[str, Any]:
    """GET /api/v1/admin/recruiters/{recruiter_id}/export"""
    return await AdminRecruiterService.export_recruiter_dossier(
        db=db,
        recruiter_id=recruiter_id,
    )


# Mount routes onto alias_router as well
alias_router.add_api_route("", list_admin_recruiters, methods=["GET"], response_model=Union[PaginatedAdminRecruiterResponse, List[AdminRecruiterItem]])
alias_router.add_api_route("/{recruiter_id}", get_admin_recruiter, methods=["GET"], response_model=AdminRecruiterDetail)
alias_router.add_api_route("/{recruiter_id}/verification", update_recruiter_verification, methods=["PATCH"], response_model=AdminRecruiterItem)
