"""
Recruiter Internships Integration & Governance Tests

Endpoints covered:
- GET  /api/v1/recruiters/internships (and /recruiter/internships)
- POST /api/v1/recruiters/internships
- POST /api/v1/recruiters/internships/draft
- POST /api/v1/recruiters/internships/{id}/close
- GET  /api/v1/admin/internships
- GET  /api/v1/admin/internships/{id}
- POST /api/v1/admin/internships/{id}/approve
- POST /api/v1/admin/internships/{id}/reject
- GET  /api/v1/internships (Candidate public view)
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text
from app.main import app
from app.database.session import AsyncSessionLocal


# ── Cleanup Fixture ────────────────────────────────────────────────────────────

@pytest_asyncio.fixture(autouse=True)
async def cleanup_test_internships():
    """Clean up test-created internships (INT-0004 and above) before and after each test."""
    async with AsyncSessionLocal() as session:
        await session.execute(
            text("DELETE FROM audit_logs WHERE entity = 'internship' AND entity_id IN (SELECT id FROM internships WHERE internship_number >= 'INT-0004')")
        )
        await session.execute(
            text("DELETE FROM internship_applications WHERE internship_id IN (SELECT id FROM internships WHERE internship_number >= 'INT-0004')")
        )
        await session.execute(
            text("DELETE FROM internships WHERE internship_number >= 'INT-0004'")
        )
        await session.commit()
    yield
    async with AsyncSessionLocal() as session:
        await session.execute(
            text("DELETE FROM audit_logs WHERE entity = 'internship' AND entity_id IN (SELECT id FROM internships WHERE internship_number >= 'INT-0004')")
        )
        await session.execute(
            text("DELETE FROM internship_applications WHERE internship_id IN (SELECT id FROM internships WHERE internship_number >= 'INT-0004')")
        )
        await session.execute(
            text("DELETE FROM internships WHERE internship_number >= 'INT-0004'")
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
async def test_recruiter_internships_unauthenticated_returns_401():
    """No token -> 401 Unauthorized."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/recruiters/internships")
    assert resp.status_code == 401


# ── 2. Candidate Role Forbidden ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_recruiter_internships_candidate_forbidden_returns_403():
    """Candidate JWT must not access recruiter internships."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "candidate1@ntrvikasa.com", role="CANDIDATE")
        resp = await client.get(
            "/api/v1/recruiters/internships",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 403


# ── 3. Admin Role Forbidden for Recruiter Route ────────────────────────────────

@pytest.mark.asyncio
async def test_recruiter_internships_admin_forbidden_returns_403():
    """Admin JWT must not access recruiter-specific list without recruiter role."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "admin1@ntrvikasa.com", role="ADMIN")
        resp = await client.get(
            "/api/v1/recruiters/internships",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 403


# ── 4. Recruiter Lists Internships (with applicant counts) ─────────────────────

@pytest.mark.asyncio
async def test_recruiter_internships_returns_200_with_items_and_counts():
    """Authenticated recruiter gets 200 with paginated list and exact applicant counts."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "recruiter1@ntrvikasa.com", role="RECRUITER")
        resp = await client.get(
            "/api/v1/recruiters/internships",
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
    assert len(items) >= 3

    # Check for seeded internships
    numbers = {item["internship_number"]: item for item in items}
    assert "INT-0001" in numbers
    assert "INT-0002" in numbers
    assert "INT-0003" in numbers

    # Verify applicant counts from DB
    assert numbers["INT-0001"]["candidate_count"] == 42
    assert numbers["INT-0002"]["candidate_count"] == 28
    assert numbers["INT-0003"]["candidate_count"] == 19


# ── 5. Status Tab Filtering ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_recruiter_internships_status_tab_filtering():
    """Tab filtering correctly maps to backend status values."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "recruiter1@ntrvikasa.com", role="RECRUITER")

        # Active / Published
        resp_pub = await client.get(
            "/api/v1/recruiters/internships?status=PUBLISHED",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp_pub.status_code == 200
        for item in resp_pub.json()["items"]:
            assert item["status"] == "PUBLISHED"

        # Pending Approval
        resp_pend = await client.get(
            "/api/v1/recruiters/internships?status=PENDING",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp_pend.status_code == 200
        for item in resp_pend.json()["items"]:
            assert item["status"] == "PENDING"


# ── 6. Search Query Filtering ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_recruiter_internships_search_filtering():
    """Search matches title, internship number, or work mode."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "recruiter1@ntrvikasa.com", role="RECRUITER")

        resp = await client.get(
            "/api/v1/recruiters/internships?search=React",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) >= 1
        assert "React" in items[0]["title"]


# ── 7. Recruiter Creates Internship -> Starts in PENDING ───────────────────────

@pytest.mark.asyncio
async def test_recruiter_creates_internship_starts_in_pending():
    """Submitting new internship creates sequential number INT-0004 and status PENDING."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "recruiter1@ntrvikasa.com", role="RECRUITER")

        payload = {
            "title": "AI & Data Science Engineering Intern",
            "stipend_monthly": 28000,
            "duration": "6 Months",
            "work_mode": "REMOTE",
            "number_of_interns": 2,
            "description": "Train and fine-tune transformer models and build automated Python evaluation pipelines.",
        }

        resp = await client.post(
            "/api/v1/recruiters/internships",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201
        created = resp.json()

        assert created["title"] == payload["title"]
        assert created["status"] == "PENDING"
        assert created["internship_number"].startswith("INT-")
        assert created["stipend_monthly"] == 28000
        assert created["number_of_interns"] == 2

        # Verify it now appears under pending filter
        resp_pending = await client.get(
            "/api/v1/recruiters/internships?status=PENDING",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp_pending.status_code == 200
        pending_ids = [i["id"] for i in resp_pending.json()["items"]]
        assert created["id"] in pending_ids


# ── 8. Recruiter Saves Draft ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_recruiter_saves_draft():
    """Draft endpoint sets status strictly to DRAFT."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "recruiter1@ntrvikasa.com", role="RECRUITER")

        payload = {
            "title": "Draft QA Intern",
            "stipend_monthly": 15000,
            "duration": "3 Months",
            "work_mode": "HYBRID",
            "number_of_interns": 1,
            "description": "Testing mobile apps.",
        }

        resp = await client.post(
            "/api/v1/recruiters/internships/draft",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201
        draft = resp.json()
        assert draft["status"] == "DRAFT"


# ── 9. Recruiter Closes Internship ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_recruiter_closes_internship():
    """Recruiter can close an active internship."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "recruiter1@ntrvikasa.com", role="RECRUITER")

        # Create one first
        create_resp = await client.post(
            "/api/v1/recruiters/internships",
            json={
                "title": "Temporary Marketing Intern",
                "stipend_monthly": 12000,
                "duration": "2 Months",
                "work_mode": "ONSITE",
                "number_of_interns": 1,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        int_id = create_resp.json()["id"]

        # Close it
        close_resp = await client.post(
            f"/api/v1/recruiters/internships/{int_id}/close",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert close_resp.status_code == 200
        closed_data = close_resp.json()
        assert closed_data["status"] == "CLOSED"
        assert closed_data["closed_at"] is not None


# ── 10. Admin Governance: List, Detail, Approve, Reject ────────────────────────

@pytest.mark.asyncio
async def test_admin_internship_approval_flow():
    """Admin can view details, approve pending internship, or reject with reason."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        recruiter_token = await _login(client, "recruiter1@ntrvikasa.com", role="RECRUITER")
        admin_token = await _login(client, "admin1@ntrvikasa.com", role="ADMIN")

        # 1. Recruiter creates internship
        create_resp = await client.post(
            "/api/v1/recruiters/internships",
            json={
                "title": "Machine Learning Research Intern",
                "stipend_monthly": 35000,
                "duration": "6 Months",
                "work_mode": "HYBRID",
                "number_of_interns": 3,
                "description": "Deep learning research and model quantization.",
            },
            headers={"Authorization": f"Bearer {recruiter_token}"},
        )
        assert create_resp.status_code == 201
        int_id = create_resp.json()["id"]

        # 2. Admin views pending list
        admin_list = await client.get(
            "/api/v1/admin/internships?status=PENDING",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert admin_list.status_code == 200
        assert any(item["id"] == int_id for item in admin_list.json()["items"])

        # 3. Admin views detail
        admin_detail = await client.get(
            f"/api/v1/admin/internships/{int_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert admin_detail.status_code == 200
        detail = admin_detail.json()
        assert detail["id"] == int_id
        assert detail["title"] == "Machine Learning Research Intern"
        assert "company" in detail
        assert "recruiter" in detail

        # 4. Admin approves
        approve_resp = await client.post(
            f"/api/v1/admin/internships/{int_id}/approve",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert approve_resp.status_code == 200
        approved = approve_resp.json()
        assert approved["status"] == "PUBLISHED"
        assert approved["published_at"] is not None

        # 5. Test rejection on a second internship
        create_resp2 = await client.post(
            "/api/v1/recruiters/internships",
            json={
                "title": "Incomplete Internship Posting",
                "stipend_monthly": 5000,
                "duration": "1 Month",
            },
            headers={"Authorization": f"Bearer {recruiter_token}"},
        )
        int_id2 = create_resp2.json()["id"]

        reject_resp = await client.post(
            f"/api/v1/admin/internships/{int_id2}/reject",
            json={"reason": "Stipend too low and missing mandatory details."},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert reject_resp.status_code == 200
        rejected = reject_resp.json()
        assert rejected["status"] == "REJECTED"
        assert rejected["rejection_reason"] == "Stipend too low and missing mandatory details."


# ── 11. Candidate Public View: Only PUBLISHED Internships ─────────────────────

@pytest.mark.asyncio
async def test_candidate_public_api_only_returns_published():
    """Candidate endpoint /api/v1/internships strictly returns PUBLISHED internships."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/internships")
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) >= 2
        for item in items:
            assert item["status"] == "PUBLISHED"
            # Ensure no PENDING or REJECTED or DRAFT
            assert item["status"] not in ("PENDING", "DRAFT", "REJECTED")


# ── 12. Recruiter Multi-Tenant Isolation ──────────────────────────────────────

@pytest.mark.asyncio
async def test_recruiter_multi_tenant_isolation():
    """Recruiter 2 does not see Recruiter 1's pending or draft internships."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token1 = await _login(client, "recruiter1@ntrvikasa.com", role="RECRUITER")
        token2 = await _login(client, "recruiter2@ntrvikasa.com", role="RECRUITER")

        # Recruiter 1 creates an internship
        resp1 = await client.post(
            "/api/v1/recruiters/internships",
            json={
                "title": "Recruiter1 Secret Intern",
                "stipend_monthly": 20000,
                "duration": "3 Months",
            },
            headers={"Authorization": f"Bearer {token1}"},
        )
        created_id = resp1.json()["id"]

        # Recruiter 2 lists their internships
        resp2 = await client.get(
            "/api/v1/recruiters/internships",
            headers={"Authorization": f"Bearer {token2}"},
        )
        assert resp2.status_code == 200
        r2_ids = [item["id"] for item in resp2.json()["items"]]
        assert created_id not in r2_ids
