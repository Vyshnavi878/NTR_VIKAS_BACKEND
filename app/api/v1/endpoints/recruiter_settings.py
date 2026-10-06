from typing import List, Dict, Any
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_database, get_current_recruiter, get_current_active_user
from app.models.user import User
from app.schemas.recruiter_settings import (
    RecruiterProfileSettingsResponse,
    RecruiterProfileSettingsUpdate,
    TeamMemberResponse,
    TeamInvitationCreate,
    TeamInvitationResponse,
    RecruiterNotificationPreferencesResponse,
    RecruiterNotificationPreferencesUpdate,
    RecruiterChangePasswordRequest,
)
from app.services.recruiter_settings_service import RecruiterSettingsService

router = APIRouter(
    prefix="/recruiter/settings",
    tags=["Recruiter Settings & Preferences"],
)


# ── 1. Personal Recruiter Profile ─────────────────────────────────────────────
@router.get(
    "/profile",
    response_model=RecruiterProfileSettingsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get authenticated recruiter personal profile",
    description="Retrieve personal credentials, contact info, and company association for the authenticated recruiter.",
)
async def get_profile(
    current_recruiter: User = Depends(get_current_recruiter),
    db: AsyncSession = Depends(get_database),
) -> RecruiterProfileSettingsResponse:
    return await RecruiterSettingsService.get_profile(db=db, current_recruiter=current_recruiter)


@router.patch(
    "/profile",
    response_model=RecruiterProfileSettingsResponse,
    status_code=status.HTTP_200_OK,
    summary="Update authenticated recruiter personal profile",
    description="Update personal full name, designation, and official mobile phone. Email is read-only.",
)
@router.put(
    "/profile",
    response_model=RecruiterProfileSettingsResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def update_profile(
    payload: RecruiterProfileSettingsUpdate,
    current_recruiter: User = Depends(get_current_recruiter),
    db: AsyncSession = Depends(get_database),
) -> RecruiterProfileSettingsResponse:
    return await RecruiterSettingsService.update_profile(
        db=db, current_recruiter=current_recruiter, payload=payload
    )


# ── 2. Hiring Team & Collaborators ───────────────────────────────────────────
@router.get(
    "/team",
    response_model=List[TeamMemberResponse],
    status_code=status.HTTP_200_OK,
    summary="Get company hiring team members and pending invitations",
    description="Retrieve all team members and pending invitations belonging to the recruiter's company workspace.",
)
async def get_team(
    current_recruiter: User = Depends(get_current_recruiter),
    db: AsyncSession = Depends(get_database),
) -> List[TeamMemberResponse]:
    return await RecruiterSettingsService.get_team(db=db, current_recruiter=current_recruiter)


@router.post(
    "/team/invitations",
    response_model=TeamInvitationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Invite a new hiring team member",
    description="Send an invitation to a team member to join the company hiring workspace. Only Company Owner can invite.",
)
async def invite_team_member(
    payload: TeamInvitationCreate,
    current_recruiter: User = Depends(get_current_recruiter),
    db: AsyncSession = Depends(get_database),
) -> TeamInvitationResponse:
    return await RecruiterSettingsService.invite_team_member(
        db=db, current_recruiter=current_recruiter, payload=payload
    )


@router.post(
    "/team/invitations/{invitation_id}/resend",
    response_model=TeamInvitationResponse,
    status_code=status.HTTP_200_OK,
    summary="Resend an invitation email with a new secure token",
    description="Invalidates the old token and dispatches a new invitation email.",
)
async def resend_invitation(
    invitation_id: str,
    current_recruiter: User = Depends(get_current_recruiter),
    db: AsyncSession = Depends(get_database),
) -> TeamInvitationResponse:
    return await RecruiterSettingsService.resend_invitation(
        db=db, current_recruiter=current_recruiter, invitation_id=invitation_id
    )


@router.delete(
    "/team/members/{member_id}",
    status_code=status.HTTP_200_OK,
    summary="Remove or deactivate a hiring team member / cancel invitation",
    description="Deactivates a team member while preserving all historical data and candidate records.",
)
async def remove_team_member(
    member_id: str,
    current_recruiter: User = Depends(get_current_recruiter),
    db: AsyncSession = Depends(get_database),
) -> Dict[str, Any]:
    return await RecruiterSettingsService.remove_or_deactivate_member(
        db=db, current_recruiter=current_recruiter, member_id=member_id
    )


# ── 3. Notification Preferences ───────────────────────────────────────────────
@router.get(
    "/notifications",
    response_model=RecruiterNotificationPreferencesResponse,
    status_code=status.HTTP_200_OK,
    summary="Get recruiter notification preferences",
    description="Retrieve personal email/in-app notification toggle rules for the authenticated recruiter.",
)
async def get_notifications(
    current_recruiter: User = Depends(get_current_recruiter),
    db: AsyncSession = Depends(get_database),
) -> RecruiterNotificationPreferencesResponse:
    return await RecruiterSettingsService.get_notification_preferences(
        db=db, current_recruiter=current_recruiter
    )


@router.patch(
    "/notifications",
    response_model=RecruiterNotificationPreferencesResponse,
    status_code=status.HTTP_200_OK,
    summary="Update recruiter notification preferences",
    description="Update notification preference rules for the authenticated recruiter.",
)
@router.put(
    "/notifications",
    response_model=RecruiterNotificationPreferencesResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def update_notifications(
    payload: RecruiterNotificationPreferencesUpdate,
    current_recruiter: User = Depends(get_current_recruiter),
    db: AsyncSession = Depends(get_database),
) -> RecruiterNotificationPreferencesResponse:
    return await RecruiterSettingsService.update_notification_preferences(
        db=db, current_recruiter=current_recruiter, payload=payload
    )


# ── 4. Password Change Alias ──────────────────────────────────────────────────
@router.post(
    "/password",
    status_code=status.HTTP_200_OK,
    summary="Change password (recruiter settings route)",
)
@router.patch(
    "/password",
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def change_password_settings(
    payload: RecruiterChangePasswordRequest,
    current_user: User = Depends(get_current_recruiter),
    db: AsyncSession = Depends(get_database),
) -> Dict[str, str]:
    return await RecruiterSettingsService.change_password(
        db=db, current_user=current_user, payload=payload
    )
