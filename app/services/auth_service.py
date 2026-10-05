from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password, create_access_token, create_refresh_token
from app.repositories.user_repository import UserRepository
from app.schemas.auth import LoginRequest, LoginResponse, UserSummaryWithRole


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
