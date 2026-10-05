"""
Recruiter Job Mela Participation Integration Tests
GET /api/v1/recruiter/job-melas
GET /api/v1/recruiter/job-melas/available
POST /api/v1/recruiter/job-melas/participate
GET /api/v1/admin/job-melas/participations
PATCH /api/v1/admin/job-melas/participations/{id}/approve
PATCH /api/v1/admin/job-melas/participations/{id}/reject
GET /api/v1/job-melas/{id}/companies

Tests cover:
1.  Unauthenticated request to /recruiter/job-melas returns 401
2.  Candidate token returns 403 Forbidden
3.  Admin token returns 403 Forbidden
4.  Authenticated recruiter gets 200 with list of job melas
5.  Status tab filtering: APPROVED vs PENDING
6.  Search query filtering by title / city / venue
7.  Available job melas endpoint returns published events for dropdown
8.  Recruiter registers for mela -> status is created strictly as PENDING
9.  Duplicate participation request is rejected with 400 Bad Request
10. Nonexistent Job Mela returns 404 Not Found
11. Admin participations endpoint requires ADMIN role (401 / 403)
12. Admin lists company participation requests with status and details
13. Admin approves participation -> sets APPROVED status and assigns booth
14. Admin rejects participation -> sets REJECTED status with mandatory reason
15. Approved company becomes available in Candidate Job Mela experience
16. Multi-tenant recruiter isolation: Recruiter 2 does not share Recruiter 1's participation
17. OpenAPI schema documents all recruiter and admin job mela endpoints
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text
from app.main import app
from app.database.session import AsyncSessionLocal


# ── Cleanup Fixture ────────────────────────────────────────────────────────────

@pytest_asyncio.fixture(autouse=True)
async def cleanup_test_participations():
    """Ensure test Job Melas (mela-13, mela-14, mela-15) are clean before and after each test."""
    async with AsyncSessionLocal() as session:
        await session.execute(
            text("DELETE FROM job_mela_company_participations WHERE job_mela_id IN ('mela-13', 'mela-14', 'mela-15')")
        )
        await session.commit()
    yield
    async with AsyncSessionLocal() as session:
        await session.execute(
            text("DELETE FROM job_mela_company_participations WHERE job_mela_id IN ('mela-13', 'mela-14', 'mela-15')")
        )
        await session.commit()


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
async def test_recruiter_job_melas_unauthenticated_returns_401():
    """No token → 401 Unauthorized."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/recruiter/job-melas")
    assert resp.status_code == 401


# ── 2. Candidate Role Forbidden ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_recruiter_job_melas_candidate_forbidden_returns_403():
    """Candidate JWT must not access recruiter job melas."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "candidate1@ntrvikasa.com", role="CANDIDATE")
        resp = await client.get(
            "/api/v1/recruiter/job-melas",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 403
    assert "Recruiter account required" in resp.json()["detail"]


# ── 3. Admin Role Forbidden ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_recruiter_job_melas_admin_forbidden_returns_403():
    """Admin JWT must not access recruiter job melas directly."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "admin1@ntrvikasa.com", role="ADMIN")
        resp = await client.get(
            "/api/v1/recruiter/job-melas",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 403


# ── 4. Happy Path: 200 with full list ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_recruiter_job_melas_returns_200():
    """Recruiter gets 200 with list of Job Melas containing participation status."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "recruiter1@ntrvikasa.com", role="RECRUITER")
        resp = await client.get(
            "/api/v1/recruiter/job-melas",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    events = resp.json()
    assert isinstance(events, list)
    assert len(events) >= 12

    first = events[0]
    required_keys = (
        "id",
        "mela_number",
        "title",
        "date",
        "time",
        "venue",
        "city",
        "participation_status",
        "status",
        "booth_number",
        "boothNumber",
    )
    for key in required_keys:
        assert key in first, f"Missing key in event: {key}"


# ── 5. Status Tab Filtering: APPROVED vs PENDING ───────────────────────────────

@pytest.mark.asyncio
async def test_recruiter_job_melas_status_tab_filtering():
    """Filter by APPROVED returns only approved events; PENDING returns only pending."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "recruiter1@ntrvikasa.com", role="RECRUITER")

        # Test APPROVED filter
        resp_approved = await client.get(
            "/api/v1/recruiter/job-melas?status=APPROVED",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp_approved.status_code == 200
        approved_events = resp_approved.json()
        assert len(approved_events) > 0
        for ev in approved_events:
            assert ev["participation_status"] == "APPROVED"
            assert ev["status"] == "APPROVED"

        # Test PENDING filter
        resp_pending = await client.get(
            "/api/v1/recruiter/job-melas?status=PENDING",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp_pending.status_code == 200
        pending_events = resp_pending.json()
        assert len(pending_events) > 0
        for ev in pending_events:
            assert ev["participation_status"] == "PENDING"
            assert ev["status"] == "PENDING"


# ── 6. Search Filtering ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_recruiter_job_melas_search_filtering():
    """Search query filters events by title, venue, or city."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "recruiter1@ntrvikasa.com", role="RECRUITER")
        resp = await client.get(
            "/api/v1/recruiter/job-melas?search=Bengaluru",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    events = resp.json()
    assert len(events) >= 1
    assert any("Bengaluru" in e["title"] or "Bengaluru" in e["city"] for e in events)


# ── 7. Available Job Melas ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_recruiter_available_job_melas():
    """Recruiter gets list of published Job Melas for modal dropdown."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "recruiter1@ntrvikasa.com", role="RECRUITER")
        resp = await client.get(
            "/api/v1/recruiter/job-melas/available",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    melas = resp.json()
    assert len(melas) >= 12
    first = melas[0]
    assert "id" in first
    assert "title" in first
    assert "event_date" in first
    assert "city" in first


# ── 8. Recruiter Registers for Job Mela (strictly PENDING) ─────────────────────

@pytest.mark.asyncio
async def test_recruiter_register_participation_pending():
    """Recruiter registers for an upcoming event -> created strictly as PENDING."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "recruiter1@ntrvikasa.com", role="RECRUITER")
        resp = await client.post(
            "/api/v1/recruiter/job-melas/participate",
            json={
                "job_mela_id": "mela-13",
                "title": "Visakhapatnam IT & FinTech Job Fair 2026",
                "openings": "React Engineers, Cloud Specialists, Python Devs",
                "target_hires": 25,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "PENDING"
    assert data["job_mela_id"] == "mela-13"
    assert data["target_hires"] == 25
    assert "React Engineers" in data["openings"]
    assert "pending administrative review" in data["message"].lower()


# ── 9. Duplicate Participation Request Rejected ────────────────────────────────

@pytest.mark.asyncio
async def test_recruiter_register_duplicate_rejected():
    """Attempting to register again for the same Job Mela returns 400 Bad Request."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "recruiter1@ntrvikasa.com", role="RECRUITER")
        # First registration
        resp1 = await client.post(
            "/api/v1/recruiter/job-melas/participate",
            json={
                "job_mela_id": "mela-13",
                "title": "Visakhapatnam IT & FinTech Job Fair 2026",
                "openings": "React Engineers",
                "target_hires": 10,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp1.status_code == 201

        # Second registration for same event
        resp2 = await client.post(
            "/api/v1/recruiter/job-melas/participate",
            json={
                "job_mela_id": "mela-13",
                "title": "Visakhapatnam IT & FinTech Job Fair 2026",
                "openings": "Cloud Specialists",
                "target_hires": 5,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp2.status_code == 400
    assert "already" in resp2.json()["detail"].lower()


# ── 10. Nonexistent Job Mela 404 ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_recruiter_register_nonexistent_mela_returns_404():
    """Registering for a nonexistent event returns 404."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "recruiter1@ntrvikasa.com", role="RECRUITER")
        resp = await client.post(
            "/api/v1/recruiter/job-melas/participate",
            json={
                "job_mela_id": "nonexistent-mela-999",
                "title": "Fictional Job Fair",
                "openings": "Engineers",
                "target_hires": 5,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 404


# ── 11. Admin Participations Endpoint Authentication & Roles ───────────────────

@pytest.mark.asyncio
async def test_admin_participations_auth():
    """Admin participations endpoint requires ADMIN role."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Unauthenticated
        resp_unauth = await client.get("/api/v1/admin/job-melas/participations")
        assert resp_unauth.status_code == 401

        # Recruiter forbidden
        rec_token = await _login(client, "recruiter1@ntrvikasa.com", role="RECRUITER")
        resp_rec = await client.get(
            "/api/v1/admin/job-melas/participations",
            headers={"Authorization": f"Bearer {rec_token}"},
        )
        assert resp_rec.status_code == 403


# ── 12. Admin List Company Participations ──────────────────────────────────────

@pytest.mark.asyncio
async def test_admin_list_participations():
    """Admin gets 200 with list of company participations."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "admin1@ntrvikasa.com", role="ADMIN")
        resp = await client.get(
            "/api/v1/admin/job-melas/participations",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    requests = resp.json()
    assert isinstance(requests, list)
    assert len(requests) > 0

    first = requests[0]
    for key in ("id", "company_name", "companyName", "event_name", "eventName", "status"):
        assert key in first


# ── 13. Admin Approves Participation ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_admin_approves_participation():
    """Admin approves a PENDING participation and allocates a booth."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        rec_token = await _login(client, "recruiter1@ntrvikasa.com", role="RECRUITER")
        admin_token = await _login(client, "admin1@ntrvikasa.com", role="ADMIN")

        # 1. Register for mela-13
        reg_resp = await client.post(
            "/api/v1/recruiter/job-melas/participate",
            json={
                "job_mela_id": "mela-13",
                "title": "Visakhapatnam IT & FinTech Job Fair 2026",
                "openings": "DevOps & Cloud Engineers",
                "target_hires": 15,
            },
            headers={"Authorization": f"Bearer {rec_token}"},
        )
        assert reg_resp.status_code == 201
        part_id = reg_resp.json()["id"]

        # 2. Admin approves it
        resp_approve = await client.patch(
            f"/api/v1/admin/job-melas/participations/{part_id}/approve",
            json={
                "booth_number": "Booth VIP-01 (Tech Pavilion)",
                "booth_location": "Main Hall, Tech Pavilion",
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp_approve.status_code == 200
        data = resp_approve.json()
        assert data["status"] == "APPROVED"
        assert "Booth VIP-01" in data["booth_number"]

        # 3. Recruiter now sees it as APPROVED
        resp_rec = await client.get(
            "/api/v1/recruiter/job-melas?status=APPROVED",
            headers={"Authorization": f"Bearer {rec_token}"},
        )
        assert resp_rec.status_code == 200
        approved_melas = resp_rec.json()
        mela_13 = next((m for m in approved_melas if m["id"] == "mela-13"), None)
        assert mela_13 is not None
        assert mela_13["participation_status"] == "APPROVED"
        assert "Booth VIP-01" in mela_13["boothNumber"]


# ── 14. Admin Rejects Participation ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_admin_rejects_participation():
    """Admin rejects a participation with mandatory reason."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        rec_token = await _login(client, "recruiter1@ntrvikasa.com", role="RECRUITER")
        admin_token = await _login(client, "admin1@ntrvikasa.com", role="ADMIN")

        # 1. Register for mela-14
        reg_resp = await client.post(
            "/api/v1/recruiter/job-melas/participate",
            json={
                "job_mela_id": "mela-14",
                "title": "Tirupati Rayalaseema Mega Employment Drive",
                "openings": "Testing Roles",
                "target_hires": 5,
            },
            headers={"Authorization": f"Bearer {rec_token}"},
        )
        assert reg_resp.status_code == 201
        part_id = reg_resp.json()["id"]

        # 2. Admin rejects
        reject_resp = await client.patch(
            f"/api/v1/admin/job-melas/participations/{part_id}/reject",
            json={"rejection_reason": "Stalls fully booked for software category"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert reject_resp.status_code == 200
        assert reject_resp.json()["status"] == "REJECTED"


# ── 15. Candidate Job Mela Experience: Approved Companies Visible ──────────────

@pytest.mark.asyncio
async def test_candidate_mela_approved_companies():
    """Approved participating companies are available in the public/candidate mela experience."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        rec_token = await _login(client, "recruiter1@ntrvikasa.com", role="RECRUITER")
        admin_token = await _login(client, "admin1@ntrvikasa.com", role="ADMIN")

        # 1. Register for mela-15
        reg_resp = await client.post(
            "/api/v1/recruiter/job-melas/participate",
            json={
                "job_mela_id": "mela-15",
                "title": "Guntur & Amaravati Skills & Tech Expo",
                "openings": "Fullstack React & Python Developers",
                "target_hires": 30,
            },
            headers={"Authorization": f"Bearer {rec_token}"},
        )
        assert reg_resp.status_code == 201
        part_id = reg_resp.json()["id"]

        # 2. Approve it
        await client.patch(
            f"/api/v1/admin/job-melas/participations/{part_id}/approve",
            json={"booth_number": "Booth G-10 (Amaravati Pavilion)"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        # 3. Candidate queries approved companies for mela-15
        resp = await client.get("/api/v1/job-melas/mela-15/companies")
        assert resp.status_code == 200
        companies = resp.json()
        assert len(companies) >= 1
        abc = next((c for c in companies if "ABC Technologies" in c["company_name"]), None)
        assert abc is not None
        assert abc["status"] == "APPROVED"
        assert "Booth G-10" in abc["booth_number"]


# ── 16. Recruiter Data Isolation ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_recruiter_data_isolation():
    """Recruiter 2 does not share Recruiter 1's participation status."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token2 = await _login(client, "recruiter2@ntrvikasa.com", role="RECRUITER")
        resp = await client.get(
            "/api/v1/recruiter/job-melas",
            headers={"Authorization": f"Bearer {token2}"},
        )
        assert resp.status_code == 200
        events = resp.json()
        # Recruiter 2 has not registered for any events yet
        for ev in events:
            assert ev["participation_status"] == "NOT_REGISTERED"
            assert ev["status"] == "NOT_REGISTERED"


# ── 17. OpenAPI Schema Verification ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_job_melas_in_openapi():
    """OpenAPI schema documents all recruiter, admin, and public job mela endpoints."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/openapi.json")
    assert resp.status_code == 200
    schema = resp.json()
    paths = schema["paths"]

    assert "/api/v1/recruiter/job-melas" in paths
    assert "/api/v1/recruiter/job-melas/participate" in paths
    assert "/api/v1/recruiter/job-melas/available" in paths
    assert "/api/v1/admin/job-melas/participations" in paths
    assert "/api/v1/admin/job-melas/participations/{participation_id}/approve" in paths
    assert "/api/v1/admin/job-melas/participations/{participation_id}/reject" in paths
    assert "/api/v1/job-melas/{job_mela_id}/companies" in paths
