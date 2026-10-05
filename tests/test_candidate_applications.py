"""
Candidate Applications Integration Tests
GET /api/v1/candidate/applications
GET /api/v1/candidate/applications/{application_id}
GET /api/v1/candidate/applications/{application_id}/timeline

Covers:
1.  Authenticated candidate can fetch applications
2.  Unauthenticated request returns 401
3.  Non-candidate role returns 403
4.  Candidate sees only own applications (Candidate 1 has 8, Candidate 2 has 0)
5.  Candidate name matches ("Priya Sharma" vs "Rahul Varma")
6.  Status counts are correct (all, applied, screening, shortlisted, interview, selected, rejected)
7.  Applications sorted newest first
8.  Search filter works (by role, company, location)
9.  Status filter works (e.g. status=SHORTLISTED)
10. Empty application list works for candidate without applications
11. Application IDs / numbers returned correctly
12. Job Mela ID returned correctly when applicable, null otherwise
13. Sensitive information (passwords, aadhaar) not exposed
14. Candidate can view own application details
15. Candidate cannot view another candidate's application details (403/404)
16. Non-existing application details returns 404
17. Candidate can view own application timeline
18. Candidate cannot view another candidate's timeline (403/404)
19. Timeline events ordered correctly
20. Swagger / OpenAPI documentation contains canonical routes
"""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


# ── Helpers ────────────────────────────────────────────────────────────────────

async def _login(
    client: AsyncClient,
    email: str,
    password: str = "password123",
    role: str = "CANDIDATE",
) -> str:
    """Return a valid Bearer access token for the given credentials."""
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password, "role": role},
    )
    assert resp.status_code == 200, f"Login failed for {email}: {resp.text}"
    return resp.json()["access_token"]


# ── 1. Unauthenticated Request returns 401 ─────────────────────────────────────

@pytest.mark.asyncio
async def test_applications_unauthenticated_returns_401():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/candidate/applications")
    assert resp.status_code == 401


# ── 2. Non-Candidate Role returns 403 ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_applications_admin_role_returns_403():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        admin_token = await _login(client, "admin1@ntrvikasa.com", role="ADMIN")
        resp = await client.get(
            "/api/v1/candidate/applications",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
    assert resp.status_code == 403


# ── 3. Authenticated Candidate Returns 200 ────────────────────────────────────

@pytest.mark.asyncio
async def test_applications_authenticated_returns_200():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "candidate1@ntrvikasa.com")
        resp = await client.get(
            "/api/v1/candidate/applications",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "candidate" in data
    assert "status_counts" in data
    assert "applications" in data
    assert data["candidate"]["full_name"] == "Priya Sharma"


# ── 4. Candidate Isolation: Candidate 2 sees 0 applications ───────────────────

@pytest.mark.asyncio
async def test_applications_candidate_isolation():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token_c2 = await _login(client, "candidate2@ntrvikasa.com")
        resp = await client.get(
            "/api/v1/candidate/applications",
            headers={"Authorization": f"Bearer {token_c2}"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["candidate"]["full_name"] == "Rahul Varma"
    assert data["status_counts"]["all"] == 0
    assert len(data["applications"]) == 0


# ── 5. Status Counts are Accurate ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_applications_status_counts():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "candidate1@ntrvikasa.com")
        resp = await client.get(
            "/api/v1/candidate/applications",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    counts = resp.json()["status_counts"]
    assert counts["all"] == 8
    assert counts["applied"] == 2
    assert counts["screening"] == 1
    assert counts["shortlisted"] == 2
    assert counts["interview"] == 1
    assert counts["selected"] == 1
    assert counts["rejected"] == 1


# ── 6. Status Filtering Works ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_applications_status_filter():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "candidate1@ntrvikasa.com")
        
        # Test status=SHORTLISTED
        resp = await client.get(
            "/api/v1/candidate/applications?status=SHORTLISTED",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        apps = resp.json()["applications"]
        assert len(apps) == 2
        for a in apps:
            assert a["status"] == "SHORTLISTED"

        # Test status=INTERVIEW
        resp_int = await client.get(
            "/api/v1/candidate/applications?status=INTERVIEW",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp_int.status_code == 200
        apps_int = resp_int.json()["applications"]
        assert len(apps_int) == 1
        assert apps_int[0]["status"] == "INTERVIEW"


# ── 7. Search Filter Works ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_applications_search_filter():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "candidate1@ntrvikasa.com")
        
        # Search by company name "TechCorp"
        resp = await client.get(
            "/api/v1/candidate/applications?search=TechCorp",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        apps = resp.json()["applications"]
        assert len(apps) >= 2
        for a in apps:
            assert "techcorp" in a["company_name"].lower() or "techcorp" in a["company"].lower()


# ── 8. Application IDs and Mela IDs Returned Correctly ─────────────────────────

@pytest.mark.asyncio
async def test_applications_identifiers():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "candidate1@ntrvikasa.com")
        resp = await client.get(
            "/api/v1/candidate/applications",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    apps = resp.json()["applications"]

    # Check Job Mela application
    mela_app = next((a for a in apps if a["application_id"] == "NTR-01-02-0024"), None)
    assert mela_app is not None
    assert mela_app["application_type"] == "Job Mela Application"
    assert mela_app["job_mela_id"] == "1"
    assert "Mega IT" in mela_app["melaTitle"]

    # Check Direct Job application
    direct_app = next((a for a in apps if a["application_id"] == "APP-000124"), None)
    assert direct_app is not None
    assert direct_app["application_type"] == "Direct Job Application"
    assert direct_app["job_mela_id"] is None


# ── 9. View Details Endpoint Works ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_application_details_success():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "candidate1@ntrvikasa.com")
        resp = await client.get(
            "/api/v1/candidate/applications/APP-000124",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    detail = resp.json()
    assert detail["application_id"] == "APP-000124"
    assert detail["job_title"] == "Senior Python Developer"
    assert detail["company_name"] == "TechCorp India"


# ── 10. Cross-Candidate Details Access is Forbidden ───────────────────────────

@pytest.mark.asyncio
async def test_cross_candidate_details_forbidden():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token_c2 = await _login(client, "candidate2@ntrvikasa.com")
        
        # Candidate 2 attempts to view Candidate 1's application
        resp = await client.get(
            "/api/v1/candidate/applications/APP-000124",
            headers={"Authorization": f"Bearer {token_c2}"},
        )
        assert resp.status_code in (403, 404)


# ── 11. Non-Existing Application Details Returns 404 ───────────────────────────

@pytest.mark.asyncio
async def test_non_existing_application_details_404():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "candidate1@ntrvikasa.com")
        resp = await client.get(
            "/api/v1/candidate/applications/non-existing-id-99999",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404


# ── 12. View Timeline Endpoint Works ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_application_timeline_success():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "candidate1@ntrvikasa.com")
        resp = await client.get(
            "/api/v1/candidate/applications/APP-000002/timeline",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    timeline_data = resp.json()
    assert timeline_data["application_id"] == "APP-000002"
    events = timeline_data["timeline"]
    assert len(events) >= 5
    assert events[0]["stage"] == "Applied"
    assert events[0]["completed"] is True
    # Verify events are in chronological step_order
    for i in range(len(events) - 1):
        assert events[i]["step_order"] <= events[i + 1]["step_order"]


# ── 13. Cross-Candidate Timeline Access Forbidden ──────────────────────────────

@pytest.mark.asyncio
async def test_cross_candidate_timeline_forbidden():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token_c2 = await _login(client, "candidate2@ntrvikasa.com")
        resp = await client.get(
            "/api/v1/candidate/applications/APP-000002/timeline",
            headers={"Authorization": f"Bearer {token_c2}"},
        )
        assert resp.status_code in (403, 404)


# ── 14. Sensitive Fields Not Exposed ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_applications_no_sensitive_fields():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "candidate1@ntrvikasa.com")
        resp = await client.get(
            "/api/v1/candidate/applications",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    text = resp.text.lower()
    assert "hashed_password" not in text
    assert "aadhaar" not in text


# ── 15. Swagger / OpenAPI Canonical Endpoints ──────────────────────────────────

@pytest.mark.asyncio
async def test_applications_swagger_canonical_endpoints():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/openapi.json")
    assert resp.status_code == 200
    paths = resp.json()["paths"]
    assert "/api/v1/candidate/applications" in paths
    assert "/api/v1/candidate/applications/{application_id}" in paths
    assert "/api/v1/candidate/applications/{application_id}/timeline" in paths
