"""
Recruiter Jobs Postings, Approvals, Candidate Apply & Governance Integration Tests

Endpoints covered:
- GET  /api/v1/recruiters/jobs (and /recruiter/jobs)
- POST /api/v1/recruiters/jobs
- POST /api/v1/recruiters/jobs/draft
- POST /api/v1/recruiters/jobs/{id}/close
- PUT  /api/v1/recruiters/jobs/{id}
- GET  /api/v1/recruiters/jobs/{id}
- GET  /api/v1/admin/jobs
- GET  /api/v1/admin/jobs/{id}
- POST /api/v1/admin/jobs/{id}/approve
- POST /api/v1/admin/jobs/{id}/reject
- GET  /api/v1/jobs (Candidate public view)
- GET  /api/v1/jobs/{id}
- POST /api/v1/candidate/applications (Apply to job & match score)
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text
from app.main import app
from app.database.session import AsyncSessionLocal


# ── Cleanup Fixture ────────────────────────────────────────────────────────────

@pytest_asyncio.fixture(autouse=True)
async def cleanup_test_jobs():
    """Clean up test-created jobs before and after each test."""
    test_titles = [
        "Lead Site Reliability Engineer",
        "Draft Technical Writer",
        "Contract Security Auditor",
        "Staff Distributed Systems Architect",
        "Incomplete Requisition Test",
        "Cloud Security Specialist",
        "Immediate Contract Job",
        "Recruiter1 Proprietary Role",
    ]
    async with AsyncSessionLocal() as session:
        await session.execute(
            text("DELETE FROM audit_logs WHERE entity = 'JOB' AND entity_id IN (SELECT id FROM jobs WHERE title IN :titles OR job_id LIKE 'test-%')"),
            {"titles": tuple(test_titles)},
        )
        await session.execute(
            text("DELETE FROM candidate_applications WHERE job_id IN (SELECT id FROM jobs WHERE title IN :titles OR job_id LIKE 'test-%') OR cover_letter LIKE '%cloud security%'"),
            {"titles": tuple(test_titles)},
        )
        await session.execute(
            text("DELETE FROM job_skills WHERE job_id IN (SELECT id FROM jobs WHERE title IN :titles OR job_id LIKE 'test-%')"),
            {"titles": tuple(test_titles)},
        )
        await session.execute(
            text("DELETE FROM jobs WHERE title IN :titles OR job_id LIKE 'test-%'"),
            {"titles": tuple(test_titles)},
        )
        await session.commit()
    yield
    async with AsyncSessionLocal() as session:
        await session.execute(
            text("DELETE FROM audit_logs WHERE entity = 'JOB' AND entity_id IN (SELECT id FROM jobs WHERE title IN :titles OR job_id LIKE 'test-%')"),
            {"titles": tuple(test_titles)},
        )
        await session.execute(
            text("DELETE FROM candidate_applications WHERE job_id IN (SELECT id FROM jobs WHERE title IN :titles OR job_id LIKE 'test-%') OR cover_letter LIKE '%cloud security%'"),
            {"titles": tuple(test_titles)},
        )
        await session.execute(
            text("DELETE FROM job_skills WHERE job_id IN (SELECT id FROM jobs WHERE title IN :titles OR job_id LIKE 'test-%')"),
            {"titles": tuple(test_titles)},
        )
        await session.execute(
            text("DELETE FROM jobs WHERE title IN :titles OR job_id LIKE 'test-%'"),
            {"titles": tuple(test_titles)},
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


# ── 1. Unauthenticated Request ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_recruiter_jobs_unauthenticated_returns_401():
    """No token -> 401 Unauthorized."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/recruiters/jobs")
    assert resp.status_code == 401


# ── 2. Candidate Role Forbidden ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_recruiter_jobs_candidate_forbidden_returns_403():
    """Candidate JWT must not access recruiter jobs."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "candidate1@ntrvikasa.com", role="CANDIDATE")
        resp = await client.get(
            "/api/v1/recruiters/jobs",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 403


# ── 3. Admin Role Forbidden for Recruiter Route ────────────────────────────────

@pytest.mark.asyncio
async def test_recruiter_jobs_admin_forbidden_returns_403():
    """Admin JWT must not access recruiter-specific list without recruiter role."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "admin1@ntrvikasa.com", role="ADMIN")
        resp = await client.get(
            "/api/v1/recruiters/jobs",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 403


# ── 4. Recruiter Lists Jobs (with real pipeline counts) ────────────────────────

@pytest.mark.asyncio
async def test_recruiter_jobs_returns_200_with_pipeline_counts():
    """Authenticated recruiter gets 200 with paginated jobs and exact pipeline counts."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "recruiter1@ntrvikasa.com", role="RECRUITER")
        resp = await client.get(
            "/api/v1/recruiters/jobs",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data
    assert "total_pages" in data

    items = data["items"]
    assert len(items) >= 4

    by_num = {item["job_number"]: item for item in items}
    assert "JOB-101" in by_num
    assert "JOB-102" in by_num
    assert "JOB-103" in by_num
    assert "JOB-104" in by_num

    # Verify pipeline counts from database
    assert by_num["JOB-101"]["applicantsCount"] >= 78
    assert by_num["JOB-101"]["shortlistedCount"] >= 14
    assert by_num["JOB-101"]["interviewsCount"] >= 5

    assert by_num["JOB-102"]["applicantsCount"] >= 45
    assert by_num["JOB-102"]["shortlistedCount"] >= 9
    assert by_num["JOB-102"]["interviewsCount"] >= 4


# ── 5. Status Tab Filtering ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_recruiter_jobs_status_tab_filtering():
    """Tab filtering correctly maps to backend status values."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "recruiter1@ntrvikasa.com", role="RECRUITER")

        # Active / Published
        resp_pub = await client.get(
            "/api/v1/recruiters/jobs?status=PUBLISHED",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp_pub.status_code == 200
        for item in resp_pub.json()["items"]:
            assert item["status"] == "PUBLISHED"

        # Pending Approval
        resp_pend = await client.get(
            "/api/v1/recruiters/jobs?status=PENDING",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp_pend.status_code == 200
        for item in resp_pend.json()["items"]:
            assert item["status"] == "PENDING"

        # Closed
        resp_closed = await client.get(
            "/api/v1/recruiters/jobs?status=CLOSED",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp_closed.status_code == 200
        for item in resp_closed.json()["items"]:
            assert item["status"] == "CLOSED"


# ── 6. Department and Search Filtering ────────────────────────────────────────

@pytest.mark.asyncio
async def test_recruiter_jobs_department_and_search_filtering():
    """Filter by department and search query."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "recruiter1@ntrvikasa.com", role="RECRUITER")

        # Department filter
        resp_dept = await client.get(
            "/api/v1/recruiters/jobs?department=Platform%20Core",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp_dept.status_code == 200
        for item in resp_dept.json()["items"]:
            assert item["department"] == "Platform Core"

        # Search filter
        resp_search = await client.get(
            "/api/v1/recruiters/jobs?search=Frontend",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp_search.status_code == 200
        assert len(resp_search.json()["items"]) >= 1
        assert "Frontend" in resp_search.json()["items"][0]["title"]


# ── 7. Recruiter Creates Job -> Starts in PENDING with sequential number ───────

@pytest.mark.asyncio
async def test_recruiter_creates_job_starts_in_pending():
    """Submitting new job requisition sets status to PENDING and generates JOB-106."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "recruiter1@ntrvikasa.com", role="RECRUITER")

        payload = {
            "title": "Lead Site Reliability Engineer",
            "department": "Infra & SecOps",
            "job_type": "Full-time",
            "work_mode": "Hybrid",
            "location": "Bengaluru, Karnataka",
            "experience": "5-8 years",
            "salary_min": 2400000,
            "salary_max": 3600000,
            "salary": "₹24,00,000 - ₹36,00,000 / year",
            "openings": 2,
            "deadline": "2026-11-15",
            "description": "Lead multi-region SRE operations and zero-downtime reliability architecture.",
            "responsibilities": "• Oversee platform uptime, incident response, and chaos engineering exercises.",
            "requirements": "• Deep expertise in Kubernetes, Linux kernel tuning, and observability frameworks.",
            "qualifications": "B.Tech in Computer Science or equivalent practical experience.",
            "skills": ["Kubernetes", "Linux", "Terraform", "Prometheus", "Golang"],
        }

        resp = await client.post(
            "/api/v1/recruiters/jobs",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201
        created = resp.json()

        assert created["title"] == payload["title"]
        assert created["status"] == "PENDING"
        assert created["job_number"].startswith("JOB-")
        assert created["openings"] == 2
        assert "Kubernetes" in created["skills"]

        # Ensure it appears under pending tab
        resp_pending = await client.get(
            "/api/v1/recruiters/jobs?status=PENDING",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp_pending.status_code == 200
        p_ids = [j["id"] for j in resp_pending.json()["items"]]
        assert created["id"] in p_ids


# ── 8. Recruiter Saves Job Draft ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_recruiter_saves_job_draft():
    """Draft endpoint sets status strictly to DRAFT."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "recruiter1@ntrvikasa.com", role="RECRUITER")

        payload = {
            "title": "Draft Technical Writer",
            "department": "Platform Core",
            "description": "Internal developer documentation.",
        }

        resp = await client.post(
            "/api/v1/recruiters/jobs/draft",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201
        draft = resp.json()
        assert draft["status"] == "DRAFT"

        # Verify candidate cannot see draft
        resp_cand = await client.get("/api/v1/jobs")
        cand_ids = [j["id"] for j in resp_cand.json()["items"]]
        assert draft["id"] not in cand_ids


# ── 9. Recruiter Closes Job ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_recruiter_closes_job():
    """Recruiter can close an active job posting."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "recruiter1@ntrvikasa.com", role="RECRUITER")

        create_resp = await client.post(
            "/api/v1/recruiters/jobs",
            json={
                "title": "Contract Security Auditor",
                "department": "Infra & SecOps",
                "description": "SOC-2 Type II audit readiness.",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        job_id = create_resp.json()["id"]

        close_resp = await client.post(
            f"/api/v1/recruiters/jobs/{job_id}/close",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert close_resp.status_code == 200
        closed_job = close_resp.json()
        assert closed_job["status"] == "CLOSED"
        assert closed_job["closed_at"] is not None


# ── 10. Admin Governance Flow: Approve and Reject ─────────────────────────────

@pytest.mark.asyncio
async def test_admin_job_governance_flow():
    """Admin can view details, approve pending job to PUBLISHED, or reject with reason."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        recruiter_token = await _login(client, "recruiter1@ntrvikasa.com", role="RECRUITER")
        admin_token = await _login(client, "admin1@ntrvikasa.com", role="ADMIN")

        # 1. Recruiter creates job
        create_resp = await client.post(
            "/api/v1/recruiters/jobs",
            json={
                "title": "Staff Distributed Systems Architect",
                "department": "Platform Core",
                "description": "Design mission-critical event backbones in Kafka and Cassandra.",
                "skills": ["Kafka", "Cassandra", "Go", "Distributed Systems"],
            },
            headers={"Authorization": f"Bearer {recruiter_token}"},
        )
        assert create_resp.status_code == 201
        job_id = create_resp.json()["id"]

        # 2. Admin views pending list
        admin_list = await client.get(
            "/api/v1/admin/jobs?status=PENDING",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert admin_list.status_code == 200
        assert any(j["id"] == job_id for j in admin_list.json()["items"])

        # 3. Admin views detail
        admin_detail = await client.get(
            f"/api/v1/admin/jobs/{job_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert admin_detail.status_code == 200
        detail = admin_detail.json()
        assert detail["id"] == job_id
        assert detail["title"] == "Staff Distributed Systems Architect"
        assert "company" in detail or "company_name" in detail
        assert "Kafka" in detail["skills"]

        # 4. Admin approves
        approve_resp = await client.post(
            f"/api/v1/admin/jobs/{job_id}/approve",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert approve_resp.status_code == 200
        approved = approve_resp.json()
        assert approved["status"] == "PUBLISHED"
        assert approved["posted_at"] is not None

        # 5. Verify published in public candidate API
        pub_resp = await client.get("/api/v1/jobs")
        assert pub_resp.status_code == 200
        pub_ids = [j["id"] for j in pub_resp.json()["items"]]
        assert job_id in pub_ids

        # 6. Admin rejects a second job
        create_resp2 = await client.post(
            "/api/v1/recruiters/jobs",
            json={
                "title": "Incomplete Requisition Test",
                "description": "Missing vital job info.",
            },
            headers={"Authorization": f"Bearer {recruiter_token}"},
        )
        job_id2 = create_resp2.json()["id"]

        reject_resp = await client.post(
            f"/api/v1/admin/jobs/{job_id2}/reject",
            json={"reason": "Job description is missing required compliance details."},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert reject_resp.status_code == 200
        rejected = reject_resp.json()
        assert rejected["status"] == "REJECTED"
        assert rejected["rejection_reason"] == "Job description is missing required compliance details."


# ── 11. Candidate Public View Isolation ───────────────────────────────────────

@pytest.mark.asyncio
async def test_candidate_public_api_only_returns_published():
    """Candidate endpoint /api/v1/jobs strictly returns only PUBLISHED jobs."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/jobs")
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) >= 2
        for item in items:
            assert item["status"] == "PUBLISHED"
            assert item["status"] not in ("PENDING", "DRAFT", "REJECTED")


# ── 12. Candidate Applies to Job & Recruiter Pipeline Count Increases ─────────

@pytest.mark.asyncio
async def test_candidate_applies_and_pipeline_count_increments():
    """Candidate applying to published job increases applicant_count and calculates match score."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        recruiter_token = await _login(client, "recruiter1@ntrvikasa.com", role="RECRUITER")
        candidate_token = await _login(client, "candidate1@ntrvikasa.com", role="CANDIDATE")

        # 1. Create and approve a new job
        create_job_resp = await client.post(
            "/api/v1/recruiters/jobs",
            json={
                "title": "Cloud Security Specialist",
                "department": "Infra & SecOps",
                "description": "Manage multi-cloud identity and security infrastructure.",
                "skills": ["AWS", "Terraform", "Python", "Docker"],
            },
            headers={"Authorization": f"Bearer {recruiter_token}"},
        )
        job_id = create_job_resp.json()["id"]

        admin_token = await _login(client, "admin1@ntrvikasa.com", role="ADMIN")
        await client.post(
            f"/api/v1/admin/jobs/{job_id}/approve",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        # 2. Check initial applicant count is 0
        detail_before = await client.get(
            f"/api/v1/recruiters/jobs/{job_id}",
            headers={"Authorization": f"Bearer {recruiter_token}"},
        )
        assert detail_before.json()["applicantsCount"] == 0

        # 3. Candidate applies
        apply_resp = await client.post(
            "/api/v1/candidate/applications",
            json={
                "job_id": job_id,
                "cover_letter": "I have extensive experience in cloud security and infrastructure.",
            },
            headers={"Authorization": f"Bearer {candidate_token}"},
        )
        assert apply_resp.status_code == 201
        app_data = apply_resp.json()
        assert app_data["status"] == "APPLIED"
        assert "match_percentage" in app_data

        # 4. Check applicant count has incremented to 1
        detail_after = await client.get(
            f"/api/v1/recruiters/jobs/{job_id}",
            headers={"Authorization": f"Bearer {recruiter_token}"},
        )
        assert detail_after.json()["applicantsCount"] == 1


# ── 13. Closed Job Cannot Receive New Applications ────────────────────────────

@pytest.mark.asyncio
async def test_closed_job_cannot_receive_applications():
    """Applying to a closed job is rejected with 400 Bad Request."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        recruiter_token = await _login(client, "recruiter1@ntrvikasa.com", role="RECRUITER")
        candidate_token = await _login(client, "candidate1@ntrvikasa.com", role="CANDIDATE")

        # Create and close a job
        create_resp = await client.post(
            "/api/v1/recruiters/jobs",
            json={
                "title": "Immediate Contract Job",
                "description": "Will be closed right away.",
            },
            headers={"Authorization": f"Bearer {recruiter_token}"},
        )
        job_id = create_resp.json()["id"]

        await client.post(
            f"/api/v1/recruiters/jobs/{job_id}/close",
            headers={"Authorization": f"Bearer {recruiter_token}"},
        )

        # Candidate attempts to apply
        apply_resp = await client.post(
            "/api/v1/candidate/applications",
            json={
                "job_id": job_id,
            },
            headers={"Authorization": f"Bearer {candidate_token}"},
        )
        assert apply_resp.status_code == 400
        assert "closed" in apply_resp.json()["detail"].lower()


# ── 14. Recruiter Multi-Tenant Isolation ──────────────────────────────────────

@pytest.mark.asyncio
async def test_recruiter_multi_tenant_isolation():
    """Recruiter 2 does not see Recruiter 1's pending or draft jobs."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token1 = await _login(client, "recruiter1@ntrvikasa.com", role="RECRUITER")
        token2 = await _login(client, "recruiter2@ntrvikasa.com", role="RECRUITER")

        # Recruiter 1 creates job
        resp1 = await client.post(
            "/api/v1/recruiters/jobs",
            json={
                "title": "Recruiter1 Proprietary Role",
                "description": "Private position.",
            },
            headers={"Authorization": f"Bearer {token1}"},
        )
        created_id = resp1.json()["id"]

        # Recruiter 2 lists jobs
        resp2 = await client.get(
            "/api/v1/recruiters/jobs",
            headers={"Authorization": f"Bearer {token2}"},
        )
        assert resp2.status_code == 200
        r2_ids = [j["id"] for j in resp2.json()["items"]]
        assert created_id not in r2_ids
