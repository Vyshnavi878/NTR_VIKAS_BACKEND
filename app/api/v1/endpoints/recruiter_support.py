from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_database, get_current_recruiter
from app.models.user import User
from app.schemas.recruiter_support import (
    RecruiterSupportRequestCreate,
    RecruiterSupportRequestResponse,
    RecruiterSupportRequestListResponse,
)
from app.services.support_service import SupportService

router = APIRouter(
    prefix="/recruiter/support",
    tags=["Recruiter Help & Support"],
)


@router.post(
    "/requests",
    response_model=RecruiterSupportRequestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a new recruiter support request",
    description="Submits a support request from the authenticated recruiter and persists it to MySQL.",
)
async def submit_support_request(
    payload: RecruiterSupportRequestCreate,
    current_user: User = Depends(get_current_recruiter),
    db: AsyncSession = Depends(get_database),
) -> RecruiterSupportRequestResponse:
    """
    POST /api/v1/recruiter/support/requests
    Requires Bearer JWT token with RECRUITER role.
    Resolves recruiter & company information automatically from authenticated session.
    """
    return await SupportService.create_support_request(
        db=db, current_user=current_user, data=payload
    )


@router.get(
    "/requests",
    response_model=RecruiterSupportRequestListResponse,
    status_code=status.HTTP_200_OK,
    summary="List recruiter support requests",
    description="Returns all support requests submitted by the authenticated recruiter.",
)
async def list_support_requests(
    current_user: User = Depends(get_current_recruiter),
    db: AsyncSession = Depends(get_database),
) -> RecruiterSupportRequestListResponse:
    """
    GET /api/v1/recruiter/support/requests
    Requires Bearer JWT token with RECRUITER role.
    """
    return await SupportService.get_recruiter_support_requests(
        db=db, current_user=current_user
    )
