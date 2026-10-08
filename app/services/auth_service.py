import re
import json
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.security import verify_password, hash_password, create_access_token, create_refresh_token
from app.models.user import User
from app.models.internship import AuditLog
from app.repositories.user_repository import UserRepository
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    UserSummaryWithRole,
    ChangePasswordRequest,
    ChangePasswordResponse,
)


class AuthService:
    """
    Authentication service handling multi-role login, JWT issuance, and account validation.
    """

    @classmethod
    async def authenticate_user(
        cls,
        payload: LoginRequest,
        db: AsyncSession,
    ) -> LoginResponse:
        """
        Authenticate user with email and password:
        1. Normalizes email.
        2. Retrieves user account and associated profile from MySQL.
        3. Verifies password using bcrypt hash.
        4. Validates account status (active check).
        5. Returns signed JWT access & refresh tokens with safe user summary.
        """
        clean_email = payload.email.lower().strip()
        user = await UserRepository.get_by_email_with_profile(db, clean_email)

        # Constant error message to prevent account enumeration
        if not user or not verify_password(payload.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check recruiter approval status
        if user.role.upper() == "RECRUITER" and user.recruiter_profile:
            if user.recruiter_profile.status == "PENDING_APPROVAL":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Your recruiter application is currently under admin review and pending approval.",
                )
            elif user.recruiter_profile.status == "REJECTED":
                reason = f": {user.recruiter_profile.rejection_reason}" if user.recruiter_profile.rejection_reason else "."
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Your recruiter registration was rejected{reason}",
                )

        # Check account activation status
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is inactive or disabled. Please contact support.",
            )

        # Derive user display name for frontend greeting
        display_name = None
        if user.candidate_profile and user.candidate_profile.name:
            display_name = user.candidate_profile.name
        elif user.recruiter_profile and user.recruiter_profile.recruiter_name:
            display_name = user.recruiter_profile.recruiter_name
        elif user.admin_profile and user.admin_profile.full_name:
            display_name = user.admin_profile.full_name
        elif "admin1" in clean_email:
            display_name = "Admin User"
        elif "admin2" in clean_email:
            display_name = "Super Admin"

        elif "recruiter1" in clean_email:
            display_name = "Arjun"
        elif "recruiter2" in clean_email:
            display_name = "Sneha"
        elif "candidate1" in clean_email:
            display_name = "Priya"
        elif "candidate2" in clean_email:
            display_name = "Rahul"
        else:
            display_name = clean_email.split("@")[0].replace(".", " ").title()

        # Generate JWT tokens
        access_token = create_access_token(subject=user.id, role=user.role, email=clean_email)
        refresh_token = create_refresh_token(subject=user.id, role=user.role)

        # Log audit entry for Admin Login
        if user.role.upper() == "ADMIN":
            audit_entry = AuditLog(
                id=f"audit-{uuid.uuid4().hex[:10]}",
                actor=display_name or user.email,
                action="Admin System Login",
                entity="AUTH",
                entity_id="AUTH_LOGIN",
                target_name="Admin Control Panel",
                result="SUCCESS",
                timestamp=datetime.now(timezone.utc),
            )
            db.add(audit_entry)
            await db.commit()

        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            user=UserSummaryWithRole(
                id=user.id,
                email=user.email,
                name=display_name,
                role=user.role.upper(),
                is_active=user.is_active,
                is_verified=user.is_verified,
            ),
        )

    @classmethod
    async def change_password(
        cls,
        db: AsyncSession,
        current_user: User,
        payload: ChangePasswordRequest,
    ) -> ChangePasswordResponse:
        """
        Universal authenticated password change:
        1. Extract current_password, new_password, confirm_password (supports camelCase).
        2. Validate current_password is provided.
        3. Verify current_password against stored hash using verify_password() (401 on mismatch).
        4. Validate new_password is provided.
        5. Validate new_password rules:
           - Minimum 8 characters (422 on failure)
           - At least one numeric digit [0-9] (422 on failure)
           - At least one letter [a-zA-Z] (422 on failure)
        6. Validate confirm_password matches new_password (422 on mismatch).
        7. Validate new_password is not identical to current password (400 on reuse).
        8. Hash new_password with hash_password() and update user record.
        9. Write audit log entry for admin password change.
        10. Commit transaction and return safe success message.
        """
        curr_pwd = (payload.current_password or payload.currentPassword or "").strip()
        new_pwd = (payload.new_password or payload.newPassword or "").strip()
        conf_pwd = (payload.confirm_password or payload.confirmPassword or "").strip()

        if not curr_pwd:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is required.",
            )

        if not new_pwd:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password is required.",
            )

        # Retrieve freshest user record in current db session
        user = await db.get(User, current_user.id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User account not found.",
            )

        # 1. Verify current password
        if not verify_password(curr_pwd, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Current password is incorrect.",
            )

        # 2. Validate new password length
        if len(new_pwd) < 8:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Password must be at least 8 characters.",
            )

        # 3. Validate new password contains at least one numeric digit (0-9)
        if not re.search(r"[0-9]", new_pwd):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Password must contain at least one number.",
            )

        # 4. Validate new password contains at least one letter
        if not re.search(r"[a-zA-Z]", new_pwd):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Password must contain at least one letter.",
            )

        # 5. Validate confirmation match if provided
        if conf_pwd and new_pwd != conf_pwd:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="New password and confirmation password do not match.",
            )

        # 6. Reject same password
        if verify_password(new_pwd, user.hashed_password) or curr_pwd == new_pwd:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password must be different from the current password.",
            )

        # 7. Hash and update
        user.hashed_password = hash_password(new_pwd)
        user.updated_at = datetime.now(timezone.utc)

        # 8. Record audit log for admin / security events
        if user.role.upper() == "ADMIN":
            audit_entry = AuditLog(
                id=f"audit-{uuid.uuid4().hex[:10]}",
                actor=user.email,
                action="Password Change",
                entity="USER",
                entity_id=user.id,
                target_name="Admin Password Credentials",
                result="SUCCESS",
                metadata_json=json.dumps({
                    "action": "Password Change",
                    "role": user.role,
                    "email": user.email,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }),
                timestamp=datetime.now(timezone.utc),
            )
            db.add(audit_entry)

        await db.commit()
        await db.refresh(user)

        return ChangePasswordResponse(
            status="success",
            message="Password changed successfully.",
        )
