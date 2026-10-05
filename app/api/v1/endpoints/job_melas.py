from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_database
from app.schemas.job_mela import JobMelaRead, CandidateMelaCompanyItem
from app.services.job_mela_service import JobMelaService

router = APIRouter(
    prefix="/job-melas",
    tags=["Job Melas"],
)


@router.get(
    "",
    response_model=List[JobMelaRead],
    status_code=status.HTTP_200_OK,
    summary="List published Job Melas",
    description="Retrieve all active and published Job Mela events.",
)
async def list_job_melas(
    db: AsyncSession = Depends(get_database),
) -> List[JobMelaRead]:
    """
    GET /api/v1/job-melas
    Public / candidate endpoint.
    """
    return await JobMelaService.get_available_melas(db=db)


@router.get(
    "/{job_mela_id}/companies",
    response_model=List[CandidateMelaCompanyItem],
    status_code=status.HTTP_200_OK,
    summary="Get approved companies participating in a Job Mela",
    description="Retrieve approved companies, their open positions, and allocated stalls for candidates.",
)
async def get_approved_companies(
    job_mela_id: str,
    db: AsyncSession = Depends(get_database),
) -> List[CandidateMelaCompanyItem]:
    """
    GET /api/v1/job-melas/{job_mela_id}/companies
    Public / candidate endpoint.
    """
    return await JobMelaService.get_approved_mela_companies(
        db=db, job_mela_id=job_mela_id
    )
