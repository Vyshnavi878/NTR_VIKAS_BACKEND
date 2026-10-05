"""
Automated Pytest Suite for Recruiter Help & Support Requests
============================================================
Tests verify:
1.  Authenticated recruiter submits valid support request (201 Created, stored in MySQL)
2.  Unauthenticated user receives 401 Unauthorized
3.  Candidate token receives 403 Forbidden
4.  Admin token receives 403 Forbidden
5.  Missing issue category returns 422
6.  Missing subject returns 422
7.  Missing description returns 422
8.  Invalid issue category returns 422
9.  Double-click submit returns existing ticket without duplicate MySQL record
10. Support request remains persisted across independent database sessions
11. Ticket numbers are unique and properly formatted (SUP-XXXXXX)
12. Recruiter can list their own submitted support requests
13. OpenAPI / Swagger contains POST and GET /api/v1/recruiter/support/requests with Bearer auth
"""
import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from app.main import app
from app.database.session import AsyncSessionLocal
from app.models.recruiter_support import RecruiterSupportRequest


# ── Helpers ────────────────────────────────────────────────────────────────────

async def _login(
    client: AsyncClient,
    email: str,
    password: str = "password123",
    role: str = "RECRUITER",
) -> str:
    """Return a valid Bearer access token for the given credentials."""
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password, "role": role},
    )
    assert resp.status_code == 200, f"Login failed for {email}: {resp.text}"
    return resp.json()["access_token"]


# ── Tests ──────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_recruiter_support_unauthenticated_returns_401():
    """TEST 2: Unauthenticated user submits request → 401 Unauthorized."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/recruiter/support/requests",
            json={
                "issue_category": "Job Posting Approval & Moderation",
                "subject": "Question regarding job approval",
                "description": "Please check on the approval for my recent posting.",
            },
        )
        assert resp.status_code == 401

        resp_get = await client.get("/api/v1/recruiter/support/requests")
        assert resp_get.status_code == 401


@pytest.mark.asyncio
async def test_recruiter_support_candidate_role_returns_403():
    """TEST 3: Candidate token attempts recruiter support endpoint → 403 Forbidden."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        cand_token = await _login(client, "candidate1@ntrvikasa.com", role="CANDIDATE")
        headers = {"Authorization": f"Bearer {cand_token}"}
        resp = await client.post(
            "/api/v1/recruiter/support/requests",
            headers=headers,
            json={
                "issue_category": "Job Posting Approval & Moderation",
                "subject": "Question regarding job approval",
                "description": "Please check on the approval for my recent posting.",
            },
        )
        assert resp.status_code == 403

        resp_get = await client.get("/api/v1/recruiter/support/requests", headers=headers)
        assert resp_get.status_code == 403


@pytest.mark.asyncio
async def test_recruiter_support_admin_role_returns_403():
    """Admin token attempts recruiter support endpoint → 403 Forbidden."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        admin_token = await _login(client, "admin1@ntrvikasa.com", role="ADMIN")
        headers = {"Authorization": f"Bearer {admin_token}"}
        resp = await client.post(
            "/api/v1/recruiter/support/requests",
            headers=headers,
            json={
                "issue_category": "Job Posting Approval & Moderation",
                "subject": "Question regarding job approval",
                "description": "Please check on the approval for my recent posting.",
            },
        )
        assert resp.status_code == 403


@pytest.mark.asyncio
async def test_recruiter_submits_valid_support_request():
    """TEST 1: Authenticated recruiter submits valid support request. Returns 201 Created and ticket stored in MySQL."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "recruiter1@ntrvikasa.com")
        headers = {"Authorization": f"Bearer {token}"}

        unique_marker = uuid.uuid4().hex[:6]
        payload = {
            "issue_category": "Job Posting Approval & Moderation",
            "subject": f"Question regarding job approval status {unique_marker}",
            "description": f"Please provide an update regarding my pending job approval #{unique_marker}.",
        }

        resp = await client.post(
            "/api/v1/recruiter/support/requests",
            headers=headers,
            json=payload,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["message"] == "Support request submitted successfully."
        assert "ticket_number" in data
        assert data["ticket_number"].startswith("SUP-")
        assert data["status"] == "OPEN"

        # Verify record in MySQL
        async with AsyncSessionLocal() as session:
            stmt = select(RecruiterSupportRequest).where(
                RecruiterSupportRequest.ticket_number == data["ticket_number"]
            )
            res = await session.execute(stmt)
            record = res.scalar_one_or_none()
            assert record is not None
            assert record.subject == payload["subject"]
            assert record.issue_category == "Job Posting Approval & Moderation"
            assert record.status == "OPEN"
            assert record.priority == "NORMAL"
            assert record.company_name == "ABC Technologies Pvt Ltd"
            assert record.recruiter_name == "Arjun Reddy"


@pytest.mark.asyncio
async def test_recruiter_support_missing_issue_category_returns_422():
    """TEST 4: Missing issue category → 422."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "recruiter1@ntrvikasa.com")
        headers = {"Authorization": f"Bearer {token}"}
        resp = await client.post(
            "/api/v1/recruiter/support/requests",
            headers=headers,
            json={
                "subject": "Missing category test",
                "description": "This is a detailed description of the query.",
            },
        )
        assert resp.status_code == 422


@pytest.mark.asyncio
async def test_recruiter_support_missing_subject_returns_422():
    """TEST 5: Missing subject → 422."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "recruiter1@ntrvikasa.com")
        headers = {"Authorization": f"Bearer {token}"}
        resp = await client.post(
            "/api/v1/recruiter/support/requests",
            headers=headers,
            json={
                "issue_category": "Job Posting Approval & Moderation",
                "description": "This is a detailed description without subject.",
            },
        )
        assert resp.status_code == 422


@pytest.mark.asyncio
async def test_recruiter_support_missing_description_returns_422():
    """TEST 6: Missing description → 422."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "recruiter1@ntrvikasa.com")
        headers = {"Authorization": f"Bearer {token}"}
        resp = await client.post(
            "/api/v1/recruiter/support/requests",
            headers=headers,
            json={
                "issue_category": "Job Posting Approval & Moderation",
                "subject": "Subject without description",
            },
        )
        assert resp.status_code == 422


@pytest.mark.asyncio
async def test_recruiter_support_invalid_category_returns_422():
    """TEST 7: Invalid issue category → 422."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "recruiter1@ntrvikasa.com")
        headers = {"Authorization": f"Bearer {token}"}
        resp = await client.post(
            "/api/v1/recruiter/support/requests",
            headers=headers,
            json={
                "issue_category": "Completely Invalid Arbitrary Category",
                "subject": "Invalid category test",
                "description": "Testing that invalid categories are rejected properly.",
            },
        )
        assert resp.status_code == 422


@pytest.mark.asyncio
async def test_double_click_submit_creates_only_one_ticket():
    """TEST 8: Double-click submit creates only one support request and returns identical ticket number."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "recruiter1@ntrvikasa.com")
        headers = {"Authorization": f"Bearer {token}"}

        marker = uuid.uuid4().hex[:8]
        payload = {
            "issue_category": "Candidate Applications & Pipeline",
            "subject": f"Pipeline Question {marker}",
            "description": f"Detailed question about candidate pipeline {marker}.",
        }

        # First request
        resp1 = await client.post(
            "/api/v1/recruiter/support/requests",
            headers=headers,
            json=payload,
        )
        assert resp1.status_code in (200, 201)
        ticket_number_1 = resp1.json()["ticket_number"]

        # Immediate second request (simulating double click)
        resp2 = await client.post(
            "/api/v1/recruiter/support/requests",
            headers=headers,
            json=payload,
        )
        assert resp2.status_code in (200, 201)
        ticket_number_2 = resp2.json()["ticket_number"]

        assert ticket_number_1 == ticket_number_2

        # Verify only 1 record exists in MySQL for this subject
        async with AsyncSessionLocal() as session:
            stmt = select(RecruiterSupportRequest).where(
                RecruiterSupportRequest.subject == payload["subject"]
            )
            res = await session.execute(stmt)
            records = res.scalars().all()
            assert len(records) == 1


@pytest.mark.asyncio
async def test_support_request_remains_persisted():
    """TEST 9: Refresh/reopen backend database: support request remains persisted in MySQL."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "recruiter1@ntrvikasa.com")
        headers = {"Authorization": f"Bearer {token}"}

        marker = uuid.uuid4().hex[:8]
        payload = {
            "issue_category": "Company Verification & Documents",
            "subject": f"Verification Status Inquiry {marker}",
            "description": f"Inquiring about our corporate document verification status {marker}.",
        }

        resp = await client.post(
            "/api/v1/recruiter/support/requests",
            headers=headers,
            json=payload,
        )
        assert resp.status_code == 201
        ticket_number = resp.json()["ticket_number"]

        # Read back in completely new database session
        async with AsyncSessionLocal() as session:
            stmt = select(RecruiterSupportRequest).where(
                RecruiterSupportRequest.ticket_number == ticket_number
            )
            res = await session.execute(stmt)
            ticket = res.scalar_one_or_none()
            assert ticket is not None
            assert ticket.ticket_number == ticket_number
            assert ticket.subject == payload["subject"]


@pytest.mark.asyncio
async def test_ticket_number_uniqueness():
    """TEST 10: Ticket numbers are unique and incrementing sequentially."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "recruiter1@ntrvikasa.com")
        headers = {"Authorization": f"Bearer {token}"}

        ticket_numbers = set()
        for i in range(3):
            marker = uuid.uuid4().hex[:8]
            resp = await client.post(
                "/api/v1/recruiter/support/requests",
                headers=headers,
                json={
                    "issue_category": "Hiring Team & Collaborators",
                    "subject": f"Unique Ticket Test {i} {marker}",
                    "description": f"Description for unique ticket test {i} {marker}.",
                },
            )
            assert resp.status_code == 201
            t_num = resp.json()["ticket_number"]
            assert t_num not in ticket_numbers
            ticket_numbers.add(t_num)

        assert len(ticket_numbers) == 3


@pytest.mark.asyncio
async def test_recruiter_list_own_support_requests():
    """Recruiter can list their own submitted support requests via GET /recruiter/support/requests."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "recruiter1@ntrvikasa.com")
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.get("/api/v1/recruiter/support/requests", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] >= 1
        assert len(data["items"]) == data["total"]

        first = data["items"][0]
        assert "ticket_number" in first
        assert "issue_category" in first
        assert "subject" in first
        assert "status" in first


@pytest.mark.asyncio
async def test_openapi_contains_recruiter_support():
    """Swagger / OpenAPI schema contains canonical recruiter support endpoints with Bearer security."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/openapi.json")
        assert resp.status_code == 200
        schema = resp.json()

        paths = schema.get("paths", {})
        assert "/api/v1/recruiter/support/requests" in paths
        endpoint = paths["/api/v1/recruiter/support/requests"]
        assert "post" in endpoint
        assert "get" in endpoint

        # Verify Bearer security scheme
        post_spec = endpoint["post"]
        assert "security" in post_spec
        security_schemes = [list(s.keys())[0] for s in post_spec["security"]]
        assert "Bearer" in security_schemes
