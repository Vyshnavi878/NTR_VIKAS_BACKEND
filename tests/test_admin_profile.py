import io
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from app.main import app
from app.database.session import AsyncSessionLocal
from app.models.internship import AuditLog


async def _login_admin(client: AsyncClient, email: str = "admin1@ntrvikasa.com", password: str = "password123") -> str:
    """Helper to authenticate admin and return JWT access token."""
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200
    return resp.json()["access_token"]


async def _login_user(client: AsyncClient, email: str, password: str = "password123") -> str:
    """Helper to authenticate user and return JWT access token."""
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200
    return resp.json()["access_token"]


@pytest.mark.asyncio
async def test_admin_profile_authentication_and_authorization():
    """Security tests for authentication and role requirements on /api/v1/admin/profile."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Unauthenticated request -> 401
        res_unauth = await client.get("/api/v1/admin/profile")
        assert res_unauth.status_code == 401

        # 2. Candidate token -> 403
        cand_token = await _login_user(client, "candidate1@ntrvikasa.com")
        res_cand = await client.get(
            "/api/v1/admin/profile",
            headers={"Authorization": f"Bearer {cand_token}"},
        )
        assert res_cand.status_code == 403

        # 3. Recruiter token -> 403
        rec_token = await _login_user(client, "recruiter1@ntrvikasa.com")
        res_rec = await client.get(
            "/api/v1/admin/profile",
            headers={"Authorization": f"Bearer {rec_token}"},
        )
        assert res_rec.status_code == 403


@pytest.mark.asyncio
async def test_get_admin_profile_success():
    """Admin successfully fetches their profile with correct attributes."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        admin_token = await _login_admin(client, "admin1@ntrvikasa.com")

        res = await client.get(
            "/api/v1/admin/profile",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res.status_code == 200
        data = res.json()

        assert "id" in data
        assert data["email"] == "admin1@ntrvikasa.com"
        assert isinstance(data["full_name"], str) and len(data["full_name"]) > 0
        assert data["role"] in ["Platform Administrator", "PLATFORM_ADMINISTRATOR", "ADMIN"]
        assert data["status"] == "ACTIVE"
        assert "password" not in data
        assert "hashed_password" not in data
        assert "jwt" not in data



@pytest.mark.asyncio
async def test_update_admin_profile_success_and_audit():
    """Admin successfully updates their profile fields and audit log is created."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        admin_token = await _login_admin(client, "admin1@ntrvikasa.com")

        update_payload = {
            "full_name": "Admin State Lead",
            "designation": "Chief Operations Director",
            "contact_phone": "+91 98765 43210",
        }

        res = await client.patch(
            "/api/v1/admin/profile",
            headers={"Authorization": f"Bearer {admin_token}"},
            json=update_payload,
        )
        assert res.status_code == 200
        data = res.json()
        assert data["full_name"] == "Admin State Lead"
        assert data["designation"] == "Chief Operations Director"
        assert data["contact_phone"] == "+91 98765 43210"

        # Verify audit log in database
        async with AsyncSessionLocal() as session:
            stmt = select(AuditLog).where(
                AuditLog.action == "ADMIN_PROFILE_UPDATED",
                AuditLog.actor == "admin1@ntrvikasa.com",
            )
            res_db = await session.execute(stmt)
            logs = res_db.scalars().all()
            assert len(logs) > 0


@pytest.mark.asyncio
async def test_update_admin_profile_validation_errors():
    """Validation errors for blank full_name, invalid phone, or duplicate email."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        admin_token = await _login_admin(client, "admin1@ntrvikasa.com")

        # 1. Blank full name -> 422
        res_blank_name = await client.patch(
            "/api/v1/admin/profile",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"full_name": "   "},
        )
        assert res_blank_name.status_code == 422

        # 2. Invalid phone format -> 422
        res_invalid_phone = await client.patch(
            "/api/v1/admin/profile",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"contact_phone": "123"},
        )
        assert res_invalid_phone.status_code == 422

        # 3. Duplicate email -> 400
        res_dup_email = await client.patch(
            "/api/v1/admin/profile",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"email": "candidate1@ntrvikasa.com"},
        )
        assert res_dup_email.status_code == 400


@pytest.mark.asyncio
async def test_admin_profile_image_upload_and_validation():
    """Upload admin profile image with validation on format and size."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        admin_token = await _login_admin(client, "admin1@ntrvikasa.com")

        # 1. Valid PNG upload
        png_content = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
        files = {"file": ("test_avatar.png", io.BytesIO(png_content), "image/png")}

        res_img = await client.post(
            "/api/v1/admin/profile/image",
            headers={"Authorization": f"Bearer {admin_token}"},
            files=files,
        )
        assert res_img.status_code == 200
        img_data = res_img.json()
        assert "profile_image_url" in img_data
        assert img_data["profile_image_url"].startswith("/uploads/admin/profile/")

        # Verify GET /api/v1/admin/profile now contains profile_image_url
        res_prof = await client.get(
            "/api/v1/admin/profile",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res_prof.status_code == 200
        assert res_prof.json()["profile_image_url"] == img_data["profile_image_url"]

        # 2. Invalid file type (.txt / text/plain)
        files_bad = {"file": ("malicious.txt", io.BytesIO(b"hello world"), "text/plain")}
        res_bad = await client.post(
            "/api/v1/admin/profile/image",
            headers={"Authorization": f"Bearer {admin_token}"},
            files=files_bad,
        )
        assert res_bad.status_code == 422

        # 3. Oversized file (>2MB)
        large_content = b"0" * (2 * 1024 * 1024 + 100)
        files_large = {"file": ("large.png", io.BytesIO(large_content), "image/png")}
        res_large = await client.post(
            "/api/v1/admin/profile/image",
            headers={"Authorization": f"Bearer {admin_token}"},
            files=files_large,
        )
        assert res_large.status_code == 422
