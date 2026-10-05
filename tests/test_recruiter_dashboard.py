"""
Recruiter Dashboard Integration Tests
GET /api/v1/recruiter/dashboard

Tests cover:
1.  Unauthenticated request returns 401
2.  Candidate token returns 403
3.  Admin token returns 403
4.  Authenticated recruiter gets 200 with full structure
5.  Recruiter identity matches Arjun Reddy & ABC Technologies Pvt Ltd
6.  Summary metrics reflect MySQL database state
7.  Pipeline funnel counts match application statuses
8.  Recent applications list has required fields (no sensitive info leaked)
9.  Active jobs list has application counts
10. Upcoming interviews list has scheduled interviews
11. Recruiter isolation: Recruiter 2 cannot see Recruiter 1's jobs/applications
12. OpenAPI schema contains GET /api/v1/recruiter/dashboard
"""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


# ── Helpers ────────────────────────────────────────────────────────────────────

async def _login(client: AsyncClient, email: str, password: str = "password123", role: str = "RECRUITER") -> str:
    """Return a valid Bearer access token for the given credentials."""
    resp = await client.post("/api/v1/auth/login", json={
        "email": email,
        "password": password,
        "role": role,
    })
    assert resp.status_code == 200, f"Login failed for {email}: {resp.text}"
    return resp.json()["access_token"]


# ── 1. Unauthenticated ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_recruiter_dashboard_unauthenticated_returns_401():
    """No token → 401 Unauthorized."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/recruiter/dashboard")
    assert resp.status_code == 401


# ── 2. Candidate Role Forbidden ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_recruiter_dashboard_candidate_role_returns_403():
    """Candidate JWT must not access recruiter dashboard."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "candidate1@ntrvikasa.com", role="CANDIDATE")
        resp = await client.get(
            "/api/v1/recruiter/dashboard",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 403
    assert "Recruiter account required" in resp.json()["detail"]


# ── 3. Admin Role Forbidden ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_recruiter_dashboard_admin_role_returns_403():
    """Admin JWT must not access recruiter dashboard directly."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "admin1@ntrvikasa.com", role="ADMIN")
        resp = await client.get(
            "/api/v1/recruiter/dashboard",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 403


# ── 4. Happy Path: 200 with full structure ─────────────────────────────────────

@pytest.mark.asyncio
async def test_recruiter_dashboard_returns_200():
    """Recruiter gets 200 with complete response structure."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "recruiter1@ntrvikasa.com", role="RECRUITER")
        resp = await client.get(
            "/api/v1/recruiter/dashboard",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    data = resp.json()

    for key in ("recruiter", "summary", "pipeline", "recent_applications", "active_jobs", "upcoming_interviews"):
        assert key in data, f"Missing top-level key: {key}"

    # Recruiter Profile check
    rec = data["recruiter"]
    assert rec["name"] == "Arjun Reddy"
    assert "ABC Technologies" in rec["company_name"]
    assert rec["email"] == "recruiter1@ntrvikasa.com"


# ── 5. Summary Metrics ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_recruiter_dashboard_summary_metrics():
    """Summary counts match active jobs, pending approvals, applications, etc."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "recruiter1@ntrvikasa.com", role="RECRUITER")
        resp = await client.get(
            "/api/v1/recruiter/dashboard",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    summary = resp.json()["summary"]

    assert summary["active_jobs"] >= 3
    assert summary["pending_approvals"] >= 1
    assert summary["total_applications"] >= 5
    assert summary["shortlisted_pool"] >= 2
    assert summary["upcoming_interviews"] >= 3


# ── 6. Pipeline Conversion Funnel ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_recruiter_dashboard_pipeline_counts():
    """Pipeline funnel contains integer counts reflecting applications."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "recruiter1@ntrvikasa.com", role="RECRUITER")
        resp = await client.get(
            "/api/v1/recruiter/dashboard",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    pipeline = resp.json()["pipeline"]

    assert pipeline["applications"] >= 5
    assert pipeline["under_review"] >= 1
    assert pipeline["shortlisted"] >= 2
    assert pipeline["interviews"] >= 1
    assert pipeline["selected_hired"] >= 0


# ── 7. Recent Applications Structure ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_recruiter_dashboard_recent_applications():
    """Recent applications list contains required fields with both snake_case and camelCase."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "recruiter1@ntrvikasa.com", role="RECRUITER")
        resp = await client.get(
            "/api/v1/recruiter/dashboard",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    apps = resp.json()["recent_applications"]
    assert len(apps) > 0

    first = apps[0]
    assert "candidate_name" in first or "candidateName" in first
    assert "job_title" in first or "jobTitle" in first
    assert "status" in first
    assert "match_percentage" in first or "matchScore" in first

    # Ensure no sensitive information is leaked
    assert "password" not in first
    assert "hashed_password" not in first
    assert "aadhaar_number" not in first


# ── 8. Active Job Positions Structure ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_recruiter_dashboard_active_jobs():
    """Active jobs list contains published requisitions with applications_count."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "recruiter1@ntrvikasa.com", role="RECRUITER")
        resp = await client.get(
            "/api/v1/recruiter/dashboard",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    jobs = resp.json()["active_jobs"]
    assert len(jobs) > 0

    for j in jobs:
        assert j["status"] == "PUBLISHED"
        assert "title" in j
        assert "applications_count" in j
        assert isinstance(j["applications_count"], int)


# ── 9. Upcoming Interviews Structure ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_recruiter_dashboard_upcoming_interviews():
    """Upcoming interviews list contains scheduled interviews with meeting links."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "recruiter1@ntrvikasa.com", role="RECRUITER")
        resp = await client.get(
            "/api/v1/recruiter/dashboard",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    interviews = resp.json()["upcoming_interviews"]
    assert len(interviews) > 0

    first = interviews[0]
    assert first["status"] == "SCHEDULED"
    assert "candidate_name" in first or "candidateName" in first
    assert "meeting_platform" in first


# ── 10. Recruiter Isolation (Recruiter 2 sees only their own data) ─────────────

@pytest.mark.asyncio
async def test_recruiter_dashboard_data_isolation():
    """Recruiter 2 does not see Recruiter 1's jobs or applications."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "recruiter2@ntrvikasa.com", role="RECRUITER")
        resp = await client.get(
            "/api/v1/recruiter/dashboard",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    data = resp.json()

    # Recruiter 2 has not posted any jobs yet, so their summary should be 0
    assert data["summary"]["active_jobs"] == 0
    assert data["summary"]["total_applications"] == 0
    assert len(data["recent_applications"]) == 0
    assert len(data["active_jobs"]) == 0
    assert len(data["upcoming_interviews"]) == 0


# ── 11. OpenAPI / Swagger verification ────────────────────────────────────────

@pytest.mark.asyncio
async def test_recruiter_dashboard_in_openapi():
    """OpenAPI schema includes /api/v1/recruiter/dashboard."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/openapi.json")
    assert resp.status_code == 200
    schema = resp.json()
    assert "/api/v1/recruiter/dashboard" in schema["paths"]
    assert "get" in schema["paths"]["/api/v1/recruiter/dashboard"]
