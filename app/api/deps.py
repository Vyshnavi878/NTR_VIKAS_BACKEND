from typing import AsyncGenerator, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import decode_token
from app.database.session import get_db
from app.models.user import User
from app.repositories.user_repository import UserRepository

# HTTPBearer provides a direct "Bearer Token" input in Swagger UI (Authorize dialog)
# without asking for username/password or requiring OAuth2 form flows.
bearer_scheme = HTTPBearer(
    bearerFormat="JWT",
    scheme_name="Bearer",
    description="Enter your JWT Access Token directly (obtained from POST /api/v1/auth/login).",
    auto_error=False,
)
oauth2_scheme = bearer_scheme  # backward compatibility alias


async def get_database() -> AsyncGenerator[AsyncSession, None]:
    """Dependency provider yielding an async database session."""
    async for db in get_db():
        yield db


async def get_current_user(
    auth: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_database),
) -> User:
    """Validate JWT access token and return authenticated user model."""
    token: Optional[str] = None
    if auth and auth.credentials:
        token = auth.credentials.strip()
        # Handle if user accidentally pasted 'Bearer <token>' in the Swagger input box
        if token.lower().startswith("bearer "):
            token = token[7:].strip()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = await UserRepository.get_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Ensure the authenticated user account is active."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive or disabled.",
        )
    return current_user


async def get_current_candidate(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """Ensure the authenticated user is an active CANDIDATE."""
    if current_user.role.upper() != "CANDIDATE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Candidate account required.",
        )
    return current_user


async def get_current_recruiter(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """Ensure the authenticated user is an active RECRUITER."""
    if current_user.role.upper() != "RECRUITER":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Recruiter account required.",
        )
    return current_user


async def get_current_admin(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """Ensure the authenticated user is an active ADMIN."""
    if current_user.role.upper() != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Administrator privileges required.",
        )
    return current_user


async def get_optional_user(
    auth: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_database),
) -> Optional[User]:
    """Return authenticated User if valid Bearer token provided, else None."""
    if not auth or not auth.credentials:
        return None
    token = auth.credentials.strip()
    if token.lower().startswith("bearer "):
        token = token[7:].strip()
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        return None
    user_id = payload.get("sub")
    if not user_id:
        return None
    return await UserRepository.get_by_id(db, user_id)

