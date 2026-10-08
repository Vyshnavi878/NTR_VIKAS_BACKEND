"""
Admin Profile Endpoints
GET   /api/v1/admin/profile
PATCH /api/v1/admin/profile
POST  /api/v1/admin/profile/image
"""
from fastapi import APIRouter, Depends, UploadFile, File, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_database, get_current_admin
from app.models.user import User
from app.schemas.admin_profile import (
    AdminProfileResponse,
    AdminProfileUpdate,
    AdminProfileImageResponse,
)
from app.services.admin_profile_service import AdminProfileService

router = APIRouter(
    prefix="/admin/profile",
    tags=["Admin Profile & Identity Management"],
)


@router.get(
    "",
    response_model=AdminProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Get authenticated admin profile",
    description="Retrieve personal administrator profile and credentials for the authenticated admin.",
)
async def get_admin_profile(
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_database),
) -> AdminProfileResponse:
    """Returns the authenticated administrator's profile information."""
    return await AdminProfileService.get_profile(db=db, current_admin=current_admin)


@router.patch(
    "",
    response_model=AdminProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Update authenticated admin profile",
    description="Update editable profile fields (full name, email, designation, contact phone).",
)
@router.put(
    "",
    response_model=AdminProfileResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def update_admin_profile(
    payload: AdminProfileUpdate,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_database),
) -> AdminProfileResponse:
    """Updates editable profile details for the authenticated administrator."""
    return await AdminProfileService.update_profile(
        db=db, current_admin=current_admin, payload=payload
    )


@router.post(
    "/image",
    response_model=AdminProfileImageResponse,
    status_code=status.HTTP_200_OK,
    summary="Upload admin profile photo",
    description="Upload an avatar image (PNG, JPG, JPEG, WEBP max 2MB) for the authenticated admin.",
)
async def upload_admin_profile_image(
    file: UploadFile = File(..., description="Avatar image file (PNG, JPG, WEBP max 2MB)"),
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_database),
) -> AdminProfileImageResponse:
    """Uploads and saves a custom profile image for the authenticated administrator."""
    return await AdminProfileService.upload_profile_image(
        db=db, current_admin=current_admin, upload_file=file
    )
