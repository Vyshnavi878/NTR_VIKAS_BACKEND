"""
Candidate Applications Endpoints
GET /api/v1/candidate/applications
GET /api/v1/candidate/applications/{application_id}
GET /api/v1/candidate/applications/{application_id}/timeline

Authentication:  Bearer JWT (CANDIDATE role only)
Authorization:   Identity derived exclusively from verified JWT bearer token.
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_database, get_current_candidate
from app.models.user import User
from app.schemas.candidate_application import (
    CandidateApplicationsListResponse,
    CandidateApplicationItem,
    ApplicationTimelineResponse,
    CandidateApplicationCreate,
)
from app.services.candidate_application_service import CandidateApplicationService

router = APIRouter(
    prefix="/candidate/applications",
    tags=["Candidate Applications"],
)


@router.get(
    "",
    response_model=CandidateApplicationsListResponse,
    summary="Get Candidate Applications",
    description="Returns all job applications and status counts belonging to the authenticated candidate.",
)
async def get_candidate_applications(
    status: Optional[str] = Query(
        None, description="Optional status filter: APPLIED, SCREENING, SHORTLISTED, INTERVIEW, SELECTED, REJECTED, ALL"
    ),
    search: Optional[str] = Query(
        None, description="Optional search term matching role, company, location, or application number"
    ),
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_database),
) -> CandidateApplicationsListResponse:
    """
    GET /api/v1/candidate/applications
    Derives candidate identity from JWT token. Returns status counts and applications.
    """
    return await CandidateApplicationService.get_applications(
        db, current_user, status_filter=status, search=search
    )


@router.post(
    "",
    response_model=CandidateApplicationItem,
    status_code=status.HTTP_201_CREATED,
    summary="Apply for a Job",
    description="Creates a new application for the authenticated candidate. Verifies candidate identity from JWT, checks for duplicates, and generates initial timeline event.",
)
async def apply_for_job(
    data: CandidateApplicationCreate,
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_database),
) -> CandidateApplicationItem:
    """
    POST /api/v1/candidate/applications
    Derives candidate identity from JWT token. Returns created application.
    """
    return await CandidateApplicationService.create_application(
        db, current_user, data
    )



@router.get(
    "/{application_id}",
    response_model=CandidateApplicationItem,
    summary="Get Application Details",
    description="Returns detailed information for a single application. Verifies candidate ownership.",
)
async def get_application_details(
    application_id: str,
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_database),
) -> CandidateApplicationItem:
    """
    GET /api/v1/candidate/applications/{application_id}
    Verifies that the application belongs to the current candidate before returning.
    """
    return await CandidateApplicationService.get_application_details(
        db, current_user, application_id
    )


@router.get(
    "/{application_id}/timeline",
    response_model=ApplicationTimelineResponse,
    summary="Get Application Timeline",
    description="Returns chronological status history and milestones for an application. Verifies candidate ownership.",
)
async def get_application_timeline(
    application_id: str,
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_database),
) -> ApplicationTimelineResponse:
    """
    GET /api/v1/candidate/applications/{application_id}/timeline
    Verifies candidate ownership and returns step-by-step milestones.
    """
    return await CandidateApplicationService.get_application_timeline(
        db, current_user, application_id
    )
