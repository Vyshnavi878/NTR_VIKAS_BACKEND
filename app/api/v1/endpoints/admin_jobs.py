"""
Admin Job Governance Endpoints
GET  /api/v1/admin/jobs
GET  /api/v1/admin/jobs/{job_id}
POST /api/v1/admin/jobs/{job_id}/approve
POST /api/v1/admin/jobs/{job_id}/reject
"""
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_database, get_current_admin
from app.models.user import User
from app.schemas.job import (
    PaginatedJobResponse,
    AdminJobDetail,
    AdminRejectJobRequest,
)
from app.services.job_service import JobService

router = APIRouter(
    prefix="/admin/jobs",
    tags=["Admin Jobs Governance"],
)


@router.get(
    "",
    response_model=PaginatedJobResponse,
    summary="Admin List Job Requisitions",
    description="Cross-organization listing of job requisitions for compliance and governance review.",
)
async def list_admin_jobs(
    status: Optional[str] = Query(None, description="Status filter: ALL, PENDING, PUBLISHED, DRAFT, CLOSED, REJECTED"),
    department: Optional[str] = Query(None, description="Department filter"),
    search: Optional[str] = Query(None, description="Search term for title, number, company, or skills"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_database),
) -> PaginatedJobResponse:
    return await JobService.get_admin_jobs(
        db=db,
        status_filter=status or "ALL",
        department=department,
        search=search,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{job_id}",
    response_model=AdminJobDetail,
    summary="Admin Get Job Details",
    description="Returns complete requisition data including company, recruiter contact, requirements, and audit information.",
)
async def get_admin_job_details(
    job_id: str,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_database),
) -> AdminJobDetail:
    return await JobService.get_admin_job_detail(
        db=db,
        job_identifier=job_id,
    )


@router.post(
    "/{job_id}/approve",
    response_model=Dict[str, Any],
    summary="Admin Approve Job Requisition",
    description="Approves a PENDING job requisition. Sets status to PUBLISHED, records approved_at and approved_by, logs audit event, and sends recruiter notification.",
)
async def approve_job(
    job_id: str,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_database),
) -> Dict[str, Any]:
    return await JobService.approve_job(
        db=db,
        current_admin=current_admin,
        job_identifier=job_id,
    )


@router.post(
    "/{job_id}/reject",
    response_model=Dict[str, Any],
    summary="Admin Reject Job Requisition",
    description="Rejects a job requisition with a mandatory reason. Sets status to REJECTED, records rejection audit event, and notifies recruiter.",
)
async def reject_job(
    job_id: str,
    payload: AdminRejectJobRequest,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_database),
) -> Dict[str, Any]:
    return await JobService.reject_job(
        db=db,
        current_admin=current_admin,
        job_identifier=job_id,
        reason=payload.reason,
    )
