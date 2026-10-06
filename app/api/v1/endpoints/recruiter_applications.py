"""
Recruiter Applications Endpoints.
Canonical APIs for recruiter application management:
GET   /api/v1/recruiter/applications
GET   /api/v1/recruiter/applications/{application_id}
PATCH /api/v1/recruiter/applications/{application_id}/status
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_database, get_current_recruiter
from app.models.user import User
from app.schemas.recruiter_application import (
    RecruiterApplicationsResponse,
    RecruiterApplicationDetail,
    ApplicationStatusUpdateRequest,
)
from app.services.recruiter_application_service import RecruiterApplicationService

router = APIRouter(
    prefix="/recruiter/applications",
    tags=["Recruiter Applications"],
)

recruiters_plural_router = APIRouter(
    prefix="/recruiters/applications",
    tags=["Recruiter Applications"],
)


# ── 1. List Applications ───────────────────────────────────────────────────────
@router.get(
    "",
    response_model=RecruiterApplicationsResponse,
    status_code=status.HTTP_200_OK,
    summary="List Recruiter Applications",
    description="Retrieve paginated applications belonging to the authenticated recruiter's organization. Supports search, job filtering, status filtering, sorting, and summary metrics.",
)
async def list_recruiter_applications(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(9, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search across candidate name, email, application number, role, etc."),
    job_id: Optional[str] = Query(None, description="Filter by job ID or slug (e.g. JOB-101)"),
    status: Optional[str] = Query(None, description="Filter by application status (e.g. SCREENING, SHORTLISTED, INTERVIEW, SELECTED, REJECTED)"),
    sort_by: Optional[str] = Query("newest", description="Sort field: newest, oldest, match/match_score"),
    sort_order: Optional[str] = Query("desc", description="Sort direction: asc or desc"),
    application_type: Optional[str] = Query(None, description="Filter by application type: DIRECT or JOB_MELA"),
    current_user: User = Depends(get_current_recruiter),
    db: AsyncSession = Depends(get_database),
) -> RecruiterApplicationsResponse:
    return await RecruiterApplicationService.list_applications(
        db=db,
        current_user=current_user,
        page=page,
        page_size=page_size,
        search=search,
        job_id=job_id,
        status=status,
        application_type=application_type,
        sort_by=sort_by,
        sort_order=sort_order,
    )


# ── 2. Get Application Detail ──────────────────────────────────────────────────
@router.get(
    "/{application_id}",
    response_model=RecruiterApplicationDetail,
    status_code=status.HTTP_200_OK,
    summary="Get Application Details",
    description="Retrieve complete dossier of an application including candidate profile, resume, timeline events, and interview status. IDOR protected.",
)
async def get_recruiter_application_detail(
    application_id: str,
    current_user: User = Depends(get_current_recruiter),
    db: AsyncSession = Depends(get_database),
) -> RecruiterApplicationDetail:
    return await RecruiterApplicationService.get_application_detail(
        db=db,
        current_user=current_user,
        application_id=application_id,
    )


# ── 3. Update Application Status ───────────────────────────────────────────────
@router.patch(
    "/{application_id}/status",
    response_model=RecruiterApplicationDetail,
    status_code=status.HTTP_200_OK,
    summary="Update Application Status",
    description="Advance or reject candidate application (e.g., SCREENING, SHORTLISTED, INTERVIEW, SELECTED, REJECTED). Automatically logs timeline event and notifies candidate.",
)
async def update_recruiter_application_status(
    application_id: str,
    payload: ApplicationStatusUpdateRequest,
    current_user: User = Depends(get_current_recruiter),
    db: AsyncSession = Depends(get_database),
) -> RecruiterApplicationDetail:
    return await RecruiterApplicationService.update_application_status(
        db=db,
        current_user=current_user,
        application_id=application_id,
        new_status=payload.status,
        notes=payload.notes,
    )


# ── Plural routes forwarding ──────────────────────────────────────────────────
@recruiters_plural_router.get("", response_model=RecruiterApplicationsResponse, include_in_schema=False)
async def list_recruiters_applications_plural(
    page: int = Query(1, ge=1),
    page_size: int = Query(9, ge=1, le=100),
    search: Optional[str] = Query(None),
    job_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    sort_by: Optional[str] = Query("newest"),
    sort_order: Optional[str] = Query("desc"),
    application_type: Optional[str] = Query(None),
    current_user: User = Depends(get_current_recruiter),
    db: AsyncSession = Depends(get_database),
) -> RecruiterApplicationsResponse:
    return await list_recruiter_applications(
        page=page,
        page_size=page_size,
        search=search,
        job_id=job_id,
        status=status,
        sort_by=sort_by,
        sort_order=sort_order,
        application_type=application_type,
        current_user=current_user,
        db=db,
    )


@recruiters_plural_router.get("/{application_id}", response_model=RecruiterApplicationDetail, include_in_schema=False)
async def get_recruiters_application_detail_plural(
    application_id: str,
    current_user: User = Depends(get_current_recruiter),
    db: AsyncSession = Depends(get_database),
) -> RecruiterApplicationDetail:
    return await get_recruiter_application_detail(
        application_id=application_id,
        current_user=current_user,
        db=db,
    )


@recruiters_plural_router.patch("/{application_id}/status", response_model=RecruiterApplicationDetail, include_in_schema=False)
async def update_recruiters_application_status_plural(
    application_id: str,
    payload: ApplicationStatusUpdateRequest,
    current_user: User = Depends(get_current_recruiter),
    db: AsyncSession = Depends(get_database),
) -> RecruiterApplicationDetail:
    return await update_recruiter_application_status(
        application_id=application_id,
        payload=payload,
        current_user=current_user,
        db=db,
    )
