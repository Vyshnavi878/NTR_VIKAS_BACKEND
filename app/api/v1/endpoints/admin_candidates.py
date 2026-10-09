from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, Query, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_database, get_current_admin
from app.models.user import User
from app.services.admin_candidate_service import AdminCandidateService
from app.schemas.admin_candidate import (
    AdminCreateCandidateRequest,
    AdminUpdateCandidatePlacementRequest,
    AdminUpdateCandidateStatusRequest,
    AdminCandidateItem,
    PaginatedAdminCandidateResponse,
)

router = APIRouter(
    prefix="/admin/candidates",
    tags=["Admin Candidate Governance"],
)


@router.get(
    "",
    response_model=PaginatedAdminCandidateResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin List Candidates & Student Directory",
    description="Retrieve paginated candidate directory with filters for search, placement status, qualifications, mandals, reference admin, and account status.",
)
async def list_admin_candidates(
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Records per page"),
    search: Optional[str] = Query(default=None, description="Search by name, email, phone, mandal, village, company, referrer"),
    placement_status: Optional[str] = Query(default="ALL", description="Filter by placement status: ALL, PLACED, NOT_PLACED"),
    qualification: Optional[str] = Query(default="ALL", description="Filter by qualification: ALL, 10TH, INTER, UG_PG"),
    mandal: Optional[str] = Query(default="ALL", description="Filter by NTR District mandal"),
    reference: Optional[str] = Query(default="ALL", description="Filter by referring admin officer"),
    account_status: Optional[str] = Query(default="ALL", description="Filter by account status: ALL, ACTIVE, SUSPENDED"),
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_database),
) -> PaginatedAdminCandidateResponse:
    return await AdminCandidateService.list_candidates(
        db=db,
        page=page,
        page_size=page_size,
        search=search,
        placement_status=placement_status,
        qualification=qualification,
        mandal=mandal,
        reference=reference,
        account_status=account_status,
    )


@router.post(
    "",
    response_model=AdminCandidateItem,
    status_code=status.HTTP_201_CREATED,
    summary="Admin Manually Onboard & Register Student / Candidate",
    description="Admin creates and registers a candidate directly. Enforces unique email, mobile, and Aadhaar, hashes credentials, initializes KYC profile, and records administrative audit trail.",
)
async def create_admin_candidate(
    payload: AdminCreateCandidateRequest,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_database),
) -> AdminCandidateItem:
    return await AdminCandidateService.create_candidate(
        db=db,
        current_admin=current_admin,
        payload=payload,
    )


@router.get(
    "/{candidate_id}",
    response_model=AdminCandidateItem,
    status_code=status.HTTP_200_OK,
    summary="Admin Get Candidate Profile Details",
    description="Retrieve complete verified details for an individual candidate (Aadhaar masked).",
)
async def get_admin_candidate(
    candidate_id: str = Path(..., description="Candidate or User ID"),
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_database),
) -> AdminCandidateItem:
    return await AdminCandidateService.get_candidate_details(
        db=db,
        candidate_id=candidate_id,
    )


@router.patch(
    "/{candidate_id}/placement",
    response_model=AdminCandidateItem,
    status_code=status.HTTP_200_OK,
    summary="Admin Update Candidate Placement Details",
    description="Update candidate placement status (PLACED/NOT_PLACED) and employer hiring details.",
)
async def update_candidate_placement(
    candidate_id: str = Path(..., description="Candidate or User ID"),
    payload: AdminUpdateCandidatePlacementRequest = ...,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_database),
) -> AdminCandidateItem:
    return await AdminCandidateService.update_candidate_placement(
        db=db,
        current_admin=current_admin,
        candidate_id=candidate_id,
        payload=payload,
    )


@router.patch(
    "/{candidate_id}/status",
    response_model=AdminCandidateItem,
    status_code=status.HTTP_200_OK,
    summary="Admin Update Candidate Account Status",
    description="Suspend or reactivate a candidate user account.",
)
async def update_candidate_status(
    candidate_id: str = Path(..., description="Candidate or User ID"),
    payload: AdminUpdateCandidateStatusRequest = ...,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_database),
) -> AdminCandidateItem:
    return await AdminCandidateService.update_candidate_status(
        db=db,
        current_admin=current_admin,
        candidate_id=candidate_id,
        payload=payload,
    )


@router.post(
    "/{candidate_id}/suspend",
    response_model=AdminCandidateItem,
    status_code=status.HTTP_200_OK,
    summary="Admin Suspend Candidate Action Alias",
    description="Action alias to suspend candidate account.",
)
async def suspend_candidate_alias(
    candidate_id: str = Path(..., description="Candidate or User ID"),
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_database),
) -> AdminCandidateItem:
    return await AdminCandidateService.update_candidate_status(
        db=db,
        current_admin=current_admin,
        candidate_id=candidate_id,
        payload=AdminUpdateCandidateStatusRequest(status="SUSPENDED", reason="Suspended by admin"),
    )


@router.post(
    "/{candidate_id}/activate",
    response_model=AdminCandidateItem,
    status_code=status.HTTP_200_OK,
    summary="Admin Activate Candidate Action Alias",
    description="Action alias to activate candidate account.",
)
async def activate_candidate_alias(
    candidate_id: str = Path(..., description="Candidate or User ID"),
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_database),
) -> AdminCandidateItem:
    return await AdminCandidateService.update_candidate_status(
        db=db,
        current_admin=current_admin,
        candidate_id=candidate_id,
        payload=AdminUpdateCandidateStatusRequest(status="ACTIVE", reason="Activated by admin"),
    )
