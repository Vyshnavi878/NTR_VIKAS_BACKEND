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
    search: Optional[str] = Query(None, description="Search term matching title, description, skills, company name, department, or industry"),
    q: Optional[str] = Query(None, description="Alias for search query"),
    location: Optional[str] = Query(None, description="Location filter"),
    experience_level: Optional[str] = Query(None, description="Experience level filter: Fresher, 1-3 years, 3-5 years, etc."),
    experience: Optional[str] = Query(None, description="Alias for experience_level"),
    salary_min: Optional[int] = Query(None, description="Minimum salary in INR or LPA"),
    salary_max: Optional[int] = Query(None, description="Maximum salary in INR or LPA"),
    salary_range: Optional[str] = Query(None, description="Salary range filter string e.g. '₹6 - ₹10 LPA'"),
    salary: Optional[str] = Query(None, description="Alias for salary_range"),
    work_mode: Optional[str] = Query(None, description="Work mode filter: On-site, Hybrid, Remote"),
    mode: Optional[str] = Query(None, description="Alias for work_mode"),
    employment_type: Optional[str] = Query(None, description="Employment type filter: Full-time, Part-time, Contract, Internship"),
    job_type: Optional[str] = Query(None, description="Alias for employment_type"),
    required_skill: Optional[str] = Query(None, description="Required skill filter: React, Python, AWS, etc."),
    skill: Optional[str] = Query(None, description="Alias for required_skill"),
    industry_sector: Optional[str] = Query(None, description="Industry sector filter"),
    industry: Optional[str] = Query(None, description="Alias for industry_sector"),
    department: Optional[str] = Query(None, description="Department / functional area filter"),
    sort: Optional[str] = Query("relevance", description="Sorting: relevance, newest, oldest, salary_high, salary_low"),
    sort_by: Optional[str] = Query(None, description="Alias for sort"),
    sortBy: Optional[str] = Query(None, description="Alias for sort"),
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=100),
    current_user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_database),
) -> PaginatedJobResponse:
    eff_search = search or q
    eff_exp = experience_level or experience
    eff_salary_range = salary_range or salary
    eff_work_mode = work_mode or mode
    eff_emp_type = employment_type or job_type
    eff_skill = required_skill or skill
    eff_industry = industry_sector or industry
    eff_sort = sortBy or sort_by or sort

    return await JobService.get_published_jobs(
        db=db,
        search=eff_search,
        department=department,
        location=location,
        experience_level=eff_exp,
        salary_min=salary_min,
        salary_max=salary_max,
        salary_range=eff_salary_range,
        work_mode=eff_work_mode,
        employment_type=eff_emp_type,
        required_skill=eff_skill,
        industry_sector=eff_industry,
        sort=eff_sort,
        page=page,
        page_size=page_size,
        current_user=current_user,
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
