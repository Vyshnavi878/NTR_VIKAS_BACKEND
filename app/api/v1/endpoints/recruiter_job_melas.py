from typing import Optional, List
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_database, get_current_recruiter
from app.models.user import User
from app.schemas.job_mela import (
    JobMelaRead,
    RecruiterJobMelaItem,
    JobMelaParticipationRequest,
    JobMelaParticipationResponse,
)
from app.services.job_mela_service import JobMelaService

router = APIRouter(
    prefix="/recruiter/job-melas",
    tags=["Recruiter Job Melas"],
)


@router.get(
    "",
    response_model=List[RecruiterJobMelaItem],
    status_code=status.HTTP_200_OK,
    summary="Get recruiter Job Melas participation listing",
    description="Retrieve all Job Melas with this recruiter's company participation status, booth allocation, and metrics.",
)
async def list_recruiter_job_melas(
    status_filter: Optional[str] = Query(
        "ALL",
        alias="status",
        description="Filter by participation status: ALL, APPROVED, or PENDING",
    ),
    search: Optional[str] = Query(
        None,
        description="Search events by title, venue, city, or booth",
    ),
    current_user: User = Depends(get_current_recruiter),
    db: AsyncSession = Depends(get_database),
) -> List[RecruiterJobMelaItem]:
    """
    GET /api/v1/recruiter/job-melas
    Requires Bearer JWT token with RECRUITER role.
    """
    return await JobMelaService.get_recruiter_job_melas(
        db=db,
        current_user=current_user,
        status_filter=status_filter,
        search=search,
    )


@router.get(
    "/available",
    response_model=List[JobMelaRead],
    status_code=status.HTTP_200_OK,
    summary="Get available upcoming Job Melas for registration",
    description="Retrieve list of published and active Job Melas available for company participation.",
)
async def get_available_job_melas(
    current_user: User = Depends(get_current_recruiter),
    db: AsyncSession = Depends(get_database),
) -> List[JobMelaRead]:
    """
    GET /api/v1/recruiter/job-melas/available
    """
    return await JobMelaService.get_available_melas(db=db)


@router.post(
    "/participate",
    response_model=JobMelaParticipationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register company for a Job Mela event",
    description="Submit a company participation request for an upcoming Job Mela. Status is created strictly as PENDING.",
)
async def register_job_mela_participation(
    payload: JobMelaParticipationRequest,
    current_user: User = Depends(get_current_recruiter),
    db: AsyncSession = Depends(get_database),
) -> JobMelaParticipationResponse:
    """
    POST /api/v1/recruiter/job-melas/participate
    Requires Bearer JWT token with RECRUITER role.
    """
    return await JobMelaService.register_company_participation(
        db=db,
        current_user=current_user,
        payload=payload,
    )


@router.post(
    "/register",
    response_model=JobMelaParticipationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register company for a Job Mela event (alias)",
    description="Alias endpoint for submitting a Job Mela participation request.",
)
async def register_job_mela_participation_alias(
    payload: JobMelaParticipationRequest,
    current_user: User = Depends(get_current_recruiter),
    db: AsyncSession = Depends(get_database),
) -> JobMelaParticipationResponse:
    """
    POST /api/v1/recruiter/job-melas/register
    """
    return await JobMelaService.register_company_participation(
        db=db,
        current_user=current_user,
        payload=payload,
    )
