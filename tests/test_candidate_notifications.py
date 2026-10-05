"""
Automated Pytest Suite for Candidate Notifications
===================================================
Tests verify:
1.  Unauthenticated access to notification endpoints returns 401
2.  Non-candidate roles (Recruiter, Admin) receive 403
3.  Candidate gets own notifications persisted in MySQL
4.  Candidate isolation: Candidate A cannot view Candidate B notification (404)
5.  Candidate isolation: Candidate A cannot mark read Candidate B notification (404)
6.  Candidate isolation: Candidate A cannot dismiss Candidate B notification (404)
7.  Category filter: ?category=interview returns only interview notifications
8.  Category filter: ?category=shortlisted returns shortlisted notifications
9.  Search filter: ?search=Infosys matches relevant items
10. Unread filter: ?is_read=false returns only unread items
11. Unread count endpoint: GET /candidate/notifications/unread-count
12. Mark single notification as read: PATCH /candidate/notifications/{id}/read
13. Mark single notification as read is idempotent
14. Mark multiple notifications as read: POST /candidate/notifications/mark-read
15. Dismiss single notification: PATCH /candidate/notifications/{id}/dismiss
16. Dismiss multiple notifications: POST /candidate/notifications/dismiss
17. Dismissed notifications are omitted from default list
18. Dismissed notifications appear when ?include_dismissed=true
"""
import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database.session import AsyncSessionLocal
from app.models.notification import Notification
from app.services.notification_service import NotificationService
from app.models.candidate import CandidateProfile
from sqlalchemy import select


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


async def _register_candidate(
    client: AsyncClient,
    password: str = "password123",
) -> dict:
    """Register a fresh candidate with unique credentials and return token & data."""
    unique_suffix = uuid.uuid4().hex[:8]
    email = f"notif_tester_{unique_suffix}@example.com"
    phone = f"98{uuid.uuid4().int % 100000000:08d}"
    aadhaar = f"{uuid.uuid4().int % 1000000000000:012d}"

    payload = {
        "name": f"Notification Tester {unique_suffix}",
        "email": email,
        "phone": phone,
        "aadhaar_number": aadhaar,
        "district": "NTR District",
        "mandal": "Vijayawada Urban",
        "village": "Bhavanipuram",
        "qualification_level": "GRADUATE",
        "password": password,
        "terms_accepted": True,
    }
    resp = await client.post("/api/v1/auth/candidate/register", json=payload)
    assert resp.status_code in (200, 201), f"Register candidate failed: {resp.text}"
    data = resp.json()
    token = data.get("access_token") or await _login(client, email, password)
    return {
        "email": email,
        "token": token,
        "candidate_id": data.get("candidate", {}).get("id") or data.get("candidate_id"),
    }


# ── Tests ──────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_notifications_unauthenticated_returns_401():
    """Unauthenticated access to candidate notifications must return 401."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/candidate/notifications")
        assert resp.status_code == 401

        resp = await client.get("/api/v1/candidate/notifications/unread-count")
        assert resp.status_code == 401

        resp = await client.post("/api/v1/candidate/notifications/mark-read", json={})
        assert resp.status_code == 401

        resp = await client.post("/api/v1/candidate/notifications/dismiss", json={})
        assert resp.status_code == 401


@pytest.mark.asyncio
async def test_notifications_non_candidate_returns_403():
    """Recruiters or Admins accessing candidate notifications must receive 403."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        recruiter_token = await _login(client, "recruiter1@ntrvikasa.com", role="RECRUITER")
        resp = await client.get(
            "/api/v1/candidate/notifications",
            headers={"Authorization": f"Bearer {recruiter_token}"},
        )
        assert resp.status_code == 403


@pytest.mark.asyncio
async def test_candidate_gets_own_notifications():
    """Candidate 1 can retrieve their persisted notifications with total and unread counts."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "candidate1@ntrvikasa.com")
        resp = await client.get(
            "/api/v1/candidate/notifications",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert "unread_count" in data
        assert data["total"] >= 1
        assert len(data["items"]) == data["total"]

        # Check notification item schema
        item = data["items"][0]
        assert "id" in item
        assert "title" in item
        assert "message" in item
        assert "category" in item
        assert "is_read" in item
        assert "read" in item  # computed property
        assert "time" in item  # computed property


@pytest.mark.asyncio
async def test_candidate_unread_count_endpoint():
    """Candidate can query the unread notification count directly for header bell."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "candidate1@ntrvikasa.com")
        resp = await client.get(
            "/api/v1/candidate/notifications/unread-count",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "unread_count" in data
        assert isinstance(data["unread_count"], int)


@pytest.mark.asyncio
async def test_candidate_category_filter():
    """Filtering notifications by category returns only notifications in that category."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "candidate1@ntrvikasa.com")

        # Category: interview
        resp = await client.get(
            "/api/v1/candidate/notifications?category=interview",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        for item in data["items"]:
            assert item["category"].lower() == "interview"

        # Category: shortlisted
        resp_sl = await client.get(
            "/api/v1/candidate/notifications?category=shortlisted",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp_sl.status_code == 200
        data_sl = resp_sl.json()
        for item in data_sl["items"]:
            assert "shortlist" in item["category"].lower()


@pytest.mark.asyncio
async def test_candidate_search_filter():
    """Searching notifications matches keywords in title or message."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "candidate1@ntrvikasa.com")

        resp = await client.get(
            "/api/v1/candidate/notifications?search=Infosys",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        for item in data["items"]:
            assert "infosys" in item["title"].lower() or "infosys" in item["message"].lower()


@pytest.mark.asyncio
async def test_candidate_unread_filter():
    """Filtering by is_read=false returns only unread notifications."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "candidate1@ntrvikasa.com")

        resp = await client.get(
            "/api/v1/candidate/notifications?is_read=false",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        for item in data["items"]:
            assert item["is_read"] is False
            assert item["read"] is False


@pytest.mark.asyncio
async def test_candidate_isolation_cannot_access_or_modify_other_notification():
    """Candidate A cannot view, mark read, or dismiss Candidate B's notification."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        cand_a = await _register_candidate(client)
        cand_b = await _register_candidate(client)

        # Create a notification owned by Candidate A
        async with AsyncSessionLocal() as session:
            notif = await NotificationService.create_notification(
                db=session,
                candidate_id=cand_a["candidate_id"],
                category="application",
                title="Confidential Notification for A",
                message="Only candidate A should see this.",
            )
            notif_id = notif.id

        # Candidate A can access it
        resp = await client.get(
            f"/api/v1/candidate/notifications/{notif_id}",
            headers={"Authorization": f"Bearer {cand_a['token']}"},
        )
        assert resp.status_code == 200
        assert resp.json()["id"] == notif_id

        # Candidate B attempts to GET Candidate A's notification -> 404
        resp_b_get = await client.get(
            f"/api/v1/candidate/notifications/{notif_id}",
            headers={"Authorization": f"Bearer {cand_b['token']}"},
        )
        assert resp_b_get.status_code == 404

        # Candidate B attempts to PATCH read Candidate A's notification -> 404
        resp_b_read = await client.patch(
            f"/api/v1/candidate/notifications/{notif_id}/read",
            headers={"Authorization": f"Bearer {cand_b['token']}"},
        )
        assert resp_b_read.status_code == 404

        # Candidate B attempts to PATCH dismiss Candidate A's notification -> 404
        resp_b_dismiss = await client.patch(
            f"/api/v1/candidate/notifications/{notif_id}/dismiss",
            headers={"Authorization": f"Bearer {cand_b['token']}"},
        )
        assert resp_b_dismiss.status_code == 404


@pytest.mark.asyncio
async def test_mark_single_notification_read_and_idempotent():
    """Marking a notification as read updates status and is idempotent."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        cand = await _register_candidate(client)

        # Create unread notification for cand
        async with AsyncSessionLocal() as session:
            notif = await NotificationService.create_notification(
                db=session,
                candidate_id=cand["candidate_id"],
                category="interview",
                title="Interview Schedule Test",
                message="Testing read status.",
            )
            notif_id = notif.id

        # Mark read
        resp = await client.patch(
            f"/api/v1/candidate/notifications/{notif_id}/read",
            headers={"Authorization": f"Bearer {cand['token']}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["notification"]["is_read"] is True

        # Call again (idempotent)
        resp2 = await client.patch(
            f"/api/v1/candidate/notifications/{notif_id}/read",
            headers={"Authorization": f"Bearer {cand['token']}"},
        )
        assert resp2.status_code == 200
        assert resp2.json()["notification"]["is_read"] is True


@pytest.mark.asyncio
async def test_mark_multiple_notifications_read():
    """Candidate can mark multiple specified notifications as read."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        cand = await _register_candidate(client)

        async with AsyncSessionLocal() as session:
            n1 = await NotificationService.create_notification(
                db=session,
                candidate_id=cand["candidate_id"],
                category="application",
                title="Notif 1",
                message="Message 1",
            )
            n2 = await NotificationService.create_notification(
                db=session,
                candidate_id=cand["candidate_id"],
                category="application",
                title="Notif 2",
                message="Message 2",
            )
            ids = [n1.id, n2.id]

        resp = await client.post(
            "/api/v1/candidate/notifications/mark-read",
            headers={"Authorization": f"Bearer {cand['token']}"},
            json={"notification_ids": ids},
        )
        assert resp.status_code == 200
        assert resp.json()["updated_count"] == 2

        # Check unread count is now 0
        unread_resp = await client.get(
            "/api/v1/candidate/notifications/unread-count",
            headers={"Authorization": f"Bearer {cand['token']}"},
        )
        assert unread_resp.json()["unread_count"] == 0


@pytest.mark.asyncio
async def test_dismiss_single_and_multiple_notifications():
    """Dismissing notifications soft-hides them from normal query results."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        cand = await _register_candidate(client)

        async with AsyncSessionLocal() as session:
            n1 = await NotificationService.create_notification(
                db=session,
                candidate_id=cand["candidate_id"],
                category="support",
                title="Dismiss Test 1",
                message="Message to dismiss",
            )
            n2 = await NotificationService.create_notification(
                db=session,
                candidate_id=cand["candidate_id"],
                category="account",
                title="Dismiss Test 2",
                message="Message to dismiss in bulk",
            )
            id1 = n1.id
            id2 = n2.id

        # Dismiss single
        resp = await client.patch(
            f"/api/v1/candidate/notifications/{id1}/dismiss",
            headers={"Authorization": f"Bearer {cand['token']}"},
        )
        assert resp.status_code == 200

        # Normal list should only contain n2
        resp_list = await client.get(
            "/api/v1/candidate/notifications",
            headers={"Authorization": f"Bearer {cand['token']}"},
        )
        assert resp_list.status_code == 200
        items = resp_list.json()["items"]
        assert len(items) == 1
        assert items[0]["id"] == id2

        # Bulk dismiss n2
        resp_bulk = await client.post(
            "/api/v1/candidate/notifications/dismiss",
            headers={"Authorization": f"Bearer {cand['token']}"},
            json={"notification_ids": [id2]},
        )
        assert resp_bulk.status_code == 200
        assert resp_bulk.json()["updated_count"] == 1

        # Now normal list should be empty
        resp_empty = await client.get(
            "/api/v1/candidate/notifications",
            headers={"Authorization": f"Bearer {cand['token']}"},
        )
        assert resp_empty.json()["total"] == 0

        # With include_dismissed=true, both appear
        resp_all = await client.get(
            "/api/v1/candidate/notifications?include_dismissed=true",
            headers={"Authorization": f"Bearer {cand['token']}"},
        )
        assert resp_all.json()["total"] == 2
