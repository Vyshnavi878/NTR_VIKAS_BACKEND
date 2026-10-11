"""
seed_admin.py - Idempotent, secure initial Admin account seeding.

Seeds the initial administrator user from environment configuration (.env)
using SQLAlchemy 2.0 AsyncIO, bcrypt hashing, and existing models.
Safe to run multiple times without overwriting existing credentials or data.

Usage:
    python -m app.scripts.seed_admin
    python -m scripts.seed_admin
"""

import asyncio
import logging
import os
import re
import sys
import uuid
from datetime import datetime, timezone
from typing import Optional, Tuple, Dict, Any

# Ensure project root is in sys.path when executed directly
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import hash_password
from app.database.session import AsyncSessionLocal
from app.models.user import User
from app.models.admin_profile import AdminProfile

# Configure secure console logger (never log passwords or hashes)
logger = logging.getLogger("seed_admin")
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Approved admin roles recognised across the platform
ADMIN_ROLES = {"ADMIN", "SUPER_ADMIN", "PLATFORM_ADMINISTRATOR"}


def validate_credentials() -> Tuple[bool, str, Optional[Dict[str, str]]]:
    """
    Validate that required initial admin environment variables are present and well-formed.
    Returns: (is_valid, message, credentials_dict)
    """
    email = (settings.INITIAL_ADMIN_EMAIL or os.getenv("INITIAL_ADMIN_EMAIL") or "").strip()
    password = (settings.INITIAL_ADMIN_PASSWORD or os.getenv("INITIAL_ADMIN_PASSWORD") or "").strip()
    name = (settings.INITIAL_ADMIN_NAME or os.getenv("INITIAL_ADMIN_NAME") or "Admin State Lead").strip()
    role = (settings.INITIAL_ADMIN_ROLE or os.getenv("INITIAL_ADMIN_ROLE") or "SUPER_ADMIN").strip().upper()

    if not email:
        return (
            False,
            "Required environment variable 'INITIAL_ADMIN_EMAIL' is missing or empty. Initial admin seeding aborted.",
            None,
        )

    if not password:
        return (
            False,
            "Required environment variable 'INITIAL_ADMIN_PASSWORD' is missing or empty. Initial admin seeding aborted.",
            None,
        )

    # Normalize email
    clean_email = email.lower()

    # Basic email format validation
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", clean_email):
        return (
            False,
            f"INITIAL_ADMIN_EMAIL '{clean_email}' is not a valid email address.",
            None,
        )

    if len(password) < 6:
        return (
            False,
            "INITIAL_ADMIN_PASSWORD must be at least 6 characters long for security compliance.",
            None,
        )

    return (
        True,
        "Validation successful.",
        {
            "email": clean_email,
            "password": password,
            "name": name,
            "role": role,
        },
    )


async def seed_initial_admin(session: AsyncSession, creds: Dict[str, str]) -> Tuple[int, str]:
    """
    Idempotently seed the initial admin account.
    - If user exists with an admin role: do not overwrite password, role, status, or profile.
    - If user exists with a non-admin role: report conflict and abort.
    - If user does not exist: create user and admin profile, hash password, and commit.
    Returns (exit_code, summary_message)
    """
    clean_email = creds["email"]
    name = creds["name"]
    role = creds["role"]
    raw_password = creds["password"]

    # Check for existing account by normalized email
    stmt = select(User).where(func.lower(User.email) == clean_email)
    res = await session.execute(stmt)
    existing_user = res.scalar_one_or_none()

    if existing_user:
        # Check if user has an admin role
        if existing_user.role.upper() in ADMIN_ROLES:
            msg = (
                f"Admin account already exists for email '{clean_email}' "
                f"(User ID: {existing_user.id}, Role: {existing_user.role}). "
                f"Existing credentials, role, status, and profile preserved. Skipping creation."
            )
            return (0, msg)
        else:
            msg = (
                f"Conflict detected: An account with email '{clean_email}' already exists "
                f"under role '{existing_user.role}'. "
                f"Initial admin seeding cannot overwrite or silently promote non-admin accounts. "
                f"Operation aborted."
            )
            return (1, msg)

    # Create new Admin User with securely hashed password
    now = datetime.now(timezone.utc)
    hashed_pwd = hash_password(raw_password)
    user_id = str(uuid.uuid4())

    new_admin_user = User(
        id=user_id,
        email=clean_email,
        phone=None,
        hashed_password=hashed_pwd,
        role=role,
        is_active=True,
        is_verified=True,
        created_at=now,
        updated_at=now,
    )
    session.add(new_admin_user)
    await session.flush()

    # Create associated AdminProfile
    designation = "State Operations Lead" if role == "SUPER_ADMIN" else "Platform Administrator"
    new_admin_profile = AdminProfile(
        id=str(uuid.uuid4()),
        user_id=user_id,
        full_name=name,
        designation=designation,
        contact_phone="+91 98765 43210",
        department="State Employment & Skill Development Authority",
        profile_image_url=None,
        created_at=now,
        updated_at=now,
    )
    session.add(new_admin_profile)
    await session.commit()

    msg = (
        f"Initial admin account successfully created: "
        f"email='{clean_email}', name='{name}', role='{role}', user_id='{user_id}'. "
        f"Password stored as secure bcrypt hash."
    )
    return (0, msg)


async def run_seed() -> int:
    """
    Main asynchronous executor for the admin seeding operation.
    Returns process exit code (0 = success/idempotent, 1 = failure/conflict).
    """
    logger.info("Starting initial admin account seeding check...")

    is_valid, validation_msg, creds = validate_credentials()
    if not is_valid or not creds:
        logger.error(f"Seeding aborted: {validation_msg}")
        return 1

    logger.info(f"Checking status for initial admin: '{creds['email']}' (Role: '{creds['role']}')...")

    async with AsyncSessionLocal() as session:
        try:
            exit_code, summary = await seed_initial_admin(session, creds)
            if exit_code == 0:
                logger.info(summary)
            else:
                logger.error(summary)
            return exit_code
        except Exception as e:
            await session.rollback()
            logger.error(f"Seeding failed due to unexpected database error: {type(e).__name__}: {str(e)}")
            return 1


def main() -> int:
    """Synchronous entry point."""
    try:
        return asyncio.run(run_seed())
    except KeyboardInterrupt:
        logger.warning("Seeding interrupted by user.")
        return 130
    except Exception as e:
        logger.error(f"Fatal error during seeding: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
