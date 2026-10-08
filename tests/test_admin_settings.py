import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from app.main import app
from app.database.session import AsyncSessionLocal
from app.models.internship import AuditLog
from app.models.platform_settings import PlatformSettings


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
async def test_admin_settings_authorization():
    """Security tests for authentication and role requirements on /api/v1/admin/settings."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Unauthenticated request -> 401
        res_unauth = await client.get("/api/v1/admin/settings")
        assert res_unauth.status_code == 401

        res_patch_unauth = await client.patch(
            "/api/v1/admin/settings",
            json={"platform_display_name": "New Name"},
        )
        assert res_patch_unauth.status_code == 401

        # 2. Candidate token -> 403
        cand_token = await _login_user(client, "candidate1@ntrvikasa.com")
        res_cand = await client.get(
            "/api/v1/admin/settings",
            headers={"Authorization": f"Bearer {cand_token}"},
        )
        assert res_cand.status_code == 403

        res_cand_patch = await client.patch(
            "/api/v1/admin/settings",
            headers={"Authorization": f"Bearer {cand_token}"},
            json={"platform_maintenance_mode": True},
        )
        assert res_cand_patch.status_code == 403

        # 3. Recruiter token -> 403
        rec_token = await _login_user(client, "recruiter1@ntrvikasa.com")
        res_rec = await client.get(
            "/api/v1/admin/settings",
            headers={"Authorization": f"Bearer {rec_token}"},
        )
        assert res_rec.status_code == 403

        res_rec_patch = await client.patch(
            "/api/v1/admin/settings",
            headers={"Authorization": f"Bearer {rec_token}"},
            json={"mandatory_recruiter_legal_verification": False},
        )
        assert res_rec_patch.status_code == 403


@pytest.mark.asyncio
async def test_get_admin_settings_success():
    """Admin successfully fetches global platform settings."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        admin_token = await _login_admin(client, "admin1@ntrvikasa.com")

        res = await client.get(
            "/api/v1/admin/settings",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res.status_code == 200
        data = res.json()

        assert "id" in data
        assert "platform_display_name" in data
        assert "primary_support_email" in data
        assert "grievance_redressal_email" in data
        assert "mandatory_recruiter_legal_verification" in data
        assert "pre_publish_job_moderation_queue" in data
        assert "strict_zero_fee_candidate_rule" in data
        assert "platform_maintenance_mode" in data


@pytest.mark.asyncio
async def test_update_admin_settings_validation():
    """Validates schema validation rules on PATCH /api/v1/admin/settings."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        admin_token = await _login_admin(client, "admin1@ntrvikasa.com")

        # Invalid support email
        res1 = await client.patch(
            "/api/v1/admin/settings",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"primary_support_email": "invalid-email"},
        )
        assert res1.status_code == 422

        # Invalid grievance email
        res2 = await client.patch(
            "/api/v1/admin/settings",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"grievance_redressal_email": "not-an-email"},
        )
        assert res2.status_code == 422

        # Blank platform name
        res3 = await client.patch(
            "/api/v1/admin/settings",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"platform_display_name": "   "},
        )
        assert res3.status_code == 422


@pytest.mark.asyncio
async def test_update_admin_settings_success_and_audit():
    """Admin successfully updates settings, values persist in MySQL, and audit log is recorded."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        admin_token = await _login_admin(client, "admin1@ntrvikasa.com")

        update_payload = {
            "platform_display_name": "NTR VIKASA Enterprise Portal",
            "primary_support_email": "custom-support@ntrvikasa.com",
            "grievance_redressal_email": "custom-grievance@ntrvikasa.com",
            "mandatory_recruiter_legal_verification": True,
            "pre_publish_job_moderation_queue": True,
            "strict_zero_fee_candidate_rule": True,
            "platform_maintenance_mode": False,
        }

        res = await client.patch(
            "/api/v1/admin/settings",
            headers={"Authorization": f"Bearer {admin_token}"},
            json=update_payload,
        )
        assert res.status_code == 200
        data = res.json()
        assert data["platform_display_name"] == "NTR VIKASA Enterprise Portal"
        assert data["primary_support_email"] == "custom-support@ntrvikasa.com"
        assert data["grievance_redressal_email"] == "custom-grievance@ntrvikasa.com"

        # Verify DB persistence
        async with AsyncSessionLocal() as session:
            stmt = select(PlatformSettings).where(PlatformSettings.id == 1)
            result = await session.execute(stmt)
            db_settings = result.scalar_one_or_none()
            assert db_settings is not None
            assert db_settings.platform_display_name == "NTR VIKASA Enterprise Portal"
            assert db_settings.primary_support_email == "custom-support@ntrvikasa.com"

            # Check audit log entry
            audit_stmt = (
                select(AuditLog)
                .where(AuditLog.action == "PLATFORM_SETTINGS_UPDATED")
                .order_by(AuditLog.timestamp.desc())
            )
            audit_result = await session.execute(audit_stmt)
            latest_audit = audit_result.scalars().first()
            assert latest_audit is not None
            assert latest_audit.entity in ["PLATFORM_SETTINGS", "PlatformSettings"]
            assert latest_audit.entity_id == "1"


@pytest.mark.asyncio
async def test_maintenance_mode_behavior():
    """Test that maintenance mode blocks candidate registration when enabled and allows it when disabled."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        admin_token = await _login_admin(client, "admin1@ntrvikasa.com")

        # 1. Enable Maintenance Mode
        res_maint_on = await client.patch(
            "/api/v1/admin/settings",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"platform_maintenance_mode": True},
        )
        assert res_maint_on.status_code == 200
        assert res_maint_on.json()["platform_maintenance_mode"] is True

        # 2. Try candidate registration -> 503
        reg_payload = {
            "name": "Maint Tester",
            "email": "maint_test_unique_123@example.com",
            "phone": "9876543210",
            "password": "Password123!",
            "aadhaar_number": "999988887777",
            "district": "NTR District",
            "mandal": "Vijayawada Urban",
            "village": "Bhavanipuram",
            "qualification_level": "GRADUATE",
            "terms_accepted": True,
        }
        res_reg = await client.post("/api/v1/auth/candidate/register", json=reg_payload)
        assert res_reg.status_code == 503
        assert "maintenance" in res_reg.json()["detail"].lower()

        # 3. Admin dashboard / settings still accessible
        res_admin_still_works = await client.get(
            "/api/v1/admin/settings",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res_admin_still_works.status_code == 200

        # 4. Disable Maintenance Mode
        res_maint_off = await client.patch(
            "/api/v1/admin/settings",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"platform_maintenance_mode": False},
        )
        assert res_maint_off.status_code == 200
        assert res_maint_off.json()["platform_maintenance_mode"] is False


@pytest.mark.asyncio
async def test_zero_fee_candidate_rule_enforcement():
    """Test that jobs with registration fee or security deposit mentions are rejected when zero fee rule is active."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        admin_token = await _login_admin(client, "admin1@ntrvikasa.com")

        # 1. Enable Zero-Fee Rule
        await client.patch(
            "/api/v1/admin/settings",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"strict_zero_fee_candidate_rule": True},
        )

        rec_token = await _login_user(client, "recruiter1@ntrvikasa.com")

        invalid_payload = {
            "title": "Security Deposit Requisition Role",
            "department": "IT Operations",
            "job_type": "Full-time",
            "work_mode": "On-site",
            "location": "Vijayawada, AP",
            "experience": "1-3 years",
            "salary_min": 300000,
            "salary_max": 500000,
            "salary": "₹3,00,000 - ₹5,00,000 / year",
            "openings": 1,
            "deadline": "2026-12-31",
            "description": "Candidates must pay a mandatory registration fee of 500 INR prior to interview.",
            "responsibilities": "Handle daily operations.",
            "requirements": "Knowledge of basic software.",
            "qualifications": "Bachelors degree.",
            "skills": ["Python", "SQL"],
        }

        resp = await client.post(
            "/api/v1/recruiters/jobs",
            json=invalid_payload,
            headers={"Authorization": f"Bearer {rec_token}"},
        )
        assert resp.status_code in [400, 422]
        assert "zero-fee" in resp.json()["detail"].lower() or "fee" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_pre_publish_moderation_queue_behavior():
    """Test that pre_publish_job_moderation_queue puts new jobs in PENDING when true and PUBLISHED when false."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        admin_token = await _login_admin(client, "admin1@ntrvikasa.com")
        rec_token = await _login_user(client, "recruiter1@ntrvikasa.com")

        valid_payload = {
            "title": "Clean Test Requisition Role",
            "department": "IT Operations",
            "job_type": "Full-time",
            "work_mode": "On-site",
            "location": "Vijayawada, AP",
            "experience": "1-3 years",
            "salary_min": 300000,
            "salary_max": 500000,
            "salary": "₹3,00,000 - ₹5,00,000 / year",
            "openings": 1,
            "deadline": "2026-12-31",
            "description": "Clean job requisition without any fee violation.",
            "responsibilities": "Handle daily operations.",
            "requirements": "Knowledge of basic software.",
            "qualifications": "Bachelors degree.",
            "skills": ["Python", "SQL"],
        }

        # 1. Moderation Queue ON -> PENDING
        await client.patch(
            "/api/v1/admin/settings",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"pre_publish_job_moderation_queue": True},
        )
        res_queue_on = await client.post(
            "/api/v1/recruiters/jobs",
            json=valid_payload,
            headers={"Authorization": f"Bearer {rec_token}"},
        )
        assert res_queue_on.status_code == 201
        assert res_queue_on.json()["status"] == "PENDING"

        # 2. Moderation Queue OFF -> PUBLISHED
        await client.patch(
            "/api/v1/admin/settings",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"pre_publish_job_moderation_queue": False},
        )
        valid_payload["title"] = "Direct Publish Requisition Role"
        res_queue_off = await client.post(
            "/api/v1/recruiters/jobs",
            json=valid_payload,
            headers={"Authorization": f"Bearer {rec_token}"},
        )
        assert res_queue_off.status_code == 201
        assert res_queue_off.json()["status"] == "PUBLISHED"

        # Restore default
        await client.patch(
            "/api/v1/admin/settings",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"pre_publish_job_moderation_queue": True},
        )

