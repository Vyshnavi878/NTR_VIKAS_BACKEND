import os
import uuid
from pathlib import Path
from typing import Optional
from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.user import User
from app.models.admin_profile import AdminProfile
from app.repositories.admin_profile_repository import AdminProfileRepository
from app.schemas.admin_profile import (
    AdminProfileResponse,
    AdminProfileUpdate,
    AdminProfileImageResponse,
)

MAX_IMAGE_SIZE = 2 * 1024 * 1024  # 2MB

ALLOWED_IMAGE_TYPES = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/webp": ".webp",
}

ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


class AdminProfileService:
    """Business logic service for Admin Profile management."""

    @classmethod
    async def get_or_create_profile(
        cls,
        db: AsyncSession,
        current_admin: User,
    ) -> AdminProfile:
        """Fetch or auto-provision default AdminProfile for authenticated admin."""
        profile = await AdminProfileRepository.get_by_user_id(db, current_admin.id)
        if profile:
            return profile

        # Default seeds for known admins or fallback
        email = current_admin.email.lower().strip()
        if "admin1" in email:
            full_name = "Admin User"
            designation = "State Operations Lead"
            contact_phone = "+91 98765 43210"
        elif "admin2" in email:
            full_name = "Super Admin"
            designation = "Directorate of Employment"
            contact_phone = "+91 98765 43211"
        else:
            full_name = email.split("@")[0].replace(".", " ").title()
            designation = "Platform Administrator"
            contact_phone = current_admin.phone or "+91 98765 43210"

        department = "State Employment & Skill Development Authority"

        new_profile = AdminProfile(
            id=str(uuid.uuid4()),
            user_id=current_admin.id,
            full_name=full_name,
            designation=designation,
            contact_phone=contact_phone,
            department=department,
            profile_image_url=None,
        )
        return await AdminProfileRepository.create(db, new_profile)

    @classmethod
    def _build_response(
        cls,
        user: User,
        profile: AdminProfile,
    ) -> AdminProfileResponse:
        """Construct response DTO avoiding exposure of sensitive credentials."""
        role_label = "Platform Administrator"
        if user.role.upper() == "ADMIN":
            role_label = "Platform Administrator"
        else:
            role_label = user.role

        return AdminProfileResponse(
            id=profile.id,
            full_name=profile.full_name,
            email=user.email,
            role=role_label,
            designation=profile.designation,
            contact_phone=profile.contact_phone,
            department=profile.department,
            status="ACTIVE" if user.is_active else "INACTIVE",
            profile_image_url=profile.profile_image_url,
        )

    @classmethod
    async def get_profile(
        cls,
        db: AsyncSession,
        current_admin: User,
    ) -> AdminProfileResponse:
        """Retrieve profile information for currently authenticated administrator."""
        profile = await cls.get_or_create_profile(db, current_admin)
        return cls._build_response(current_admin, profile)

    @classmethod
    async def update_profile(
        cls,
        db: AsyncSession,
        current_admin: User,
        payload: AdminProfileUpdate,
    ) -> AdminProfileResponse:
        """
        Update editable profile fields for currently authenticated administrator.
        Enforces email uniqueness and validates authorized fields.
        """
        profile = await cls.get_or_create_profile(db, current_admin)
        changes = {}

        # 1. Handle email update
        if payload.email is not None:
            new_email = str(payload.email).lower().strip()
            if new_email != current_admin.email.lower().strip():
                # Check for uniqueness across users
                stmt = select(User).where(User.email == new_email, User.id != current_admin.id)
                res = await db.execute(stmt)
                if res.scalar_one_or_none():
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="The requested email address is already in use by another account.",
                    )
                current_admin.email = new_email
                db.add(current_admin)
                changes["email"] = new_email

        # 2. Handle full_name update
        if payload.full_name is not None:
            clean_name = payload.full_name.strip()
            profile.full_name = clean_name
            changes["full_name"] = clean_name

        # 3. Handle designation update
        if payload.designation is not None:
            profile.designation = payload.designation.strip()
            changes["designation"] = profile.designation

        # 4. Handle contact_phone update
        if payload.contact_phone is not None:
            clean_phone = payload.contact_phone.strip()
            profile.contact_phone = clean_phone
            changes["contact_phone"] = clean_phone

        # Persist profile changes
        profile = await AdminProfileRepository.update(db, profile)

        # Record audit log
        if changes:
            await AdminProfileRepository.log_audit(
                db=db,
                actor=current_admin.email,
                action="ADMIN_PROFILE_UPDATED",
                entity_id=profile.id,
                metadata_json=changes,
            )

        return cls._build_response(current_admin, profile)

    @classmethod
    async def upload_profile_image(
        cls,
        db: AsyncSession,
        current_admin: User,
        upload_file: UploadFile,
    ) -> AdminProfileImageResponse:
        """
        Validate, store, and associate an avatar photo for the authenticated administrator.
        Validates PNG, JPG, WEBP formats up to 2MB.
        """
        if not upload_file or not upload_file.filename:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Profile image file is required.",
            )

        content = await upload_file.read()
        file_size = len(content)

        if file_size == 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Uploaded image file is empty.",
            )

        if file_size > MAX_IMAGE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Profile image exceeds maximum limit of 2MB.",
            )

        content_type = (upload_file.content_type or "").lower().strip()
        filename_ext = Path(upload_file.filename).suffix.lower()

        # Validate MIME and extension
        if content_type not in ALLOWED_IMAGE_TYPES and filename_ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Unsupported image format. Allowed formats: PNG, JPG, JPEG, WEBP.",
            )

        ext = ALLOWED_IMAGE_TYPES.get(content_type) or filename_ext
        if ext not in ALLOWED_EXTENSIONS:
            ext = ".png"

        # Safe unique filename
        safe_filename = f"admin_avatar_{uuid.uuid4().hex}{ext}"
        target_dir = os.path.join(settings.UPLOAD_DIR, "admin", "profile")
        os.makedirs(target_dir, exist_ok=True)
        file_path = os.path.join(target_dir, safe_filename)

        with open(file_path, "wb") as f:
            f.write(content)

        relative_url = f"/uploads/admin/profile/{safe_filename}"

        profile = await cls.get_or_create_profile(db, current_admin)
        profile.profile_image_url = relative_url
        await AdminProfileRepository.update(db, profile)

        # Record audit log
        await AdminProfileRepository.log_audit(
            db=db,
            actor=current_admin.email,
            action="ADMIN_PROFILE_IMAGE_UPDATED",
            entity_id=profile.id,
            metadata_json={"image_url": relative_url, "size": file_size},
        )

        return AdminProfileImageResponse(
            profile_image_url=relative_url,
            message="Profile image updated successfully.",
        )
