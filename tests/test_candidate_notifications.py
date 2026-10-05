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


# ── Delete Functionality Tests ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_delete_unauthenticated_returns_401():
    """TEST 7: No access token returns 401 Unauthorized for both single and bulk delete."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Single delete without token
        resp_single = await client.delete("/api/v1/candidate/notifications/test-notif-123")
        assert resp_single.status_code == 401

        # Bulk delete without token
        resp_bulk = await client.request(
            "DELETE",
            "/api/v1/candidate/notifications/bulk",
            json={"notification_ids": ["test-notif-123"]},
        )
        assert resp_bulk.status_code == 401


@pytest.mark.asyncio
async def test_delete_invalid_or_expired_token_returns_401():
    """TEST 8: Invalid or expired access token returns 401 Unauthorized."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"Authorization": "Bearer invalid.expired.token"}
        resp = await client.delete(
            "/api/v1/candidate/notifications/test-notif-123",
            headers=headers,
        )
        assert resp.status_code == 401

        resp_bulk = await client.request(
            "DELETE",
            "/api/v1/candidate/notifications/bulk",
            headers=headers,
            json={"notification_ids": ["test-notif-123"]},
        )
        assert resp_bulk.status_code == 401


@pytest.mark.asyncio
async def test_candidate_deletes_own_notification():
    """TEST 1: Authenticated candidate deletes own notification. Returns 200 and permanently removes from MySQL."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        cand = await _register_candidate(client)

        async with AsyncSessionLocal() as session:
            notif = await NotificationService.create_notification(
                db=session,
                candidate_id=cand["candidate_id"],
                category="support",
                title="Single Delete Test",
                message="Notification to be deleted permanently",
            )
            notif_id = notif.id

        # Verify it exists in DB
        async with AsyncSessionLocal() as session:
            q = select(Notification).where(Notification.id == notif_id)
            res = await session.execute(q)
            assert res.scalar_one_or_none() is not None

        # Execute DELETE
        resp = await client.delete(
            f"/api/v1/candidate/notifications/{notif_id}",
            headers={"Authorization": f"Bearer {cand['token']}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["message"] == "Notification deleted successfully."

        # Verify it is completely removed from MySQL
        async with AsyncSessionLocal() as session:
            q = select(Notification).where(Notification.id == notif_id)
            res = await session.execute(q)
            assert res.scalar_one_or_none() is None

        # Query notifications list - must not appear even with include_dismissed=true
        resp_list = await client.get(
            "/api/v1/candidate/notifications?include_dismissed=true",
            headers={"Authorization": f"Bearer {cand['token']}"},
        )
        assert resp_list.status_code == 200
        ids = [item["id"] for item in resp_list.json()["items"]]
        assert notif_id not in ids


@pytest.mark.asyncio
async def test_candidate_cannot_delete_other_candidate_notification():
    """TEST 2: Candidate A cannot delete Candidate B's notification. Returns 404 and record remains in MySQL."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        cand_a = await _register_candidate(client)
        cand_b = await _register_candidate(client)

        async with AsyncSessionLocal() as session:
            notif_b = await NotificationService.create_notification(
                db=session,
                candidate_id=cand_b["candidate_id"],
                category="interview",
                title="Candidate B Notification",
                message="Candidate B secret message",
            )
            notif_b_id = notif_b.id

        # Candidate A attempts to delete Candidate B's notification
        resp = await client.delete(
            f"/api/v1/candidate/notifications/{notif_b_id}",
            headers={"Authorization": f"Bearer {cand_a['token']}"},
        )
        assert resp.status_code == 404

        # Verify notification still exists in MySQL intact
        async with AsyncSessionLocal() as session:
            q = select(Notification).where(Notification.id == notif_b_id)
            res = await session.execute(q)
            row = res.scalar_one_or_none()
            assert row is not None
            assert row.candidate_id == cand_b["candidate_id"]


@pytest.mark.asyncio
async def test_bulk_delete_own_notifications():
    """TEST 3: Authenticated candidate bulk deletes 3 own notifications. Returns 200 with deleted_count=3 and removes from MySQL."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        cand = await _register_candidate(client)

        ids = []
        async with AsyncSessionLocal() as session:
            for i in range(3):
                n = await NotificationService.create_notification(
                    db=session,
                    candidate_id=cand["candidate_id"],
                    category="application",
                    title=f"Bulk Delete Test {i+1}",
                    message=f"Message {i+1}",
                )
                ids.append(n.id)

        # Call bulk delete API
        resp = await client.request(
            "DELETE",
            "/api/v1/candidate/notifications/bulk",
            headers={"Authorization": f"Bearer {cand['token']}"},
            json={"notification_ids": ids},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["message"] == "Notifications deleted successfully."
        assert data["deleted_count"] == 3

        # Verify all 3 are deleted from MySQL
        async with AsyncSessionLocal() as session:
            q = select(Notification).where(Notification.id.in_(ids))
            res = await session.execute(q)
            assert len(res.scalars().all()) == 0


@pytest.mark.asyncio
async def test_bulk_delete_with_foreign_notification_rejected():
    """TEST 4: Bulk delete containing another candidate's notification is rejected with 404; unauthorized notification is NOT deleted."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        cand_a = await _register_candidate(client)
        cand_b = await _register_candidate(client)

        async with AsyncSessionLocal() as session:
            n_a = await NotificationService.create_notification(
                db=session,
                candidate_id=cand_a["candidate_id"],
                category="support",
                title="A Own Notification",
                message="A's message",
            )
            n_b = await NotificationService.create_notification(
                db=session,
                candidate_id=cand_b["candidate_id"],
                category="offer",
                title="B Notification",
                message="B's message",
            )
            id_a = n_a.id
            id_b = n_b.id

        # Candidate A attempts bulk delete including Candidate B's notification
        resp = await client.request(
            "DELETE",
            "/api/v1/candidate/notifications/bulk",
            headers={"Authorization": f"Bearer {cand_a['token']}"},
            json={"notification_ids": [id_a, id_b]},
        )
        assert resp.status_code == 404

        # Verify Candidate B's notification is definitely untouched
        async with AsyncSessionLocal() as session:
            q_b = select(Notification).where(Notification.id == id_b)
            res_b = await session.execute(q_b)
            assert res_b.scalar_one_or_none() is not None


@pytest.mark.asyncio
async def test_bulk_delete_empty_list_returns_422():
    """TEST 5: Empty bulk list returns 422 validation error."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        cand = await _register_candidate(client)

        resp = await client.request(
            "DELETE",
            "/api/v1/candidate/notifications/bulk",
            headers={"Authorization": f"Bearer {cand['token']}"},
            json={"notification_ids": []},
        )
        assert resp.status_code == 422


@pytest.mark.asyncio
async def test_delete_non_existent_notification_returns_404():
    """TEST 6: Invalid/non-existent notification ID returns 404."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        cand = await _register_candidate(client)

        resp = await client.delete(
            "/api/v1/candidate/notifications/non_existent_id_99999",
            headers={"Authorization": f"Bearer {cand['token']}"},
        )
        assert resp.status_code == 404

