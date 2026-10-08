import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


async def _login_admin(client: AsyncClient, email: str = "admin1@ntrvikasa.com", password: str = "password123") -> str:
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200
    return resp.json()["access_token"]


async def _login_user(client: AsyncClient, email: str, password: str = "password123") -> str:
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200
    return resp.json()["access_token"]


@pytest.mark.asyncio
async def test_admin_dashboard_authorization():
    """Security tests: Admin required, 401 for unauthenticated, 403 for candidate & recruiter."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Unauthenticated -> 401
        res_unauth = await client.get("/api/v1/admin/dashboard")
        assert res_unauth.status_code == 401

        # 2. Candidate token -> 403
        cand_token = await _login_user(client, "candidate1@ntrvikasa.com")
        res_cand = await client.get(
            "/api/v1/admin/dashboard",
            headers={"Authorization": f"Bearer {cand_token}"},
        )
        assert res_cand.status_code == 403

        # 3. Recruiter token -> 403
        rec_token = await _login_user(client, "recruiter1@ntrvikasa.com")
        res_rec = await client.get(
            "/api/v1/admin/dashboard",
            headers={"Authorization": f"Bearer {rec_token}"},
        )
        assert res_rec.status_code == 403


@pytest.mark.asyncio
async def test_get_admin_dashboard_success_and_structure():
    """Admin successfully fetches platform command center dashboard with all cards and streams."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        admin_token = await _login_admin(client, "admin1@ntrvikasa.com")

        res = await client.get(
            "/api/v1/admin/dashboard",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res.status_code == 200
        data = res.json()

        # Check moderation queue
        assert "moderation_queue" in data
        mq = data["moderation_queue"]
        assert "pending_recruiter_verifications" in mq
        assert "pending_company_verifications" in mq
        assert "pending_job_approvals" in mq
        assert "pending_internship_approvals" in mq
        assert "pending_job_mela_approvals" in mq
        assert "open_moderation_reports" in mq
        assert "total_pending" in mq
        assert isinstance(mq["pending_recruiter_verifications"], int)

        # Check platform overview
        assert "platform_overview" in data
        po = data["platform_overview"]
        assert "total_candidates" in po
        assert "total_recruiters" in po
        assert "verified_companies" in po
        assert "active_jobs" in po
        assert "submitted_applications" in po
        assert "job_mela_registrations" in po
        assert po["total_candidates"] >= 0

        # Check moderation stream
        assert "pending_moderation_stream" in data
        assert isinstance(data["pending_moderation_stream"], list)
        for item in data["pending_moderation_stream"]:
            assert "type" in item
            assert "name" in item
            assert "entity" in item
            assert "link" in item

        # Check recent audit logs
        assert "recent_audit_logs" in data
        assert isinstance(data["recent_audit_logs"], list)
        for log in data["recent_audit_logs"]:
            assert "action" in log
            assert "target" in log
            assert "result" in log
