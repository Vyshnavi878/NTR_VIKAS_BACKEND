"""
Candidate Saved Jobs Endpoints
GET    /api/v1/candidate/saved-jobs
POST   /api/v1/candidate/saved-jobs
DELETE /api/v1/candidate/saved-jobs/{identifier}

Authentication:  Bearer JWT (CANDIDATE role only)
Authorization:   Derived strictly from verified token identity.
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_database, get_current_candidate
from app.models.user import User
from app.schemas.saved_job import (
    SavedJobsListResponse,
    SaveJobRequest,
    SavedJobActionResponse,
    SavedJobDeleteResponse,
)
from app.services.saved_job_service import SavedJobService

router = APIRouter(
    prefix="/candidate/saved-jobs",
    tags=["Candidate Saved Jobs"],
)


@router.get(
    "",
    response_model=SavedJobsListResponse,
    summary="Get Candidate Saved Jobs",
    description="Returns all jobs bookmarked by the authenticated candidate.",
)
async def get_saved_jobs(
    search: Optional[str] = Query(
        None, description="Optional search term matching title, company, or city"
    ),
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_database),
) -> SavedJobsListResponse:
    """
    GET /api/v1/candidate/saved-jobs
    Identity is derived from JWT token to ensure candidates only see their own saved jobs.
    """
    return await SavedJobService.get_saved_jobs(db, current_user, search=search)


@router.post(
    "",
    response_model=SavedJobActionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Save a Job",
    description="Bookmarks a job for the authenticated candidate. Prevents duplicate saves.",
)
async def save_job(
    payload: SaveJobRequest,
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_database),
) -> SavedJobActionResponse:
    """
    POST /api/v1/candidate/saved-jobs
    Saves a job for the current authenticated candidate.
    """
    return await SavedJobService.save_job(db, current_user, payload)


@router.delete(
    "/{identifier}",
    response_model=SavedJobDeleteResponse,
    summary="Remove a Saved Job",
    description="Deletes a saved job by its saved_job_id or job_id. Verifies candidate ownership.",
)
async def delete_saved_job(
    identifier: str,
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_database),
) -> SavedJobDeleteResponse:
    """
    DELETE /api/v1/candidate/saved-jobs/{identifier}
    Verifies that the saved job belongs to the current candidate before deleting.
    """
    return await SavedJobService.delete_saved_job(db, current_user, identifier)
