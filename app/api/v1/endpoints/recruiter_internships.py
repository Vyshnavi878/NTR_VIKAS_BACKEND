from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_database, get_current_recruiter
from app.models.user import User
from app.schemas.internship import (
    InternshipCreate,
    InternshipRead,
    PaginatedInternshipResponse,
)
from app.services.internship_service import InternshipService

router = APIRouter(
    prefix="/recruiters/internships",
    tags=["Recruiter Internships"],
)

# Secondary router for /recruiter/internships alias
recruiter_singular_router = APIRouter(
    prefix="/recruiter/internships",
    tags=["Recruiter Internships"],
)


@router.get(
    "",
    response_model=PaginatedInternshipResponse,
    status_code=status.HTTP_200_OK,
    summary="Get recruiter internship opportunities",
    description="Retrieve paginated list of internships posted by the authenticated recruiter's company.",
)
@recruiter_singular_router.get(
    "",
    response_model=PaginatedInternshipResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def list_recruiter_internships(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    status: Optional[str] = Query("ALL", description="Filter by status: ALL, PENDING, PUBLISHED, DRAFT, CLOSED"),
    search: Optional[str] = Query(None, description="Search by title, internship number, location, etc."),
    current_user: User = Depends(get_current_recruiter),
    db: AsyncSession = Depends(get_database),
) -> PaginatedInternshipResponse:
    """
    GET /api/v1/recruiters/internships
    Requires Bearer JWT token with RECRUITER role.
    """
    return await InternshipService.get_recruiter_internships(
        db=db,
        current_user=current_user,
        status_filter=status,
        search=search,
        page=page,
        page_size=page_size,
    )


@router.post(
    "",
    response_model=InternshipRead,
    status_code=status.HTTP_201_CREATED,
    summary="Post new internship opportunity for approval",
    description="Recruiter submits a new internship program. Initial status is created strictly as PENDING awaiting admin review.",
)
@recruiter_singular_router.post(
    "",
    response_model=InternshipRead,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
async def create_internship(
    payload: InternshipCreate,
    current_user: User = Depends(get_current_recruiter),
    db: AsyncSession = Depends(get_database),
) -> InternshipRead:
    """
    POST /api/v1/recruiters/internships
    Requires Bearer JWT token with RECRUITER role.
    """
    return await InternshipService.create_internship(
        db=db,
        current_user=current_user,
        payload=payload,
        initial_status="PENDING",
    )


@router.post(
    "/draft",
    response_model=InternshipRead,
    status_code=status.HTTP_201_CREATED,
    summary="Save internship opportunity as draft",
    description="Save a private draft internship program.",
)
@recruiter_singular_router.post(
    "/draft",
    response_model=InternshipRead,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
async def save_internship_draft(
    payload: InternshipCreate,
    current_user: User = Depends(get_current_recruiter),
    db: AsyncSession = Depends(get_database),
) -> InternshipRead:
    """
    POST /api/v1/recruiters/internships/draft
    """
    return await InternshipService.create_internship(
        db=db,
        current_user=current_user,
        payload=payload,
        initial_status="DRAFT",
    )


@router.post(
    "/{internship_id}/close",
    response_model=InternshipRead,
    status_code=status.HTTP_200_OK,
    summary="Close an active published internship",
    description="Recruiter closes a published internship requisition.",
)
@recruiter_singular_router.post(
    "/{internship_id}/close",
    response_model=InternshipRead,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def close_internship(
    internship_id: str,
    current_user: User = Depends(get_current_recruiter),
    db: AsyncSession = Depends(get_database),
) -> InternshipRead:
    """
    POST /api/v1/recruiters/internships/{internship_id}/close
    """
    return await InternshipService.close_internship(
        db=db,
        current_user=current_user,
        internship_id=internship_id,
    )


@router.post(
    "/{internship_id}/submit",
    response_model=InternshipRead,
    status_code=status.HTTP_200_OK,
    summary="Submit draft or rejected internship for approval",
    description="Recruiter submits a draft or rejected internship program for Administrator review.",
)
@recruiter_singular_router.post(
    "/{internship_id}/submit",
    response_model=InternshipRead,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def submit_draft_internship(
    internship_id: str,
    current_user: User = Depends(get_current_recruiter),
    db: AsyncSession = Depends(get_database),
) -> InternshipRead:
    """
    POST /api/v1/recruiters/internships/{internship_id}/submit
    """
    return await InternshipService.submit_draft_internship(
        db=db,
        current_user=current_user,
        internship_id=internship_id,
    )

