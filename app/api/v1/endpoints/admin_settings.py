"""
Admin Platform Settings Endpoints
GET   /api/v1/admin/settings
PATCH /api/v1/admin/settings
PUT   /api/v1/admin/settings
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_database, get_current_admin
from app.models.user import User
from app.schemas.platform_settings import (
    PlatformSettingsResponse,
    PlatformSettingsUpdate,
)
from app.services.platform_settings_service import PlatformSettingsService

router = APIRouter(
    prefix="/admin/settings",
    tags=["Admin Platform & Global Settings Management"],
)


@router.get(
    "",
    response_model=PlatformSettingsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get global platform settings",
    description="Retrieve system parameters, moderation policies, and maintenance mode status. Requires Administrator privileges.",
)
async def get_platform_settings(
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_database),
) -> PlatformSettingsResponse:
    """Returns the current global platform configuration."""
    return await PlatformSettingsService.get_settings(db=db, current_admin=current_admin)


@router.patch(
    "",
    response_model=PlatformSettingsResponse,
    status_code=status.HTTP_200_OK,
    summary="Update global platform settings",
    description="Update general platform parameters, verification policies, moderation queue, or maintenance mode. Requires Administrator privileges.",
)
@router.put(
    "",
    response_model=PlatformSettingsResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def update_platform_settings(
    payload: PlatformSettingsUpdate,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_database),
) -> PlatformSettingsResponse:
    """Updates and persists global platform configuration and records audit logs."""
    return await PlatformSettingsService.update_settings(
        db=db, current_admin=current_admin, payload=payload
    )
