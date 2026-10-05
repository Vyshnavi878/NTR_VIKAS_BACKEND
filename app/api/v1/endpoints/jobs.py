"""
Public & Candidate Job Postings Endpoints
GET /api/v1/jobs
GET /api/v1/jobs/{job_id}
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_database, get_optional_user
from app.models.user import User
from app.schemas.job import (
    PaginatedJobResponse,
    JobRead,
)
from app.services.job_service import JobService

router = APIRouter(
    prefix="/jobs",
    tags=["Jobs (Public & Candidate)"],
)


@router.get(
    "",
    response_model=PaginatedJobResponse,
    summary="List Published Job Postings",
    description="Returns public job postings. Strictly restricted to PUBLISHED jobs only — DRAFT, PENDING, and REJECTED jobs are never exposed to candidates.",
)
async def list_published_jobs(
    search: Optional[str] = Query(None, description="Search term for title, department, location, or skill"),
    department: Optional[str] = Query(None, description="Department filter"),
    location: Optional[str] = Query(None, description="Location filter"),
    work_mode: Optional[str] = Query(None, description="Work mode filter: On-site, Hybrid, Remote"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_database),
) -> PaginatedJobResponse:
    return await JobService.get_published_jobs(
        db=db,
        search=search,
        department=department,
        location=location,
        work_mode=work_mode,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{job_id}",
    response_model=JobRead,
    summary="Get Job Details",
    description="Returns full job requisition details. Public users and candidates can only view PUBLISHED jobs.",
)
async def get_job_detail(
    job_id: str,
    current_user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_database),
) -> JobRead:
    return await JobService.get_job_public_or_authenticated(
        db=db,
        job_identifier=job_id,
        current_user=current_user,
    )
