from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_candidate, get_database
from app.models.user import User
from app.schemas.candidate_settings import (
    CandidateSettingsResponse,
    NotificationSettingsUpdate,
    PrivacySettingsUpdate,
    ChangePasswordRequest,
    MessageResponse,
)
from app.services.candidate_settings_service import CandidateSettingsService

router = APIRouter(prefix="/candidate", tags=["Candidate Settings"])


@router.get(
    "/settings",
    response_model=CandidateSettingsResponse,
    summary="Get candidate settings",
    description="Retrieve notification and privacy preferences for the authenticated candidate.",
)
async def get_settings(
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_database),
) -> CandidateSettingsResponse:
    return await CandidateSettingsService.get_settings(db, current_user)


@router.patch(
    "/settings/notifications",
    response_model=CandidateSettingsResponse,
    summary="Update notification preferences",
    description="Persist updated notification channels and alert preferences.",
)
async def update_notifications(
    payload: NotificationSettingsUpdate,
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_database),
) -> CandidateSettingsResponse:
    return await CandidateSettingsService.update_notifications(db, current_user, payload)


@router.patch(
    "/settings/privacy",
    response_model=CandidateSettingsResponse,
    summary="Update profile visibility & privacy preferences",
    description="Persist updated recruiter talent search visibility and direct messaging preferences.",
)
async def update_privacy(
    payload: PrivacySettingsUpdate,
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_database),
) -> CandidateSettingsResponse:
    return await CandidateSettingsService.update_privacy(db, current_user, payload)


@router.patch(
    "/settings/password",
    response_model=MessageResponse,
    summary="Change candidate password",
    description="Securely verify current password and update to new password.",
)
@router.post(
    "/settings/password",
    response_model=MessageResponse,
    summary="Change candidate password (POST alias)",
    description="Securely verify current password and update to new password.",
)
async def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_database),
) -> MessageResponse:
    return await CandidateSettingsService.change_password(db, current_user, payload)


@router.delete(
    "/account",
    response_model=MessageResponse,
    summary="Delete candidate account",
    description="Securely deactivate candidate account and invalidate future logins while preserving application history.",
)
async def delete_account(
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_database),
) -> MessageResponse:
    return await CandidateSettingsService.delete_account(db, current_user)
