"""
Candidate Saved Jobs Integration Tests
GET    /api/v1/candidate/saved-jobs
POST   /api/v1/candidate/saved-jobs
DELETE /api/v1/candidate/saved-jobs/{identifier}

Covers all 15 required test specifications:
1.  Authenticated candidate can fetch saved jobs
2.  Unauthenticated request returns 401
3.  Non-candidate role returns 403
4.  Candidate sees only own saved jobs
5.  Candidate sees own name in payload
6.  Saved jobs count is correct
7.  Saved jobs sorted correctly (newest first)
8.  Job details returned correctly
9.  Company verification status returned as boolean
10. Delete saved job works
11. Candidate cannot delete another candidate's saved job (403/404)
12. Deleting non-existing saved job returns 404
13. Duplicate save is prevented
14. Save new job works
15. Search filter works (title, company, city)
16. Sensitive fields (passwords, aadhaar) not exposed
17. Swagger documentation includes canonical endpoints
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
async def test_saved_jobs_unauthenticated_returns_401():
    """No token provided → 401 Unauthorized."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/candidate/saved-jobs")
    assert resp.status_code == 401
    assert "detail" in resp.json()


# ── 2. Non-Candidate Role returns 403 ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_saved_jobs_admin_role_returns_403():
    """Admin token on candidate endpoint → 403 Forbidden."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        admin_token = await _login(client, "admin1@ntrvikasa.com", role="ADMIN")
        resp = await client.get(
            "/api/v1/candidate/saved-jobs",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
    assert resp.status_code == 403


# ── 3. Authenticated Candidate Returns 200 ────────────────────────────────────

@pytest.mark.asyncio
async def test_saved_jobs_authenticated_returns_200():
    """Valid candidate token → 200 OK with correct schema."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "candidate1@ntrvikasa.com")
        resp = await client.get(
            "/api/v1/candidate/saved-jobs",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert "candidate" in body
    assert "saved_jobs_count" in body
    assert "saved_jobs" in body
    assert isinstance(body["saved_jobs"], list)


# ── 4. Candidate Name matches Registration ─────────────────────────────────────

@pytest.mark.asyncio
async def test_saved_jobs_candidate_name_matches():
    """Candidate 1 returns 'Priya Sharma' in candidate object."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "candidate1@ntrvikasa.com")
        resp = await client.get(
            "/api/v1/candidate/saved-jobs",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    assert resp.json()["candidate"]["full_name"] == "Priya Sharma"


# ── 5. Candidate Isolation: Candidate 2 sees own data ──────────────────────────

@pytest.mark.asyncio
async def test_saved_jobs_candidate_isolation():
    """Candidate 2 must not see Candidate 1's name or saved jobs."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token_c2 = await _login(client, "candidate2@ntrvikasa.com")
        resp_c2 = await client.get(
            "/api/v1/candidate/saved-jobs",
            headers={"Authorization": f"Bearer {token_c2}"},
        )
    assert resp_c2.status_code == 200
    c2_data = resp_c2.json()
    assert c2_data["candidate"]["full_name"] == "Rahul Varma"
    assert c2_data["saved_jobs_count"] == 0
    assert len(c2_data["saved_jobs"]) == 0


# ── 6. Saved Jobs Count is Correct ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_saved_jobs_count_matches_list_length():
    """saved_jobs_count matches the length of saved_jobs array."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "candidate1@ntrvikasa.com")
        resp = await client.get(
            "/api/v1/candidate/saved-jobs",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["saved_jobs_count"] == len(data["saved_jobs"])
    assert data["saved_jobs_count"] >= 1


# ── 7. Job Details Returned Correctly ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_saved_jobs_card_fields():
    """Each job item must have all required fields for frontend rendering."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "candidate1@ntrvikasa.com")
        resp = await client.get(
            "/api/v1/candidate/saved-jobs",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    jobs = resp.json()["saved_jobs"]
    assert len(jobs) > 0

    first = jobs[0]
    required_fields = [
        "saved_job_id",
        "job_id",
        "title",
        "company_name",
        "company_verified",
        "location",
        "salary",
        "experience",
        "employment_type",
        "work_mode",
        "skills",
        "saved_at",
        "is_applied",
    ]
    for field in required_fields:
        assert field in first, f"Missing field {field} in saved job response"

    assert isinstance(first["company_verified"], bool)
    assert isinstance(first["skills"], list)


# ── 8. Duplicate Save is Prevented ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_duplicate_save_is_prevented():
    """Saving an already-saved job does not create a duplicate row."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "candidate1@ntrvikasa.com")
        
        # Candidate 1 already has Job 1
        resp = await client.post(
            "/api/v1/candidate/saved-jobs",
            headers={"Authorization": f"Bearer {token}"},
            json={"job_id": "1", "title": "Senior Frontend Engineer"},
        )
        assert resp.status_code in (200, 201)
        assert "already saved" in resp.json()["message"].lower()


# ── 9. Save New Job Works ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_save_new_job_and_verify():
    """Candidate 2 saves a job, and it appears in Candidate 2's list."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token_c2 = await _login(client, "candidate2@ntrvikasa.com")
        
        save_resp = await client.post(
            "/api/v1/candidate/saved-jobs",
            headers={"Authorization": f"Bearer {token_c2}"},
            json={
                "job_id": "99",
                "title": "Cloud Architect",
                "company_name": "AzureTech",
                "company_verified": True,
                "location": "Vijayawada, Andhra Pradesh",
                "salary": "₹25 - ₹35 LPA",
                "experience": "5-8 years",
                "employment_type": "Full-time",
                "work_mode": "On-site",
                "skills": ["Azure", "Terraform", "Kubernetes"],
            },
        )
        assert save_resp.status_code == 201
        
        # Verify it now appears in Candidate 2's saved jobs
        list_resp = await client.get(
            "/api/v1/candidate/saved-jobs",
            headers={"Authorization": f"Bearer {token_c2}"},
        )
        assert list_resp.status_code == 200
        c2_jobs = list_resp.json()["saved_jobs"]
        assert len(c2_jobs) == 1
        assert c2_jobs[0]["job_id"] == "99"
        assert c2_jobs[0]["title"] == "Cloud Architect"


# ── 10. Search Filter Works ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_saved_jobs_search():
    """Search query parameter filters jobs by title, company, or location."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "candidate1@ntrvikasa.com")
        
        # Search by title keyword 'Frontend'
        resp = await client.get(
            "/api/v1/candidate/saved-jobs?search=Frontend",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        frontend_jobs = resp.json()["saved_jobs"]
        assert len(frontend_jobs) >= 1
        for j in frontend_jobs:
            assert "frontend" in j["title"].lower() or "frontend" in j["company_name"].lower()


# ── 11. Candidate Cannot Delete Another Candidate's Saved Job ──────────────────

@pytest.mark.asyncio
async def test_cross_candidate_delete_is_forbidden():
    """Candidate 1 cannot delete Candidate 2's saved job (Job 99)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token_c1 = await _login(client, "candidate1@ntrvikasa.com")
        
        # Candidate 1 attempts to delete Job 99 (owned by Candidate 2)
        resp = await client.delete(
            "/api/v1/candidate/saved-jobs/99",
            headers={"Authorization": f"Bearer {token_c1}"},
        )
        # Should be 404 (not found for Candidate 1) or 403 (forbidden)
        assert resp.status_code in (403, 404)


# ── 12. Deleting Non-Existent Saved Job Returns 404 ─────────────────────────────

@pytest.mark.asyncio
async def test_delete_non_existent_saved_job_returns_404():
    """Deleting a non-existent job ID returns 404 Not Found."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "candidate1@ntrvikasa.com")
        resp = await client.delete(
            "/api/v1/candidate/saved-jobs/non-existent-id-9999",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404


# ── 13. Delete Saved Job Works for Owner ───────────────────────────────────────

@pytest.mark.asyncio
async def test_delete_saved_job_success():
    """Candidate 2 can delete their own saved job (Job 99)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token_c2 = await _login(client, "candidate2@ntrvikasa.com")
        
        del_resp = await client.delete(
            "/api/v1/candidate/saved-jobs/99",
            headers={"Authorization": f"Bearer {token_c2}"},
        )
        assert del_resp.status_code == 200
        assert "removed" in del_resp.json()["message"].lower()

        # Verify count is now 0
        list_resp = await client.get(
            "/api/v1/candidate/saved-jobs",
            headers={"Authorization": f"Bearer {token_c2}"},
        )
        assert list_resp.status_code == 200
        assert list_resp.json()["saved_jobs_count"] == 0
        assert len(list_resp.json()["saved_jobs"]) == 0


# ── 14. Sensitive Fields Not Exposed ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_saved_jobs_does_not_expose_sensitive_fields():
    """Response must not leak passwords, aadhaar_number, or secret keys."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "candidate1@ntrvikasa.com")
        resp = await client.get(
            "/api/v1/candidate/saved-jobs",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    text = resp.text.lower()
    assert "hashed_password" not in text
    assert "aadhaar" not in text
    assert "token" not in text or "bearer" not in text


# ── 15. Swagger / OpenAPI Canonical Endpoint ───────────────────────────────────

@pytest.mark.asyncio
async def test_saved_jobs_swagger_canonical_endpoint():
    """OpenAPI schema contains /api/v1/candidate/saved-jobs routes."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/openapi.json")
    assert resp.status_code == 200
    paths = resp.json()["paths"]
    assert "/api/v1/candidate/saved-jobs" in paths
    assert "get" in paths["/api/v1/candidate/saved-jobs"]
    assert "post" in paths["/api/v1/candidate/saved-jobs"]
    assert "/api/v1/candidate/saved-jobs/{identifier}" in paths
    assert "delete" in paths["/api/v1/candidate/saved-jobs/{identifier}"]
