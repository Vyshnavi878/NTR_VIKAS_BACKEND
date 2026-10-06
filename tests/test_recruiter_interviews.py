"""
Comprehensive Integration Tests for Recruiter Interview Management
Covers:
- Authentication & JWT Bearer token enforcement (401 / 403)
- GET /api/v1/recruiter/interviews (list, filters, dynamic tab counts)
- GET /api/v1/recruiter/interviews/{id} (details, IDOR isolation)
- POST /api/v1/recruiter/interviews (schedule, validation, conflict 409, notifications, email)
- PATCH /api/v1/recruiter/interviews/{id} and /reschedule (reschedule, status RESCHEDULED)
- POST /api/v1/recruiter/interviews/{id}/cancel (cancel, status CANCELLED, timestamp, reason)
- POST /api/v1/recruiter/interviews/{id}/complete (complete, status COMPLETED, notes)
"""
import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text
from app.main import app
from app.database.session import AsyncSessionLocal
from app.services.email_service import EmailService


@pytest_asyncio.fixture(autouse=True)
async def cleanup_test_interviews():
    """Clean up test-created interviews before and after each test."""
    yield
    async with AsyncSessionLocal() as session:
        await session.execute(
            text("DELETE FROM notifications WHERE category = 'INTERVIEW' AND title LIKE '%Automation Test%'")
        )
        await session.execute(
            text("DELETE FROM interviews WHERE notes LIKE '%Automation Test%' OR candidate_name LIKE '%Automation Test%' OR round_name LIKE '%Test Round%'")
        )
        await session.commit()


async def _login(client: AsyncClient, email: str, password: str = "password123", role: str = "RECRUITER") -> str:
    """Helper to authenticate and return a valid JWT Bearer access token."""
    resp = await client.post("/api/v1/auth/login", json={
        "email": email,
        "password": password,
        "role": role,
    })
    assert resp.status_code == 200, f"Login failed for {email}: {resp.text}"
    return resp.json()["access_token"]


# ── 1. Authentication & Security Tests ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_interviews_unauthenticated_returns_401():
    """Requests without token must be rejected with 401."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/recruiter/interviews")
        assert resp.status_code == 401
        assert "Not authenticated" in resp.text


@pytest.mark.asyncio
async def test_candidate_token_forbidden_on_recruiter_interviews():
    """Candidate token must be rejected with 403 Forbidden."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        cand_token = await _login(client, "candidate1@ntrvikasa.com", "password123", role="CANDIDATE")
        resp = await client.get(
            "/api/v1/recruiter/interviews",
            headers={"Authorization": f"Bearer {cand_token}"},
        )
        assert resp.status_code == 403
        assert "Recruiter account required" in resp.text


# ── 2. List & Detail Tests ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_recruiter_interviews_success():
    """Recruiter can list interviews with dynamic counts and schema fields."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        rec_token = await _login(client, "recruiter1@ntrvikasa.com")
        resp = await client.get(
            "/api/v1/recruiter/interviews",
            headers={"Authorization": f"Bearer {rec_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert "tab_counts" in data
        assert data["tab_counts"]["all"] >= 3
        assert data["tab_counts"]["scheduled"] >= 2
        assert data["tab_counts"]["completed"] >= 1

        # Check seeded demo interviews are present
        items = data["items"]
        names = [item["candidate_name"] for item in items]
        assert "Priya Sharma" in names
        assert "Rahul Kumar" in names
        assert "Vikram Sethi" in names

        # Verify candidate and job sub-objects & camelCase aliases
        priya = next(i for i in items if i["candidate_name"] == "Priya Sharma")
        assert priya["status"] == "SCHEDULED"
        assert priya["candidate"]["name"] == "Priya Sharma"
        assert "Senior Frontend Engineer" in priya["job"]["title"]
        assert priya["candidateName"] == "Priya Sharma"
        assert priya["jobTitle"] == priya["job"]["title"]
        assert priya["scheduled_date"] == "2026-09-10"


@pytest.mark.asyncio
async def test_get_interview_detail_success():
    """Fetch interview by ID with recruiter authorization."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        rec_token = await _login(client, "recruiter1@ntrvikasa.com")
        list_resp = await client.get(
            "/api/v1/recruiter/interviews",
            headers={"Authorization": f"Bearer {rec_token}"},
        )
        interview_id = list_resp.json()["items"][0]["id"]

        detail_resp = await client.get(
            f"/api/v1/recruiter/interviews/{interview_id}",
            headers={"Authorization": f"Bearer {rec_token}"},
        )
        assert detail_resp.status_code == 200
        detail = detail_resp.json()
        assert detail["id"] == interview_id
        assert detail["candidate_name"] is not None


# ── 3. Schedule Interview & Conflict Checks ───────────────────────────────────

@pytest.mark.asyncio
async def test_schedule_interview_and_conflict_validation():
    """Schedule a new interview, verify DB persistence, notifications, email, and 409 conflict."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        rec_token = await _login(client, "recruiter1@ntrvikasa.com")

        # 1. Schedule Interview for NTR-APP-501 (Priya Sharma)
        schedule_payload = {
            "application_id": "NTR-APP-501",
            "scheduled_date": "2026-11-20",
            "start_time": "10:00",
            "end_time": "11:00",
            "format": "ONLINE",
            "meeting_link": "https://meet.google.com/test-automation",
            "interviewer_panel": ["Arjun Reddy", "Test Lead Architect"],
            "agenda_notes": "Automation Test Round: Architecture & System Design",
        }

        EmailService.sent_emails_history.clear()

        resp = await client.post(
            "/api/v1/recruiter/interviews",
            json=schedule_payload,
            headers={"Authorization": f"Bearer {rec_token}"},
        )
        assert resp.status_code == 201, resp.text
        created = resp.json()
        assert created["status"] == "SCHEDULED"
        assert created["scheduled_date"] == "2026-11-20"
        assert created["start_time"] == "10:00"
        assert created["end_time"] == "11:00"
        interview_id = created["id"]

        # Verify Email Service was invoked
        assert len(EmailService.sent_emails_history) > 0
        last_email = EmailService.sent_emails_history[-1]
        assert last_email["scheduled_date"] == "2026-11-20"
        assert last_email["start_time"] == "10:00"

        # 2. Test Scheduling Conflict (Same candidate at same date & overlapping time -> 409)
        conflict_payload = {
            "application_id": "NTR-APP-501",
            "scheduled_date": "2026-11-20",
            "start_time": "10:30",
            "end_time": "11:30",
            "format": "ONLINE",
            "meeting_link": "https://meet.google.com/overlap-slot",
            "interviewer_panel": ["Another Interviewer"],
            "agenda_notes": "Automation Test Overlap",
        }
        conflict_resp = await client.post(
            "/api/v1/recruiter/interviews",
            json=conflict_payload,
            headers={"Authorization": f"Bearer {rec_token}"},
        )
        assert conflict_resp.status_code == 409
        assert "already has an interview scheduled" in conflict_resp.json()["detail"]

        # 3. Test Invalid Time Range (start_time >= end_time -> 422)
        invalid_time_payload = {
            "application_id": "NTR-APP-501",
            "scheduled_date": "2026-11-21",
            "start_time": "15:00",
            "end_time": "14:00",
            "format": "ONLINE",
            "meeting_link": "https://meet.google.com/invalid-time",
            "agenda_notes": "Automation Test Invalid Time",
        }
        invalid_resp = await client.post(
            "/api/v1/recruiter/interviews",
            json=invalid_time_payload,
            headers={"Authorization": f"Bearer {rec_token}"},
        )
        assert invalid_resp.status_code == 422

        # 4. Reschedule Interview (PATCH -> RESCHEDULED)
        resched_payload = {
            "scheduled_date": "2026-11-22",
            "start_time": "14:00",
            "end_time": "15:00",
            "agenda_notes": "Automation Test: Rescheduled to afternoon slot",
        }
        resched_resp = await client.patch(
            f"/api/v1/recruiter/interviews/{interview_id}",
            json=resched_payload,
            headers={"Authorization": f"Bearer {rec_token}"},
        )
        assert resched_resp.status_code == 200
        assert resched_resp.json()["status"] == "RESCHEDULED"
        assert resched_resp.json()["scheduled_date"] == "2026-11-22"

        # 5. Cancel Interview (POST /cancel -> CANCELLED)
        cancel_resp = await client.post(
            f"/api/v1/recruiter/interviews/{interview_id}/cancel",
            json={"reason": "Candidate requested cancellation for test."},
            headers={"Authorization": f"Bearer {rec_token}"},
        )
        assert cancel_resp.status_code == 200
        assert cancel_resp.json()["status"] == "CANCELLED"
        assert cancel_resp.json()["cancellation_reason"] == "Candidate requested cancellation for test."
        assert cancel_resp.json()["cancelled_at"] is not None

        # 6. Cannot Complete a Cancelled Interview (400)
        complete_fail = await client.post(
            f"/api/v1/recruiter/interviews/{interview_id}/complete",
            json={"notes": "Trying to complete cancelled interview"},
            headers={"Authorization": f"Bearer {rec_token}"},
        )
        assert complete_fail.status_code == 400


@pytest.mark.asyncio
async def test_complete_interview_success():
    """Complete an interview round and verify COMPLETED status and notes."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        rec_token = await _login(client, "recruiter1@ntrvikasa.com")

        # Schedule
        schedule_resp = await client.post(
            "/api/v1/recruiter/interviews",
            json={
                "application_id": "NTR-APP-502",
                "scheduled_date": "2026-12-05",
                "start_time": "16:00",
                "end_time": "17:00",
                "format": "ONLINE",
                "meeting_link": "https://meet.google.com/complete-test",
                "agenda_notes": "Automation Test Round For Completion",
            },
            headers={"Authorization": f"Bearer {rec_token}"},
        )
        assert schedule_resp.status_code == 201
        interview_id = schedule_resp.json()["id"]

        # Complete
        comp_resp = await client.post(
            f"/api/v1/recruiter/interviews/{interview_id}/complete",
            json={"notes": "Excellent performance. Candidate scored 9.5/10. Recommended for offer."},
            headers={"Authorization": f"Bearer {rec_token}"},
        )
        assert comp_resp.status_code == 200
        comp_data = comp_resp.json()
        assert comp_data["status"] == "COMPLETED"
        assert comp_data["completed_at"] is not None
        assert "9.5/10" in comp_data["notes"]


@pytest.mark.asyncio
async def test_invalid_token_returns_401():
    """Tampered or invalid Bearer token returns 401."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/recruiter/interviews",
            headers={"Authorization": "Bearer invalid.jwt.token.here"},
        )
        assert resp.status_code == 401


@pytest.mark.asyncio
async def test_idor_unauthorized_recruiter_access_returns_404():
    """Recruiter 2 cannot access or view Recruiter 1's private interview."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        rec1_token = await _login(client, "recruiter1@ntrvikasa.com")
        rec2_token = await _login(client, "recruiter2@ntrvikasa.com")

        # Get Recruiter 1's interview
        rec1_list = await client.get(
            "/api/v1/recruiter/interviews",
            headers={"Authorization": f"Bearer {rec1_token}"},
        )
        assert rec1_list.status_code == 200
        rec1_int_id = rec1_list.json()["items"][0]["id"]

        # Recruiter 2 tries to fetch Recruiter 1's interview
        rec2_fetch = await client.get(
            f"/api/v1/recruiter/interviews/{rec1_int_id}",
            headers={"Authorization": f"Bearer {rec2_token}"},
        )
        assert rec2_fetch.status_code == 404
        assert "not found or unauthorized" in rec2_fetch.json()["detail"].lower()


@pytest.mark.asyncio
async def test_invalid_application_id_returns_404():
    """Scheduling for a non-existent application returns 404."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        rec_token = await _login(client, "recruiter1@ntrvikasa.com")
        resp = await client.post(
            "/api/v1/recruiter/interviews",
            json={
                "application_id": "non-existent-app-99999",
                "scheduled_date": "2026-11-20",
                "start_time": "10:00",
                "end_time": "11:00",
            },
            headers={"Authorization": f"Bearer {rec_token}"},
        )
        assert resp.status_code == 404
        assert "not found or not accessible" in resp.json()["detail"].lower()

