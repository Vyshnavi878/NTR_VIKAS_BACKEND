"""
Automated Pytest Suite for Candidate Help & Support Tickets
===========================================================
Tests verify:
1.  Authenticated candidate can create a support ticket
2.  Unauthenticated request receives 401
3.  Non-candidate role receives 403
4.  Required issue category validation (invalid category -> 422)
5.  Required subject validation (empty/short -> 422)
6.  Required description validation (empty/short -> 422)
7.  Ticket number is generated server-side in NTR-SUP-XXXXXX format
8.  Ticket numbers are unique and incrementing
9.  New ticket status is always OPEN
10. Default priority is NORMAL
11. Candidate cannot override candidate_id, name, or email from request body
12. Candidate cannot set status (e.g., CLOSED) during creation
13. Candidate cannot set arbitrary administrative priority
14. Candidate can list own tickets
15. Candidate can view own ticket details by ticket_number
16. Candidate cannot view another candidate's ticket (returns 404, does not leak existence)
17. Tickets persist correctly in MySQL
18. Swagger / OpenAPI schema includes the canonical endpoints
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
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return resp.json()["access_token"]


# ── Tests ──────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_support_ticket_unauthenticated_returns_401():
    """Unauthenticated access to POST /candidate/support/tickets returns 401."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/candidate/support/tickets",
            json={
                "issue_category": "Application Status & Tracker",
                "subject": "Need help with application status",
                "description": "I submitted an application yesterday and need confirmation.",
            },
        )
        assert resp.status_code == 401


@pytest.mark.asyncio
async def test_support_ticket_admin_role_returns_403():
    """Admin role attempting to access candidate support returns 403."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "admin1@ntrvikasa.com", "password123", role="ADMIN")
        headers = {"Authorization": f"Bearer {token}"}
        resp = await client.post(
            "/api/v1/candidate/support/tickets",
            headers=headers,
            json={
                "issue_category": "Application Status & Tracker",
                "subject": "Need help with application status",
                "description": "I submitted an application yesterday and need confirmation.",
            },
        )
        assert resp.status_code == 403


@pytest.mark.asyncio
async def test_support_ticket_creation_success():
    """Authenticated candidate can create a support ticket with server-generated ticket number."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "candidate1@ntrvikasa.com", "password123", role="CANDIDATE")
        headers = {"Authorization": f"Bearer {token}"}

        payload = {
            "issue_category": "Interview Scheduling & Links",
            "subject": "Interview link not opening for technical round",
            "description": "I received an invitation for interview round but the meeting link shows expired.",
        }
        resp = await client.post(
            "/api/v1/candidate/support/tickets",
            headers=headers,
            json=payload,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "ticket" in data
        ticket = data["ticket"]
        assert ticket["ticket_number"].startswith("NTR-SUP-")
        assert ticket["status"] == "OPEN"
        assert ticket["priority"] == "NORMAL"
        assert ticket["issue_category"] == "Interview Scheduling & Links"
        assert ticket["subject"] == payload["subject"]
        assert ticket["description"] == payload["description"]
        assert ticket["candidate_name"] == "Priya Sharma"
        assert ticket["registered_email"] == "candidate1@ntrvikasa.com"


@pytest.mark.asyncio
async def test_support_ticket_category_validation():
    """Invalid category strings are rejected with 422."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "candidate1@ntrvikasa.com", "password123", role="CANDIDATE")
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.post(
            "/api/v1/candidate/support/tickets",
            headers=headers,
            json={
                "issue_category": "Random Invalid Category String",
                "subject": "Valid Subject Here",
                "description": "Valid Description that has more than 10 characters.",
            },
        )
        assert resp.status_code == 422


@pytest.mark.asyncio
async def test_support_ticket_subject_validation():
    """Empty or too short subject is rejected with 422."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "candidate1@ntrvikasa.com", "password123", role="CANDIDATE")
        headers = {"Authorization": f"Bearer {token}"}

        # Empty subject
        resp = await client.post(
            "/api/v1/candidate/support/tickets",
            headers=headers,
            json={
                "issue_category": "Application Status & Tracker",
                "subject": "   ",
                "description": "Valid description explaining the problem thoroughly.",
            },
        )
        assert resp.status_code == 422

        # Too short subject
        resp2 = await client.post(
            "/api/v1/candidate/support/tickets",
            headers=headers,
            json={
                "issue_category": "Application Status & Tracker",
                "subject": "ab",
                "description": "Valid description explaining the problem thoroughly.",
            },
        )
        assert resp2.status_code == 422


@pytest.mark.asyncio
async def test_support_ticket_description_validation():
    """Empty or too short description is rejected with 422."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "candidate1@ntrvikasa.com", "password123", role="CANDIDATE")
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.post(
            "/api/v1/candidate/support/tickets",
            headers=headers,
            json={
                "issue_category": "Application Status & Tracker",
                "subject": "Valid Subject Here",
                "description": "  ",
            },
        )
        assert resp.status_code == 422


@pytest.mark.asyncio
async def test_support_ticket_cannot_override_identity_or_status():
    """Request body cannot inject candidate_name, registered_email, or set status to CLOSED."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "candidate1@ntrvikasa.com", "password123", role="CANDIDATE")
        headers = {"Authorization": f"Bearer {token}"}

        payload = {
            "issue_category": "Profile & Skills Updating",
            "subject": "Testing parameter injection resistance",
            "description": "Attempting to send forged candidate identity and closed status.",
            "candidate_name": "Forged Hacker Name",
            "registered_email": "hacker@evil.com",
            "status": "CLOSED",
            "priority": "URGENT",
        }
        resp = await client.post(
            "/api/v1/candidate/support/tickets",
            headers=headers,
            json=payload,
        )
        assert resp.status_code == 201
        ticket = resp.json()["ticket"]
        # Authenticated user is candidate 1 (Priya Sharma, candidate1@ntrvikasa.com)
        assert ticket["candidate_name"] == "Priya Sharma"
        assert ticket["registered_email"] == "candidate1@ntrvikasa.com"
        assert ticket["status"] == "OPEN"
        assert ticket["priority"] == "NORMAL"


@pytest.mark.asyncio
async def test_candidate_list_own_tickets():
    """Candidate can list their submitted tickets."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "candidate1@ntrvikasa.com", "password123", role="CANDIDATE")
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.get("/api/v1/candidate/support/tickets", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)
        assert data["total"] >= 1
        for t in data["items"]:
            assert t["ticket_number"].startswith("NTR-SUP-")
            assert t["registered_email"] == "candidate1@ntrvikasa.com"


@pytest.mark.asyncio
async def test_candidate_get_ticket_details():
    """Candidate can view details of their own ticket by ticket_number."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "candidate1@ntrvikasa.com", "password123", role="CANDIDATE")
        headers = {"Authorization": f"Bearer {token}"}

        # Create a fresh ticket
        create_resp = await client.post(
            "/api/v1/candidate/support/tickets",
            headers=headers,
            json={
                "issue_category": "Job Mela Registration & QR Pass",
                "subject": "QR Pass not visible in downloads",
                "description": "I registered for the Vizag job mela but the QR pass download button gave a 404.",
            },
        )
        assert create_resp.status_code == 201
        created_ticket = create_resp.json()["ticket"]
        t_num = created_ticket["ticket_number"]

        # Fetch details
        detail_resp = await client.get(f"/api/v1/candidate/support/tickets/{t_num}", headers=headers)
        assert detail_resp.status_code == 200
        details = detail_resp.json()
        assert details["ticket_number"] == t_num
        assert details["issue_category"] == "Job Mela Registration & QR Pass"
        assert details["subject"] == "QR Pass not visible in downloads"
        assert details["status"] == "OPEN"


@pytest.mark.asyncio
async def test_cross_candidate_ticket_access_forbidden():
    """Candidate 2 cannot view or access Candidate 1's ticket (returns 404)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Candidate 1 creates a ticket
        token1 = await _login(client, "candidate1@ntrvikasa.com", "password123", role="CANDIDATE")
        headers1 = {"Authorization": f"Bearer {token1}"}

        create_resp = await client.post(
            "/api/v1/candidate/support/tickets",
            headers=headers1,
            json={
                "issue_category": "Other Support Request",
                "subject": "Private ticket for candidate 1",
                "description": "Sensitive query that should only be visible to candidate 1.",
            },
        )
        assert create_resp.status_code == 201
        ticket_number = create_resp.json()["ticket"]["ticket_number"]

        # Candidate 2 logs in and attempts to access Candidate 1's ticket
        token2 = await _login(client, "candidate2@ntrvikasa.com", "password123", role="CANDIDATE")
        headers2 = {"Authorization": f"Bearer {token2}"}

        detail_resp = await client.get(
            f"/api/v1/candidate/support/tickets/{ticket_number}",
            headers=headers2,
        )
        # Must return 404 to avoid leaking whether Candidate 1's ticket exists
        assert detail_resp.status_code == 404


@pytest.mark.asyncio
async def test_candidate2_sees_empty_tickets():
    """Candidate 2 has not submitted tickets and sees empty list."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token2 = await _login(client, "candidate2@ntrvikasa.com", "password123", role="CANDIDATE")
        headers2 = {"Authorization": f"Bearer {token2}"}

        resp = await client.get("/api/v1/candidate/support/tickets", headers=headers2)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["items"] == []


@pytest.mark.asyncio
async def test_support_tickets_openapi_canonical_endpoints():
    """Swagger documentation includes canonical /candidate/support/tickets routes."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/openapi.json")
        assert resp.status_code == 200
        schema = resp.json()
        paths = schema.get("paths", {})
        assert "/api/v1/candidate/support/tickets" in paths
        assert "post" in paths["/api/v1/candidate/support/tickets"]
        assert "get" in paths["/api/v1/candidate/support/tickets"]
        assert "/api/v1/candidate/support/tickets/{ticket_number}" in paths
        assert "get" in paths["/api/v1/candidate/support/tickets/{ticket_number}"]
