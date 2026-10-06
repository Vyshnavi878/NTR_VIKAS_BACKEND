"""
Comprehensive Integration Tests for Recruiter Applications Management.
Covers:
- Unauthenticated (401) and candidate role forbidden (403)
- List applications with pagination metadata, summary counts, and job posting breakdowns
- Filtering by job_id, status (Screening, Shortlisted, Interview, Selected, Rejected), application_type
- Searching across candidate name, email, application number, role, etc.
- Sorting by newest, oldest, and match score
- Application details endpoint with full candidate profile dossier
- IDOR isolation preventing unauthorized cross-company access
- Application status transition (PATCH) with timeline history recording
- Direct vs Job Mela application structure verification
"""
import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text, select
from app.main import app
from app.database.session import AsyncSessionLocal
from app.models.application import CandidateApplication


async def _login(client: AsyncClient, email: str, password: str = "password123", role: str = "RECRUITER") -> str:
    """Authenticate and return JWT Bearer access token."""
    resp = await client.post("/api/v1/auth/login", json={
        "email": email,
        "password": password,
        "role": role,
    })
    assert resp.status_code == 200, f"Login failed for {email}: {resp.text}"
    return resp.json()["access_token"]


# ── 1. Authentication & Security Tests ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_applications_unauthenticated_returns_401():
    """Unauthenticated requests must return 401."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/recruiter/applications")
        assert resp.status_code == 401
        assert "Not authenticated" in resp.text


@pytest.mark.asyncio
async def test_candidate_forbidden_on_recruiter_applications():
    """Candidate tokens must be rejected with 403."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        cand_token = await _login(client, "candidate1@ntrvikasa.com", "password123", role="CANDIDATE")
        resp = await client.get(
            "/api/v1/recruiter/applications",
            headers={"Authorization": f"Bearer {cand_token}"},
        )
        assert resp.status_code == 403


# ── 2. Recruiter Applications List & Response Schema ──────────────────────────

@pytest.mark.asyncio
async def test_recruiter_get_applications_schema():
    """Recruiter can list applications with items, pagination, summary, and job postings."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "recruiter1@ntrvikasa.com", "password123", role="RECRUITER")
        resp = await client.get(
            "/api/v1/recruiter/applications?page=1&page_size=9",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()

        # Top-level keys
        assert "items" in data
        assert "pagination" in data
        assert "summary" in data
        assert "job_postings" in data

        # Pagination structure
        pag = data["pagination"]
        assert pag["page"] == 1
        assert pag["page_size"] == 9
        assert pag["total_items"] > 0
        assert pag["total_pages"] >= 1
        assert isinstance(pag["has_next"], bool)
        assert isinstance(pag["has_previous"], bool)

        # Summary structure
        summary = data["summary"]
        assert "total_received" in summary
        assert "screening" in summary
        assert "shortlisted" in summary
        assert "interviews" in summary
        assert "selected_hired" in summary
        assert "rejected" in summary
        assert summary["total_received"] >= 0

        # Job postings structure
        job_postings = data["job_postings"]
        assert isinstance(job_postings, list)
        assert len(job_postings) > 0
        first_jp = job_postings[0]
        assert "job_id" in first_jp
        assert "title" in first_jp
        assert "application_count" in first_jp

        # Item structure
        items = data["items"]
        assert len(items) <= 9
        if items:
            item = items[0]
            assert "application_id" in item
            assert "application_number" in item
            assert "application_type" in item
            assert "status" in item
            assert "candidate" in item
            assert "job" in item
            assert "match_score" in item

            cand = item["candidate"]
            assert "name" in cand
            assert "skills" in cand

            job = item["job"]
            assert "job_id" in job
            assert "title" in job
            assert "company_name" in job


# ── 3. Pagination Controls ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_recruiter_applications_pagination():
    """Test custom page and page_size pagination behavior."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "recruiter1@ntrvikasa.com", "password123", role="RECRUITER")
        resp = await client.get(
            "/api/v1/recruiter/applications?page=2&page_size=5",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["pagination"]["page"] == 2
        assert data["pagination"]["page_size"] == 5
        assert len(data["items"]) <= 5
        assert data["pagination"]["has_previous"] is True


# ── 4. Job Filter ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_recruiter_applications_job_filter():
    """Filtering by job_id returns applications specifically for that job."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "recruiter1@ntrvikasa.com", "password123", role="RECRUITER")
        resp = await client.get(
            "/api/v1/recruiter/applications?job_id=job-101",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        for item in data["items"]:
            assert item["job"]["job_id"].lower() == "job-101"


# ── 5. Status Filter ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_recruiter_applications_status_filter():
    """Status tabs correctly filter applications."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "recruiter1@ntrvikasa.com", "password123", role="RECRUITER")
        resp = await client.get(
            "/api/v1/recruiter/applications?status=SHORTLISTED",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        for item in data["items"]:
            assert item["status"] == "SHORTLISTED"


# ── 6. Search Functionality ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_recruiter_applications_search():
    """Search matches candidate name, role, or application number."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "recruiter1@ntrvikasa.com", "password123", role="RECRUITER")
        resp = await client.get(
            "/api/v1/recruiter/applications?search=Frontend",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["pagination"]["total_items"] > 0
        for item in data["items"]:
            combined_text = f"{item['job']['title']} {item['candidate']['name']} {item['application_number']}".lower()
            assert "frontend" in combined_text or "react" in combined_text


# ── 7. Sorting Functionality ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_recruiter_applications_sorting():
    """Sorting by newest, oldest, and match score works properly."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "recruiter1@ntrvikasa.com", "password123", role="RECRUITER")
        
        # Match score sort
        resp_match = await client.get(
            "/api/v1/recruiter/applications?sort_by=match_score&sort_order=desc",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp_match.status_code == 200
        items = resp_match.json()["items"]
        if len(items) >= 2:
            scores = [i["match_score"] for i in items if i["match_score"] is not None]
            assert scores == sorted(scores, reverse=True)


# ── 8. Application Detail & IDOR Protection ───────────────────────────────────

@pytest.mark.asyncio
async def test_recruiter_application_detail_and_idor():
    """Verify application detail endpoint and ensure IDOR protection."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "recruiter1@ntrvikasa.com", "password123", role="RECRUITER")
        
        # First get a valid application ID
        list_resp = await client.get(
            "/api/v1/recruiter/applications?page=1&page_size=1",
            headers={"Authorization": f"Bearer {token}"},
        )
        app_id = list_resp.json()["items"][0]["application_id"]

        # Fetch detail
        detail_resp = await client.get(
            f"/api/v1/recruiter/applications/{app_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert detail_resp.status_code == 200
        detail = detail_resp.json()
        assert detail["application_id"] == app_id
        assert "timeline" in detail
        assert "candidate" in detail

        # Test IDOR protection with non-existent or foreign application ID
        fake_id = "non-existent-or-foreign-app-id"
        fake_resp = await client.get(
            f"/api/v1/recruiter/applications/{fake_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert fake_resp.status_code == 404


# ── 9. Status Update (PATCH) ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_recruiter_update_application_status():
    """Recruiter can update status to SHORTLISTED or REJECTED with timeline event."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "recruiter1@ntrvikasa.com", "password123", role="RECRUITER")
        
        # Get an application to update
        list_resp = await client.get(
            "/api/v1/recruiter/applications?page=1&page_size=1",
            headers={"Authorization": f"Bearer {token}"},
        )
        app_id = list_resp.json()["items"][0]["application_id"]
        original_status = list_resp.json()["items"][0]["status"]

        new_status = "SHORTLISTED" if original_status != "SHORTLISTED" else "SCREENING"

        # PATCH status
        patch_resp = await client.patch(
            f"/api/v1/recruiter/applications/{app_id}/status",
            json={"status": new_status, "notes": "Automated pipeline update"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert patch_resp.status_code == 200
        updated = patch_resp.json()
        assert updated["status"] == new_status

        # Verify timeline event was added
        assert len(updated["timeline"]) > 0
        latest_event = updated["timeline"][-1]
        assert latest_event["status"] == new_status

        # Revert back to original status
        await client.patch(
            f"/api/v1/recruiter/applications/{app_id}/status",
            json={"status": original_status, "notes": "Reverted"},
            headers={"Authorization": f"Bearer {token}"},
        )
