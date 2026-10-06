"""
Recruiter Interview Management Endpoints
POST   /api/v1/recruiter/interviews
GET    /api/v1/recruiter/interviews
GET    /api/v1/recruiter/interviews/{interview_id}
PATCH  /api/v1/recruiter/interviews/{interview_id}
PATCH  /api/v1/recruiter/interviews/{interview_id}/reschedule
POST   /api/v1/recruiter/interviews/{interview_id}/cancel
POST   /api/v1/recruiter/interviews/{interview_id}/complete
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_database, get_current_recruiter
from app.models.user import User
from app.schemas.interview import (
    InterviewCreate,
    InterviewUpdate,
    InterviewCancel,
    InterviewComplete,
    InterviewResponse,
    InterviewListResponse,
)
from app.services.interview_service import InterviewService

router = APIRouter(
    prefix="/recruiter/interviews",
    tags=["Recruiter Interviews"],
)

recruiters_plural_router = APIRouter(
    prefix="/recruiters/interviews",
    tags=["Recruiter Interviews"],
)


# ── 1. Schedule New Interview ──────────────────────────────────────────────────
@router.post(
    "",
    response_model=InterviewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Schedule Interview",
    description="Schedules a new interview round for an application. Verifies application existence, validates candidate/job relationships, and checks scheduling conflicts.",
)
async def schedule_interview(
    data: InterviewCreate,
    current_user: User = Depends(get_current_recruiter),
    db: AsyncSession = Depends(get_database),
) -> InterviewResponse:
    return await InterviewService.schedule_interview(
        db=db,
        current_user=current_user,
        data=data,
    )


# ── 2. List Recruiter Interviews ───────────────────────────────────────────────
@router.get(
    "",
    response_model=InterviewListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Recruiter Interviews",
    description="Returns interview rounds belonging to the authenticated recruiter with status tabs, search, and date filters.",
)
async def list_interviews(
    status: Optional[str] = Query(None, description="Status filter: ALL, SCHEDULED, COMPLETED, RESCHEDULED, CANCELLED"),
    job_id: Optional[str] = Query(None, description="Filter by Job ID"),
    application_id: Optional[str] = Query(None, description="Filter by Application ID"),
    candidate_id: Optional[str] = Query(None, description="Filter by Candidate ID"),
    date_from: Optional[str] = Query(None, description="Filter by start date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Filter by end date (YYYY-MM-DD)"),
    search: Optional[str] = Query(None, description="Search candidate name, job title, interviewer, or notes"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_recruiter),
    db: AsyncSession = Depends(get_database),
) -> InterviewListResponse:
    return await InterviewService.get_recruiter_interviews(
        db=db,
        current_user=current_user,
        status_filter=status,
        job_id=job_id,
        application_id=application_id,
        candidate_id=candidate_id,
        date_from=date_from,
        date_to=date_to,
        search=search,
        page=page,
        page_size=page_size,
    )


# ── 3. Get Interview Details ───────────────────────────────────────────────────
@router.get(
    "/{interview_id}",
    response_model=InterviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Interview Details",
    description="Returns full interview details for the given ID. Enforces strict multi-tenant recruiter isolation.",
)
async def get_interview_detail(
    interview_id: str,
    current_user: User = Depends(get_current_recruiter),
    db: AsyncSession = Depends(get_database),
) -> InterviewResponse:
    return await InterviewService.get_interview_detail(
        db=db,
        current_user=current_user,
        interview_id=interview_id,
    )


# ── 4. Reschedule Interview ───────────────────────────────────────────────────
@router.patch(
    "/{interview_id}",
    response_model=InterviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Reschedule Interview",
    description="Updates the schedule date and time slot for an existing interview with conflict validation.",
)
async def reschedule_interview(
    interview_id: str,
    data: InterviewUpdate,
    current_user: User = Depends(get_current_recruiter),
    db: AsyncSession = Depends(get_database),
) -> InterviewResponse:
    return await InterviewService.reschedule_interview(
        db=db,
        current_user=current_user,
        interview_id=interview_id,
        data=data,
    )


@router.patch(
    "/{interview_id}/reschedule",
    response_model=InterviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Reschedule Interview (Explicit Action Endpoint)",
    description="Dedicated action endpoint for rescheduling an interview round.",
)
async def reschedule_interview_explicit(
    interview_id: str,
    data: InterviewUpdate,
    current_user: User = Depends(get_current_recruiter),
    db: AsyncSession = Depends(get_database),
) -> InterviewResponse:
    return await InterviewService.reschedule_interview(
        db=db,
        current_user=current_user,
        interview_id=interview_id,
        data=data,
    )


# ── 5. Cancel Interview ────────────────────────────────────────────────────────
@router.post(
    "/{interview_id}/cancel",
    response_model=InterviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Cancel Interview",
    description="Cancels an interview round, preserving history and recording cancellation reason and timestamp.",
)
async def cancel_interview(
    interview_id: str,
    data: InterviewCancel,
    current_user: User = Depends(get_current_recruiter),
    db: AsyncSession = Depends(get_database),
) -> InterviewResponse:
    return await InterviewService.cancel_interview(
        db=db,
        current_user=current_user,
        interview_id=interview_id,
        data=data,
    )


# ── 6. Complete Interview ──────────────────────────────────────────────────────
@router.post(
    "/{interview_id}/complete",
    response_model=InterviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Complete Interview",
    description="Marks an interview as COMPLETED after it has been conducted, saving evaluation feedback notes.",
)
async def complete_interview(
    interview_id: str,
    data: InterviewComplete,
    current_user: User = Depends(get_current_recruiter),
    db: AsyncSession = Depends(get_database),
) -> InterviewResponse:
    return await InterviewService.complete_interview(
        db=db,
        current_user=current_user,
        interview_id=interview_id,
        data=data,
    )


# Plural router mirroring
recruiters_plural_router.add_api_route(
    "", schedule_interview, methods=["POST"], response_model=InterviewResponse, status_code=status.HTTP_201_CREATED
)
recruiters_plural_router.add_api_route(
    "", list_interviews, methods=["GET"], response_model=InterviewListResponse, status_code=status.HTTP_200_OK
)
recruiters_plural_router.add_api_route(
    "/{interview_id}", get_interview_detail, methods=["GET"], response_model=InterviewResponse, status_code=status.HTTP_200_OK
)
recruiters_plural_router.add_api_route(
    "/{interview_id}", reschedule_interview, methods=["PATCH"], response_model=InterviewResponse, status_code=status.HTTP_200_OK
)
recruiters_plural_router.add_api_route(
    "/{interview_id}/reschedule", reschedule_interview_explicit, methods=["PATCH"], response_model=InterviewResponse, status_code=status.HTTP_200_OK
)
recruiters_plural_router.add_api_route(
    "/{interview_id}/cancel", cancel_interview, methods=["POST"], response_model=InterviewResponse, status_code=status.HTTP_200_OK
)
recruiters_plural_router.add_api_route(
    "/{interview_id}/complete", complete_interview, methods=["POST"], response_model=InterviewResponse, status_code=status.HTTP_200_OK
)
