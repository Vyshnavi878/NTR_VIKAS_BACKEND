import os
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_database, get_current_admin
from app.models.user import User
from app.schemas.job_mela import (
    AdminParticipationItem,
    AdminApproveParticipationRequest,
    AdminRejectParticipationRequest,
    AdminJobMelaItem,
    AdminCreateJobMelaRequest,
    AdminUpdateJobMelaStatusRequest,
    AdminJobMelaCompanyItem,
    AdminJobMelaRequestItem,
    AdminApproveMelaRequest,
    AdminRejectMelaRequest,
    AdminJobMelaMetricsResponse,
)
from app.services.job_mela_service import JobMelaService

router = APIRouter(
    prefix="/admin/job-melas",
    tags=["Admin Job Melas"],
)


# ── 1. REAL AGGREGATE DASHBOARD METRICS ───────────────────────────────────────

@router.get(
    "/metrics",
    response_model=AdminJobMelaMetricsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get real Job Melas database metrics",
    description="Calculate real counts for registrations, event capacity, turnout rate, vacancies, and requests.",
)
async def get_admin_job_mela_metrics(
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_database),
) -> AdminJobMelaMetricsResponse:
    """GET /api/v1/admin/job-melas/metrics"""
    return await JobMelaService.get_job_mela_metrics(db=db)


# ── 2. OFFICIAL POSTER UPLOAD ────────────────────────────────────────────────

@router.post(
    "/upload-poster",
    status_code=status.HTTP_200_OK,
    summary="Upload official event poster flyer",
    description="Accepts JPG, PNG, WEBP up to 10MB, saves securely and returns the access URL.",
)
async def upload_admin_job_mela_poster(
    file: UploadFile = File(..., description="Official Job Mela poster flyer image (JPG/PNG/WEBP max 10MB)"),
    current_admin: User = Depends(get_current_admin),
) -> Dict[str, Any]:
    """POST /api/v1/admin/job-melas/upload-poster"""
    return await JobMelaService.upload_poster(upload_file=file)


# ── 3. JOB MELA REQUESTS GOVERNANCE ──────────────────────────────────────────

@router.get(
    "/requests",
    response_model=List[AdminJobMelaRequestItem],
    status_code=status.HTTP_200_OK,
    summary="List Job Mela requests with tabs & filters",
    description="Tabs: ALL, PENDING, APPROVED, REJECTED. Filter by organization and keyword.",
)
async def list_job_mela_requests(
    status_filter: Optional[str] = Query("ALL", alias="status", description="Status filter: ALL, PENDING, APPROVED, REJECTED"),
    company_filter: Optional[str] = Query("ALL", alias="company", description="Company / organization filter"),
    search: Optional[str] = Query(None, description="Search by title, venue, city, or organizer"),
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_database),
) -> List[AdminJobMelaRequestItem]:
    """GET /api/v1/admin/job-melas/requests"""
    return await JobMelaService.get_job_mela_requests(
        db=db,
        status_filter=status_filter,
        company_filter=company_filter,
        search=search,
    )


@router.get(
    "/requests/{request_id}",
    response_model=AdminJobMelaRequestItem,
    status_code=status.HTTP_200_OK,
    summary="Get single Job Mela request details",
)
async def get_job_mela_request_details(
    request_id: str,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_database),
) -> AdminJobMelaRequestItem:
    """GET /api/v1/admin/job-melas/requests/{request_id}"""
    return await JobMelaService.get_job_mela_request_by_id(db=db, request_id=request_id)


@router.patch(
    "/requests/{request_id}/approve",
    status_code=status.HTTP_200_OK,
    summary="Approve Job Mela request and activate event",
)
async def approve_job_mela_request(
    request_id: str,
    payload: Optional[AdminApproveMelaRequest] = None,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_database),
) -> Dict[str, Any]:
    """PATCH /api/v1/admin/job-melas/requests/{request_id}/approve"""
    return await JobMelaService.approve_job_mela_request(
        db=db,
        request_id=request_id,
        current_admin=current_admin,
        payload=payload,
    )


@router.patch(
    "/requests/{request_id}/reject",
    status_code=status.HTTP_200_OK,
    summary="Reject Job Mela request with reason",
)
async def reject_job_mela_request(
    request_id: str,
    payload: Optional[AdminRejectMelaRequest] = None,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_database),
) -> Dict[str, Any]:
    """PATCH /api/v1/admin/job-melas/requests/{request_id}/reject"""
    return await JobMelaService.reject_job_mela_request(
        db=db,
        request_id=request_id,
        current_admin=current_admin,
        payload=payload,
    )


# ── 4. COMPANY PARTICIPATION APPROVALS (EXISTING ROUTES) ─────────────────────

@router.get(
    "/participations",
    response_model=List[AdminParticipationItem],
    status_code=status.HTTP_200_OK,
    summary="List all company participation requests across Job Melas",
    description="Retrieve company participation requests with status filtering (ALL, PENDING, APPROVED, REJECTED).",
)
async def list_admin_participations(
    status_filter: Optional[str] = Query(
        "ALL",
        alias="status",
        description="Filter status: ALL, PENDING, APPROVED, REJECTED",
    ),
    search: Optional[str] = Query(
        None,
        description="Search by company name, event name, or recruiter name",
    ),
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_database),
) -> List[AdminParticipationItem]:
    """GET /api/v1/admin/job-melas/participations"""
    return await JobMelaService.get_admin_participations(
        db=db,
        status_filter=status_filter,
        search=search,
    )


@router.patch(
    "/participations/{participation_id}/approve",
    status_code=status.HTTP_200_OK,
    summary="Approve company participation request",
    description="Administrator approves a company participation and assigns corporate stall / booth.",
)
async def approve_participation(
    participation_id: str,
    payload: Optional[AdminApproveParticipationRequest] = None,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_database),
) -> Dict[str, Any]:
    """PATCH /api/v1/admin/job-melas/participations/{participation_id}/approve"""
    return await JobMelaService.approve_participation(
        db=db,
        participation_id=participation_id,
        current_admin=current_admin,
        payload=payload,
    )


@router.patch(
    "/participations/{participation_id}/reject",
    status_code=status.HTTP_200_OK,
    summary="Reject company participation request",
    description="Administrator rejects a company participation request with mandatory explanation.",
)
async def reject_participation(
    participation_id: str,
    payload: AdminRejectParticipationRequest,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_database),
) -> Dict[str, Any]:
    """PATCH /api/v1/admin/job-melas/participations/{participation_id}/reject"""
    return await JobMelaService.reject_participation(
        db=db,
        participation_id=participation_id,
        current_admin=current_admin,
        payload=payload,
    )


# ── 5. ADMIN CREATED JOB MELAS LISTING & CREATION ────────────────────────────

@router.get(
    "",
    response_model=List[AdminJobMelaItem],
    status_code=status.HTTP_200_OK,
    summary="List all Job Melas for Admin",
    description="Retrieve all Job Melas with participating companies, vacancies, candidate registrations, and status.",
)
async def list_admin_job_melas(
    status_filter: Optional[str] = Query("ALL", alias="status", description="Status filter: ALL, UPCOMING, APPROVED, ONGOING, COMPLETED"),
    search: Optional[str] = Query(None, description="Search by title, venue, city, or event ID"),
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_database),
) -> List[AdminJobMelaItem]:
    """GET /api/v1/admin/job-melas"""
    return await JobMelaService.get_admin_job_melas(
        db=db,
        status_filter=status_filter,
        search=search,
    )


@router.post(
    "",
    response_model=AdminJobMelaItem,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new Job Mela directly by Admin",
    description="Create event for state employment or directly for a client employer, persisting participating companies and job openings.",
)
async def create_admin_job_mela(
    payload: AdminCreateJobMelaRequest,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_database),
) -> AdminJobMelaItem:
    """POST /api/v1/admin/job-melas"""
    return await JobMelaService.create_admin_job_mela(
        db=db,
        payload=payload,
        current_admin=current_admin,
    )


@router.post(
    "/upload-poster",
    status_code=status.HTTP_200_OK,
    summary="Upload official event poster flyer",
    description="Validates image format (JPG, PNG, WEBP), size <= 10MB, and saves to static uploads directory.",
)
async def upload_job_mela_poster(
    file: UploadFile = File(...),
    current_admin: User = Depends(get_current_admin),
) -> Dict[str, Any]:
    """POST /api/v1/admin/job-melas/upload-poster"""
    return await JobMelaService.upload_poster(upload_file=file)


# ── 6. SINGLE JOB MELA OPERATIONS ────────────────────────────────────────────

@router.get(
    "/{mela_id}",
    response_model=AdminJobMelaItem,
    status_code=status.HTTP_200_OK,
    summary="Get single Job Mela details by ID",
)
async def get_admin_job_mela_details(
    mela_id: str,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_database),
) -> AdminJobMelaItem:
    """GET /api/v1/admin/job-melas/{mela_id}"""
    return await JobMelaService.get_admin_mela_by_id(db=db, mela_id=mela_id)


@router.patch(
    "/{mela_id}",
    response_model=AdminJobMelaItem,
    status_code=status.HTTP_200_OK,
    summary="Update existing Job Mela event details",
)
async def update_admin_job_mela(
    mela_id: str,
    payload: Dict[str, Any],
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_database),
) -> AdminJobMelaItem:
    """PATCH /api/v1/admin/job-melas/{mela_id}"""
    return await JobMelaService.update_admin_job_mela(
        db=db,
        mela_id=mela_id,
        payload=payload,
        current_admin=current_admin,
    )


@router.patch(
    "/{mela_id}/status",
    response_model=AdminJobMelaItem,
    status_code=status.HTTP_200_OK,
    summary="Update status of Job Mela (e.g. APPROVED, REJECTED, UPCOMING, COMPLETED)",
)
async def update_admin_job_mela_status(
    mela_id: str,
    payload: AdminUpdateJobMelaStatusRequest,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_database),
) -> AdminJobMelaItem:
    """PATCH /api/v1/admin/job-melas/{mela_id}/status"""
    return await JobMelaService.update_mela_status(
        db=db,
        mela_id=mela_id,
        new_status=payload.status,
        current_admin=current_admin,
    )


@router.get(
    "/{mela_id}/registrations",
    response_model=List[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="Get candidates registered for this Job Mela",
    description="Returns candidate passes, gate numbers, and entry tokens for the admin registrations modal.",
)
async def get_admin_job_mela_registrations(
    mela_id: str,
    search: Optional[str] = Query(None, description="Search by candidate name, email, or pass ID"),
    status: Optional[str] = Query("ALL", description="Filter by registration status"),
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_database),
) -> List[Dict[str, Any]]:
    """GET /api/v1/admin/job-melas/{mela_id}/registrations"""
    return await JobMelaService.get_mela_registrations_admin(
        db=db,
        mela_id=mela_id,
        search=search,
        status_filter=status,
    )


# ── 7. PARTICIPATING COMPANIES MANAGEMENT WITHIN MELA ────────────────────────

@router.post(
    "/{mela_id}/companies",
    response_model=AdminJobMelaCompanyItem,
    status_code=status.HTTP_201_CREATED,
    summary="Add participating company and role to Job Mela",
)
async def add_company_to_admin_job_mela(
    mela_id: str,
    payload: Dict[str, Any],
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_database),
) -> AdminJobMelaCompanyItem:
    """POST /api/v1/admin/job-melas/{mela_id}/companies"""
    return await JobMelaService.add_company_to_mela(
        db=db,
        mela_id=mela_id,
        payload=payload,
        current_admin=current_admin,
    )


@router.patch(
    "/{mela_id}/companies/{company_entry_id}",
    response_model=AdminJobMelaCompanyItem,
    status_code=status.HTTP_200_OK,
    summary="Update participating company details in Job Mela",
)
async def update_company_in_admin_job_mela(
    mela_id: str,
    company_entry_id: str,
    payload: Dict[str, Any],
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_database),
) -> AdminJobMelaCompanyItem:
    """PATCH /api/v1/admin/job-melas/{mela_id}/companies/{company_entry_id}"""
    return await JobMelaService.update_company_in_mela(
        db=db,
        mela_id=mela_id,
        company_entry_id=company_entry_id,
        payload=payload,
        current_admin=current_admin,
    )


@router.delete(
    "/{mela_id}/companies/{company_entry_id}",
    status_code=status.HTTP_200_OK,
    summary="Remove participating company from Job Mela",
)
async def remove_company_from_admin_job_mela(
    mela_id: str,
    company_entry_id: str,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_database),
) -> Dict[str, Any]:
    """DELETE /api/v1/admin/job-melas/{mela_id}/companies/{company_entry_id}"""
    return await JobMelaService.remove_company_from_mela(
        db=db,
        mela_id=mela_id,
        company_entry_id=company_entry_id,
        current_admin=current_admin,
    )


# ── 8. DIRECT ALIAS ROUTERS ──────────────────────────────────────────────────

# Alias router for /admin/job-mela-requests
admin_mela_requests_router = APIRouter(
    prefix="/admin/job-mela-requests",
    tags=["Admin Job Melas"],
)
admin_mela_requests_router.add_api_route(
    "",
    list_job_mela_requests,
    methods=["GET"],
    response_model=List[AdminJobMelaRequestItem],
    status_code=status.HTTP_200_OK,
    summary="List all Job Mela requests (/admin/job-mela-requests)",
)
admin_mela_requests_router.add_api_route(
    "/{request_id}",
    get_job_mela_request_details,
    methods=["GET"],
    response_model=AdminJobMelaRequestItem,
    status_code=status.HTTP_200_OK,
    summary="Get single request details (/admin/job-mela-requests/{id})",
)
admin_mela_requests_router.add_api_route(
    "/{request_id}/approve",
    approve_job_mela_request,
    methods=["PATCH"],
    status_code=status.HTTP_200_OK,
    summary="Approve request (/admin/job-mela-requests/{id}/approve)",
)
admin_mela_requests_router.add_api_route(
    "/{request_id}/reject",
    reject_job_mela_request,
    methods=["PATCH"],
    status_code=status.HTTP_200_OK,
    summary="Reject request (/admin/job-mela-requests/{id}/reject)",
)

# Alias Router for /admin/job-mela-approvals
admin_mela_approvals_router = APIRouter(
    prefix="/admin/job-mela-approvals",
    tags=["Admin Job Melas"],
)
admin_mela_approvals_router.add_api_route(
    "/participations",
    list_admin_participations,
    methods=["GET"],
    response_model=List[AdminParticipationItem],
    status_code=status.HTTP_200_OK,
    summary="List participations (/admin/job-mela-approvals/participations)",
)
admin_mela_approvals_router.add_api_route(
    "/participations/{participation_id}/approve",
    approve_participation,
    methods=["PATCH"],
    status_code=status.HTTP_200_OK,
    summary="Approve participation (/admin/job-mela-approvals/participations/{id}/approve)",
)
admin_mela_approvals_router.add_api_route(
    "/participations/{participation_id}/reject",
    reject_participation,
    methods=["PATCH"],
    status_code=status.HTTP_200_OK,
    summary="Reject participation (/admin/job-mela-approvals/participations/{id}/reject)",
)
