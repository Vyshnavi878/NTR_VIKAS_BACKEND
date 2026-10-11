"""
Test suite for initial Admin account seeding and authentication.
Verifies all 8 acceptance criteria:
1. Initial admin created when seed command run for first time.
2. Running command again does not create duplicate or reset credentials.
3. Password stored only as secure hash.
4. Admin can log in through existing login endpoint.
5. Account receives correct admin role and permissions.
6. Missing environment variables cause a clear, safe error.
7. Conflict with non-admin role reported without silently promoting.
8. Existing accounts remain unchanged.
"""

import os
import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select, func

from app.main import app
from app.core.config import settings
from app.core.security import verify_password, decode_token, hash_password
from app.database.session import AsyncSessionLocal
from app.models.user import User
from app.models.admin_profile import AdminProfile
from app.scripts.seed_admin import validate_credentials, seed_initial_admin, ADMIN_ROLES


@pytest.mark.asyncio
async def test_initial_admin_seeded_in_database():
    """Criterion 1 & 3: Initial admin exists with correct role, active status, and bcrypt hash."""
    clean_email = (settings.INITIAL_ADMIN_EMAIL or "admin@gmail.com").strip().lower()

    async with AsyncSessionLocal() as session:
        stmt = (
            select(User)
            .where(func.lower(User.email) == clean_email)
        )
        res = await session.execute(stmt)
        admin_user = res.scalar_one_or_none()

        assert admin_user is not None, f"Admin user with email '{clean_email}' not found."
        assert admin_user.role == "SUPER_ADMIN"
        assert admin_user.is_active is True
        assert admin_user.is_verified is True

        # Verify password is secure bcrypt hash (starts with $2b$ or $2a$, min 59 chars)
        assert admin_user.hashed_password.startswith(("$2b$", "$2a$"))
        assert len(admin_user.hashed_password) >= 59
        assert "Admin@123" not in admin_user.hashed_password
        assert verify_password("Admin@123", admin_user.hashed_password) is True
        assert verify_password("WrongPassword!", admin_user.hashed_password) is False

        # Verify AdminProfile exists and is linked
        prof_stmt = select(AdminProfile).where(AdminProfile.user_id == admin_user.id)
        prof_res = await session.execute(prof_stmt)
        admin_profile = prof_res.scalar_one_or_none()

        assert admin_profile is not None
        assert admin_profile.full_name == "Admin State Lead"
        assert admin_profile.designation == "State Operations Lead"


@pytest.mark.asyncio
async def test_seeding_is_idempotent():
    """Criterion 2: Running seed operation again does not duplicate or reset credentials."""
    creds = {
        "email": (settings.INITIAL_ADMIN_EMAIL or "admin@gmail.com").strip().lower(),
        "password": "Admin@123",
        "name": "Admin State Lead",
        "role": "SUPER_ADMIN",
    }

    async with AsyncSessionLocal() as session:
        # Capture current password hash before rerun
        stmt = select(User).where(func.lower(User.email) == creds["email"])
        orig_user = (await session.execute(stmt)).scalar_one()
        orig_hash = orig_user.hashed_password
        orig_updated_at = orig_user.updated_at

        # Execute seeding logic again
        exit_code, msg = await seed_initial_admin(session, creds)
        assert exit_code == 0
        assert "already exists" in msg
        assert "Skipping creation" in msg

        # Verify no duplicate was created
        count_stmt = select(func.count(User.id)).where(func.lower(User.email) == creds["email"])
        count = (await session.execute(count_stmt)).scalar()
        assert count == 1

        # Verify credentials and timestamp unchanged
        refreshed_user = (await session.execute(stmt)).scalar_one()
        assert refreshed_user.hashed_password == orig_hash
        assert refreshed_user.role == "SUPER_ADMIN"
        assert refreshed_user.updated_at == orig_updated_at


@pytest.mark.asyncio
async def test_admin_login_endpoint_and_token_issuance():
    """Criterion 4 & 5: Admin signs in through existing login flow and gets correct role."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/auth/login",
            json={
                "email": settings.INITIAL_ADMIN_EMAIL or "admin@gmail.com",
                "password": settings.INITIAL_ADMIN_PASSWORD or "Admin@123",
            },
        )
        assert resp.status_code == 200, f"Login failed: {resp.text}"
        data = resp.json()

        # Token fields
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

        # User payload
        user_info = data["user"]
        assert user_info["email"] == "admin@gmail.com"
        assert user_info["role"] == "SUPER_ADMIN"
        assert user_info["name"] == "Admin State Lead"
        assert user_info["is_active"] is True
        assert user_info["is_verified"] is True

        # Security: No sensitive info exposed in response
        assert "password" not in data
        assert "hashed_password" not in data

        # Token claims verification
        claims = decode_token(data["access_token"])
        assert claims is not None
        assert claims["role"] == "SUPER_ADMIN"
        assert claims["sub"] == user_info["id"]
        assert claims["type"] == "access"


@pytest.mark.asyncio
async def test_admin_permissions_on_protected_routes():
    """Criterion 5: Account receives administrative access to protected admin routes."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # First authenticate
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={
                "email": settings.INITIAL_ADMIN_EMAIL or "admin@gmail.com",
                "password": settings.INITIAL_ADMIN_PASSWORD or "Admin@123",
            },
        )
        assert login_resp.status_code == 200
        token = login_resp.json()["access_token"]
        auth_headers = {"Authorization": f"Bearer {token}"}

        # 1. Admin Dashboard Stats
        dash_resp = await client.get("/api/v1/admin/dashboard", headers=auth_headers)
        assert dash_resp.status_code == 200, f"Dashboard failed: {dash_resp.text}"

        # 2. Admin Profile
        prof_resp = await client.get("/api/v1/admin/profile", headers=auth_headers)
        assert prof_resp.status_code == 200, f"Profile failed: {prof_resp.text}"
        prof_data = prof_resp.json()
        assert prof_data["email"] == "admin@gmail.com"
        assert prof_data["full_name"] == "Admin State Lead"

        # 3. Admin Reports
        rep_resp = await client.get("/api/v1/admin/reports", headers=auth_headers)
        assert rep_resp.status_code == 200, f"Reports failed: {rep_resp.text}"

        # 4. Admin Audit Logs
        audit_resp = await client.get("/api/v1/admin/audit-logs", headers=auth_headers)
        assert audit_resp.status_code == 200, f"Audit logs failed: {audit_resp.text}"


@pytest.mark.asyncio
async def test_missing_env_variables_handling(monkeypatch):
    """Criterion 6: Missing environment variables cause a clear, safe error."""
    # Temporarily unset INITIAL_ADMIN_EMAIL
    monkeypatch.setattr(settings, "INITIAL_ADMIN_EMAIL", None)
    monkeypatch.delenv("INITIAL_ADMIN_EMAIL", raising=False)

    is_valid, msg, creds = validate_credentials()
    assert is_valid is False
    assert creds is None
    assert "INITIAL_ADMIN_EMAIL" in msg
    assert "missing or empty" in msg

    # Restore email, unset password
    monkeypatch.setattr(settings, "INITIAL_ADMIN_EMAIL", "admin@gmail.com")
    monkeypatch.setattr(settings, "INITIAL_ADMIN_PASSWORD", None)
    monkeypatch.delenv("INITIAL_ADMIN_PASSWORD", raising=False)

    is_valid, msg, creds = validate_credentials()
    assert is_valid is False
    assert creds is None
    assert "INITIAL_ADMIN_PASSWORD" in msg
    assert "missing or empty" in msg


@pytest.mark.asyncio
async def test_conflict_with_existing_non_admin_role():
    """Criterion 7: Accounts under another role report conflict without silent promotion."""
    conflict_email = f"conflict_{uuid.uuid4().hex[:8]}@example.com"

    async with AsyncSessionLocal() as session:
        # Create a candidate user with this email
        candidate_user = User(
            id=str(uuid.uuid4()),
            email=conflict_email,
            hashed_password=hash_password("Password123!"),
            role="CANDIDATE",
            is_active=True,
            is_verified=True,
        )
        session.add(candidate_user)
        await session.commit()

        # Attempt to seed admin with same email
        creds = {
            "email": conflict_email,
            "password": "AdminPassword123!",
            "name": "Conflicting Admin",
            "role": "SUPER_ADMIN",
        }
        exit_code, msg = await seed_initial_admin(session, creds)
        assert exit_code == 1
        assert "Conflict detected" in msg
        assert "cannot overwrite or silently promote" in msg

        # Verify candidate account was NOT modified
        check_user = (await session.execute(select(User).where(User.email == conflict_email))).scalar_one()
        assert check_user.role == "CANDIDATE"

        # Cleanup test conflict user
        await session.delete(check_user)
        await session.commit()


@pytest.mark.asyncio
async def test_existing_accounts_unmodified():
    """Criterion 7: Existing admin accounts remain present and unaltered."""
    async with AsyncSessionLocal() as session:
        for email in ["admin1@ntrvikasa.com", "admin2@ntrvikasa.com"]:
            stmt = select(User).where(User.email == email)
            user = (await session.execute(stmt)).scalar_one_or_none()
            assert user is not None, f"Existing admin {email} missing!"
            assert user.role == "ADMIN"
            assert user.is_active is True
