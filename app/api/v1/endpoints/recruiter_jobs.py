"""
Recruiter Job Postings Endpoints
GET  /api/v1/recruiters/jobs (and /recruiter/jobs)
POST /api/v1/recruiters/jobs
POST /api/v1/recruiters/jobs/draft
POST /api/v1/recruiters/jobs/{id}/close
PUT  /api/v1/recruiters/jobs/{id}
GET  /api/v1/recruiters/jobs/{id}
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_database, get_current_recruiter
from app.models.user import User
from app.schemas.job import (
    JobCreate,
    JobUpdate,
    JobRead,
    PaginatedJobResponse,
)
from app.services.job_service import JobService

router = APIRouter(
    prefix="/recruiters/jobs",
    tags=["Recruiter Jobs"],
)

recruiter_singular_router = APIRouter(
    prefix="/recruiter/jobs",
    tags=["Recruiter Jobs"],
)


@router.get(
    "",
    response_model=PaginatedJobResponse,
    summary="List Recruiter Job Postings",
    description="Returns paginated jobs belonging to the authenticated recruiter's organization with status tabs, search, and department filters.",
)
async def list_recruiter_jobs(
    status: Optional[str] = Query(None, description="Status filter: ALL, ACTIVE, PUBLISHED, PENDING, DRAFT, CLOSED, REJECTED"),
    department: Optional[str] = Query(None, description="Department filter"),
    search: Optional[str] = Query(None, description="Search term for title, number, location, skill"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_recruiter),
    db: AsyncSession = Depends(get_database),
) -> PaginatedJobResponse:
    return await JobService.get_recruiter_jobs(
        db=db,
        current_user=current_user,
        status_filter=status or "ALL",
        department=department,
        search=search,
        page=page,
        page_size=page_size,
    )


@router.post(
    "",
    response_model=JobRead,
    status_code=status.HTTP_201_CREATED,
    summary="Submit Job for Admin Approval",
    description="Submits a new job requisition. Server assigns sequential JOB-XXX number and sets status strictly to PENDING for admin review.",
)
async def submit_job_for_approval(
    data: JobCreate,
    current_user: User = Depends(get_current_recruiter),
    db: AsyncSession = Depends(get_database),
) -> JobRead:
    return await JobService.create_job(
        db=db,
        current_user=current_user,
        data=data,
        as_draft=False,
    )


@router.post(
    "/draft",
    response_model=JobRead,
    status_code=status.HTTP_201_CREATED,
    summary="Save Job Draft",
    description="Saves a job requisition as DRAFT. Not submitted for approval and not visible to candidates.",
)
async def save_job_draft(
    data: JobCreate,
    current_user: User = Depends(get_current_recruiter),
    db: AsyncSession = Depends(get_database),
) -> JobRead:
    return await JobService.create_job(
        db=db,
        current_user=current_user,
        data=data,
        as_draft=True,
    )


@router.post(
    "/{job_id}/close",
    response_model=JobRead,
    summary="Close Job Posting",
    description="Closes an active job posting. Closed jobs remain visible to recruiter under Closed tab, but candidates cannot apply.",
)
async def close_job(
    job_id: str,
    current_user: User = Depends(get_current_recruiter),
    db: AsyncSession = Depends(get_database),
) -> JobRead:
    return await JobService.close_job(
        db=db,
        current_user=current_user,
        job_identifier=job_id,
    )


@router.put(
    "/{job_id}",
    response_model=JobRead,
    summary="Update Job Posting",
    description="Update an existing job posting. If published job undergoes material changes, status returns to PENDING.",
)
async def update_job(
    job_id: str,
    data: JobUpdate,
    current_user: User = Depends(get_current_recruiter),
    db: AsyncSession = Depends(get_database),
) -> JobRead:
    return await JobService.update_job(
        db=db,
        current_user=current_user,
        job_identifier=job_id,
        data=data,
    )


@router.get(
    "/{job_id}",
    response_model=JobRead,
    summary="Get Recruiter Job Detail",
    description="Returns detailed job information for recruiter.",
)
async def get_recruiter_job_detail(
    job_id: str,
    current_user: User = Depends(get_current_recruiter),
    db: AsyncSession = Depends(get_database),
) -> JobRead:
    return await JobService.get_job_public_or_authenticated(
        db=db,
        job_identifier=job_id,
        current_user=current_user,
    )


@router.post(
    "/{job_id}/submit",
    response_model=JobRead,
    summary="Submit Draft Job for Admin Approval",
    description="Submits a draft or rejected job opening for Administrator review. Status transitions to PENDING.",
)
async def submit_draft_job(
    job_id: str,
    current_user: User = Depends(get_current_recruiter),
    db: AsyncSession = Depends(get_database),
) -> JobRead:
    return await JobService.submit_draft_job(
        db=db,
        current_user=current_user,
        job_identifier=job_id,
    )


# ── Register routes on singular prefix /recruiter/jobs as well ──────────────
recruiter_singular_router.add_api_route(
    "", list_recruiter_jobs, methods=["GET"], response_model=PaginatedJobResponse, summary="List Recruiter Job Postings"
)
recruiter_singular_router.add_api_route(
    "", submit_job_for_approval, methods=["POST"], response_model=JobRead, status_code=status.HTTP_201_CREATED, summary="Submit Job for Approval"
)
recruiter_singular_router.add_api_route(
    "/draft", save_job_draft, methods=["POST"], response_model=JobRead, status_code=status.HTTP_201_CREATED, summary="Save Job Draft"
)
recruiter_singular_router.add_api_route(
    "/{job_id}/submit", submit_draft_job, methods=["POST"], response_model=JobRead, summary="Submit Draft Job for Approval"
)
recruiter_singular_router.add_api_route(
    "/{job_id}/close", close_job, methods=["POST"], response_model=JobRead, summary="Close Job Posting"
)
recruiter_singular_router.add_api_route(
    "/{job_id}", update_job, methods=["PUT"], response_model=JobRead, summary="Update Job Posting"
)
recruiter_singular_router.add_api_route(
    "/{job_id}", get_recruiter_job_detail, methods=["GET"], response_model=JobRead, summary="Get Job Detail"
)

