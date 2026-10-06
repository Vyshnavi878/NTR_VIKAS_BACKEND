"""
Public & Candidate Internship Endpoints
GET /api/v1/internships
GET /api/v1/internships/{internship_id}
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_database
from app.schemas.internship import (
    InternshipRead,
    PaginatedInternshipResponse,
)
from app.services.internship_service import InternshipService
from app.repositories.internship_repository import InternshipRepository

router = APIRouter(
    prefix="/internships",
    tags=["Internships (Public & Candidate)"],
)


@router.get(
    "",
    response_model=PaginatedInternshipResponse,
    status_code=status.HTTP_200_OK,
    summary="List published internship opportunities",
    description=(
        "Retrieve public internships. ONLY published, active (not closed) internships are returned; "
        "pending, draft, and rejected opportunities are strictly excluded."
    ),
)
async def list_published_internships(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(12, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search keyword (title, description, location)"),
    q: Optional[str] = Query(None, description="Alias for search"),
    location: Optional[str] = Query(None, description="Location filter"),
    mode: Optional[str] = Query(None, description="Work mode filter: Remote, Hybrid, On-site"),
    work_mode: Optional[str] = Query(None, description="Alias for mode"),
    duration: Optional[str] = Query(None, description="Duration filter: e.g. '3 Months', '6 Months', '1 Year'"),
    stipend_min: Optional[int] = Query(None, description="Minimum monthly stipend in INR"),
    stipend_max: Optional[int] = Query(None, description="Maximum monthly stipend in INR"),
    company_id: Optional[str] = Query(None, description="Filter by company / recruiter profile ID"),
    sort: Optional[str] = Query("latest", description="Sort: latest, oldest, stipend_high, stipend_low"),
    sort_by: Optional[str] = Query(None, description="Alias for sort"),
    sortBy: Optional[str] = Query(None, description="Alias for sort"),
    db: AsyncSession = Depends(get_database),
) -> PaginatedInternshipResponse:
    """
    GET /api/v1/internships
    Public / candidate endpoint — strictly PUBLISHED + not closed.
    """
    eff_search = search or q
    eff_mode = work_mode or mode
    eff_sort = sortBy or sort_by or sort

    return await InternshipService.get_published_internships(
        db=db,
        search=eff_search,
        location=location,
        work_mode=eff_mode,
        duration=duration,
        stipend_min=stipend_min,
        stipend_max=stipend_max,
        company_id=company_id,
        sort=eff_sort,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{internship_id}",
    response_model=InternshipRead,
    status_code=status.HTTP_200_OK,
    summary="Get published internship details",
    description="Retrieve public details for an active published internship.",
)
async def get_published_internship_detail(
    internship_id: str,
    db: AsyncSession = Depends(get_database),
) -> InternshipRead:
    """
    GET /api/v1/internships/{internship_id}
    Public / candidate endpoint.
    """
    internship = await InternshipRepository.get_internship_by_id(db, internship_id)
    if not internship or internship.status != "PUBLISHED":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Internship opportunity not found or is not currently active.",
        )

    app_count = await InternshipRepository.get_applicant_count_for_internship(
        db, internship.id, internship.internship_number
    )

    return InternshipRead(
        id=internship.id,
        internship_number=internship.internship_number,
        company_id=internship.company_id,
        company_name=internship.company.company_name if internship.company else None,
        title=internship.title,
        stipend_monthly=internship.stipend_monthly,
        stipend=internship.stipend,
        duration=internship.duration,
        work_mode=internship.work_mode,
        workMode=internship.work_mode,
        location=internship.location,
        number_of_interns=internship.number_of_interns,
        openings=internship.number_of_interns,
        description=internship.description,
        status=internship.status,
        applicantsCount=app_count,
        candidate_count=app_count,
        candidates_count=app_count,
        published_at=internship.published_at.strftime("%Y-%m-%d %H:%M:%S") if internship.published_at else None,
        postedOn=internship.created_at.strftime("%Y-%m-%d") if internship.created_at else None,
        created_at=internship.created_at.strftime("%Y-%m-%d %H:%M:%S") if internship.created_at else None,
        updated_at=internship.updated_at.strftime("%Y-%m-%d %H:%M:%S") if internship.updated_at else None,
    )
