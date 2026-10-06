"""
Candidate Interviews API Endpoints
GET  /api/v1/candidate/interviews
GET  /api/v1/candidate/interviews/{interview_id}
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_database, get_current_candidate
from app.models.user import User
from app.schemas.interview import (
    InterviewResponse,
    CandidateInterviewListResponse,
)
from app.services.interview_service import InterviewService

router = APIRouter(
    prefix="/candidate/interviews",
    tags=["Candidate Interviews"],
)


@router.get(
    "",
    response_model=CandidateInterviewListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Candidate Interviews",
    description="Returns interview rounds scheduled for the authenticated candidate with dynamic tab counts (All, Upcoming, Today, Completed), search, and pagination.",
)
async def get_candidate_interviews(
    status: Optional[str] = Query(None, description="Status tab filter: ALL, UPCOMING, TODAY, COMPLETED"),
    search: Optional[str] = Query(None, description="Search keyword across company, role, interviewer panel, or notes"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(9, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_database),
) -> CandidateInterviewListResponse:
    return await InterviewService.get_candidate_interviews(
        db=db,
        current_user=current_user,
        status_filter=status,
        search=search,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{interview_id}",
    response_model=InterviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Candidate Interview Detail",
    description="Returns single scheduled interview detail for the authenticated candidate, enforcing strict candidate authorization.",
)
async def get_candidate_interview_detail(
    interview_id: str,
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_database),
) -> InterviewResponse:
    return await InterviewService.get_candidate_interview_detail(
        db=db,
        current_user=current_user,
        interview_id=interview_id,
    )
