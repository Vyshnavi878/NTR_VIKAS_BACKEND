from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_database, get_current_admin
from app.models.user import User
from app.schemas.job_mela import (
    AdminParticipationItem,
    AdminApproveParticipationRequest,
    AdminRejectParticipationRequest,
)
from app.services.job_mela_service import JobMelaService

router = APIRouter(
    prefix="/admin/job-melas",
    tags=["Admin Job Melas"],
)


@router.get(
    "/participations",
    response_model=List[AdminParticipationItem],
    status_code=status.HTTP_200_OK,
    summary="List all company participation requests across Job Melas",
    description="Retrieve company participation requests with status filtering (ALL, PENDING, APPROVED, REJECTED).",
)
async def list_admin_participations(
    status_filter: Optional[str] = Query(
        "ALL",
        alias="status",
        description="Filter status: ALL, PENDING, APPROVED, REJECTED",
    ),
    search: Optional[str] = Query(
        None,
        description="Search by company name, event name, or recruiter name",
    ),
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_database),
) -> List[AdminParticipationItem]:
    """
    GET /api/v1/admin/job-melas/participations
    Requires Bearer JWT token with ADMIN role.
    """
    return await JobMelaService.get_admin_participations(
        db=db,
        status_filter=status_filter,
        search=search,
    )


@router.patch(
    "/participations/{participation_id}/approve",
    status_code=status.HTTP_200_OK,
    summary="Approve company participation request",
    description="Administrator approves a company participation and assigns corporate stall / booth.",
)
async def approve_participation(
    participation_id: str,
    payload: Optional[AdminApproveParticipationRequest] = None,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_database),
) -> Dict[str, Any]:
    """
    PATCH /api/v1/admin/job-melas/participations/{participation_id}/approve
    Requires Bearer JWT token with ADMIN role.
    """
    return await JobMelaService.approve_participation(
        db=db,
        participation_id=participation_id,
        current_admin=current_admin,
        payload=payload,
    )


@router.patch(
    "/participations/{participation_id}/reject",
    status_code=status.HTTP_200_OK,
    summary="Reject company participation request",
    description="Administrator rejects a company participation request with mandatory explanation.",
)
async def reject_participation(
    participation_id: str,
    payload: AdminRejectParticipationRequest,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_database),
) -> Dict[str, Any]:
    """
    PATCH /api/v1/admin/job-melas/participations/{participation_id}/reject
    Requires Bearer JWT token with ADMIN role.
    """
    return await JobMelaService.reject_participation(
        db=db,
        participation_id=participation_id,
        current_admin=current_admin,
        payload=payload,
    )
