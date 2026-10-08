import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from app.main import app
from app.database.session import AsyncSessionLocal
from app.models.internship import AuditLog
from app.models.user import User


async def _login_user(client: AsyncClient, email: str, password: str = "password123") -> str:
    """Helper to authenticate user and return JWT access token."""
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, f"Login failed for {email}: {resp.text}"
    return resp.json()["access_token"]


@pytest.mark.asyncio
async def test_change_password_unauthenticated():
    """Unauthenticated call to POST /api/v1/auth/change-password returns 401."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/v1/auth/change-password",
            json={
                "current_password": "password123",
                "new_password": "NewSecretPass123",
                "confirm_password": "NewSecretPass123",
            },
        )
        assert res.status_code == 401


@pytest.mark.asyncio
async def test_change_password_wrong_current_password():
    """Providing wrong current password returns 401 Unauthorized."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login_user(client, "admin2@ntrvikasa.com", "password123")

        res = await client.post(
            "/api/v1/auth/change-password",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "current_password": "WrongPassword999",
                "new_password": "NewAdminPass123",
                "confirm_password": "NewAdminPass123",
            },
        )
        assert res.status_code == 401
        assert "Current password is incorrect" in res.json().get("detail", "")


@pytest.mark.asyncio
async def test_change_password_validation_rules():
    """Validates minimum length (8), numbers, letters, mismatch, and same password."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login_user(client, "admin2@ntrvikasa.com", "password123")

        # 1. Short password (< 8 chars) -> 422
        res_short = await client.post(
            "/api/v1/auth/change-password",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "current_password": "password123",
                "new_password": "Abc1",
                "confirm_password": "Abc1",
            },
        )
        assert res_short.status_code == 422
        assert "8 characters" in res_short.json().get("detail", "")

        # 2. No number -> 422
        res_no_num = await client.post(
            "/api/v1/auth/change-password",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "current_password": "password123",
                "new_password": "PasswordSecretOnly",
                "confirm_password": "PasswordSecretOnly",
            },
        )
        assert res_no_num.status_code == 422
        assert "number" in res_no_num.json().get("detail", "")

        # 3. No letter -> 422
        res_no_letter = await client.post(
            "/api/v1/auth/change-password",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "current_password": "password123",
                "new_password": "1234567890",
                "confirm_password": "1234567890",
            },
        )
        assert res_no_letter.status_code == 422
        assert "letter" in res_no_letter.json().get("detail", "")

        # 4. Confirmation mismatch -> 422
        res_mismatch = await client.post(
            "/api/v1/auth/change-password",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "current_password": "password123",
                "new_password": "NewValidPass123",
                "confirm_password": "DifferentPass123",
            },
        )
        assert res_mismatch.status_code == 422
        assert "match" in res_mismatch.json().get("detail", "")

        # 5. Same as current password -> 400
        res_same = await client.post(
            "/api/v1/auth/change-password",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "current_password": "password123",
                "new_password": "password123",
                "confirm_password": "password123",
            },
        )
        assert res_same.status_code == 400
        assert "different from the current password" in res_same.json().get("detail", "")


@pytest.mark.asyncio
async def test_admin_change_password_full_cycle_and_audit():
    """
    Complete flow for admin password change:
    1. Admin authenticates with current password.
    2. Changes password to new secure password.
    3. Receives HTTP 200 with safe success response.
    4. Audit log entry is created in database.
    5. Old password no longer works for login.
    6. New password successfully logs in.
    7. Restores password back for other tests.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Step 1: Login admin2
        admin_email = "admin2@ntrvikasa.com"
        orig_pass = "password123"
        new_pass = "AdminUpdatedPass999"

        token = await _login_user(client, admin_email, orig_pass)

        # Step 2: Change password
        res = await client.post(
            "/api/v1/auth/change-password",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "current_password": orig_pass,
                "new_password": new_pass,
                "confirm_password": new_pass,
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert "Password changed successfully." in data["message"]
        assert "password" not in data
        assert "hashed_password" not in data

        # Step 3: Verify audit log recorded in MySQL
        async with AsyncSessionLocal() as session:
            stmt = select(AuditLog).where(
                AuditLog.action == "ADMIN_PASSWORD_CHANGED",
                AuditLog.actor == admin_email,
            ).order_by(AuditLog.timestamp.desc())
            res_db = await session.execute(stmt)
            audit = res_db.scalars().first()
            assert audit is not None
            assert audit.action == "ADMIN_PASSWORD_CHANGED"
            assert audit.actor == admin_email
            assert audit.entity == "USER"

        # Step 4: Old password fails login
        res_old = await client.post(
            "/api/v1/auth/login",
            json={"email": admin_email, "password": orig_pass},
        )
        assert res_old.status_code == 401

        # Step 5: New password succeeds login
        res_new = await client.post(
            "/api/v1/auth/login",
            json={"email": admin_email, "password": new_pass},
        )
        assert res_new.status_code == 200
        new_token = res_new.json()["access_token"]
        assert new_token is not None

        # Step 6: Restore back to original password
        res_restore = await client.post(
            "/api/v1/auth/change-password",
            headers={"Authorization": f"Bearer {new_token}"},
            json={
                "current_password": new_pass,
                "new_password": orig_pass,
                "confirm_password": orig_pass,
            },
        )
        assert res_restore.status_code == 200
