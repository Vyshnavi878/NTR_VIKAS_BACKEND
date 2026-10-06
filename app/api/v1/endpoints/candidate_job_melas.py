from typing import Optional, List
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_database, get_current_candidate, get_optional_user
from app.models.user import User
from app.schemas.job_mela import (
    CandidateJobMelasListResponse,
    CandidateJobMelaCard,
    CandidateJobMelaRegistrationRequest,
    CandidateJobMelaRegistrationItem,
    CandidateJobMelaApplyCompanyRequest,
    CandidateJobMelaApplyCompanyResponse,
    CandidateMelaCompanyItem,
)
from app.services.job_mela_service import JobMelaService

router = APIRouter(
    prefix="/candidate/job-melas",
    tags=["Candidate Job Melas"],
)


@router.get(
    "",
    response_model=CandidateJobMelasListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Job Melas for Candidates",
    description="Retrieve all eligible and published Job Melas (Admin-created and approved Recruiter-created) with category counts, search, and candidate registration status.",
)
async def list_candidate_job_melas(
    status: Optional[str] = Query(
        "ALL",
        description="Filter status: ALL, UPCOMING, ONGOING, COMPLETED",
    ),
    search: Optional[str] = Query(
        None,
        description="Search by event title, venue, city, or district",
    ),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(12, ge=1, le=100, description="Page size"),
    current_user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_database),
) -> CandidateJobMelasListResponse:
    """
    GET /api/v1/candidate/job-melas
    Unified endpoint for candidate Job Melas tracker.
    """
    return await JobMelaService.get_candidate_job_melas(
        db=db,
        current_user=current_user,
        status_filter=status,
        search=search,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/registrations",
    response_model=List[CandidateJobMelaRegistrationItem],
    status_code=status.HTTP_200_OK,
    summary="Get Candidate's Registered Event Passes",
    description="Retrieve all Job Mela event passes registered by the authenticated candidate.",
)
async def get_candidate_registrations(
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_database),
) -> List[CandidateJobMelaRegistrationItem]:
    """
    GET /api/v1/candidate/job-melas/registrations
    Requires Bearer JWT token with CANDIDATE role.
    """
    return await JobMelaService.get_candidate_registrations(
        db=db, current_user=current_user
    )


@router.post(
    "/{job_mela_id}/register",
    response_model=CandidateJobMelaRegistrationItem,
    status_code=status.HTTP_201_CREATED,
    summary="Register Candidate for Job Mela",
    description="Register authenticated candidate for a Job Mela event, generate digital QR fast-track pass, and track in My Applications.",
)
async def register_candidate_for_job_mela(
    job_mela_id: str,
    payload: Optional[CandidateJobMelaRegistrationRequest] = None,
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_database),
) -> CandidateJobMelaRegistrationItem:
    """
    POST /api/v1/candidate/job-melas/{job_mela_id}/register
    Requires Bearer JWT token with CANDIDATE role.
    Enforces duplicate prevention at backend/database level.
    """
    return await JobMelaService.register_candidate_for_mela(
        db=db,
        current_user=current_user,
        job_mela_id=job_mela_id,
        payload=payload,
    )


@router.get(
    "/registrations/{registration_id}",
    response_model=CandidateJobMelaRegistrationItem,
    status_code=status.HTTP_200_OK,
    summary="Get Specific Event Pass Details",
    description="Retrieve pass details and QR entry token for a registered Job Mela (verifies ownership).",
)
async def get_registration_details(
    registration_id: str,
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_database),
) -> CandidateJobMelaRegistrationItem:
    """
    GET /api/v1/candidate/job-melas/registrations/{registration_id}
    """
    return await JobMelaService.get_candidate_registration_pass(
        db=db,
        current_user=current_user,
        registration_id=registration_id,
    )


@router.get(
    "/registrations/{registration_id}/pass",
    response_model=CandidateJobMelaRegistrationItem,
    status_code=status.HTTP_200_OK,
    summary="Get Digital QR Entry Pass",
    description="Retrieve Digital QR Entry Pass and badge metadata.",
)
async def get_digital_qr_pass(
    registration_id: str,
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_database),
) -> CandidateJobMelaRegistrationItem:
    """
    GET /api/v1/candidate/job-melas/registrations/{registration_id}/pass
    """
    return await JobMelaService.get_candidate_registration_pass(
        db=db,
        current_user=current_user,
        registration_id=registration_id,
    )


@router.post(
    "/{job_mela_id}/apply-company",
    response_model=CandidateJobMelaApplyCompanyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Apply for specific company in a Job Mela",
    description="Submit walk-in application for a specific company and role within a Job Mela.",
)
async def apply_to_mela_company(
    job_mela_id: str,
    payload: CandidateJobMelaApplyCompanyRequest,
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_database),
) -> CandidateJobMelaApplyCompanyResponse:
    """
    POST /api/v1/candidate/job-melas/{job_mela_id}/apply-company
    """
    return await JobMelaService.apply_candidate_to_mela_company(
        db=db,
        current_user=current_user,
        job_mela_id=job_mela_id,
        payload=payload,
    )


@router.get(
    "/{job_mela_id}",
    response_model=CandidateJobMelaCard,
    status_code=status.HTTP_200_OK,
    summary="Get Job Mela Details for Candidate",
    description="Retrieve full details of a single Job Mela including participating companies, open roles, and candidate registration status.",
)
async def get_candidate_job_mela_detail(
    job_mela_id: str,
    current_user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_database),
) -> CandidateJobMelaCard:
    """
    GET /api/v1/candidate/job-melas/{job_mela_id}
    """
    return await JobMelaService.get_candidate_job_mela_detail(
        db=db,
        job_mela_id=job_mela_id,
        current_user=current_user,
    )
