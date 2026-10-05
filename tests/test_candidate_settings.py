"""
Automated Pytest Suite for Candidate Settings & Account Lifecycle
==================================================================
Tests verify:
1.  Unauthenticated access to settings endpoints returns 401
2.  Non-candidate roles receive 403
3.  GET candidate settings returns default persisted settings
4.  PATCH notification settings persists values to MySQL
5.  PATCH privacy settings persists values to MySQL
6.  Recruiter talent search respects candidate visibility preference
7.  Change password with incorrect current password returns 401
8.  Change password with confirmation mismatch returns 422
9.  Change password with less than 8 characters returns 422
10. Change password with identical password returns 400
11. Change password updates hash; old password stops working; new password works for login
12. Account deletion deactivates account and prevents future login / API calls
13. Multi-candidate isolation (Candidate A settings never affect Candidate B)
"""
import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database.session import AsyncSessionLocal
from app.repositories.candidate_repository import CandidateRepository


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


async def _register_fresh_candidate(
    client: AsyncClient,
    password: str = "password123",
) -> dict:
    """Register a fresh candidate with unique credentials and return token & data."""
    unique_suffix = uuid.uuid4().hex[:8]
    email = f"settings_test_{unique_suffix}@example.com"
    phone = f"98{uuid.uuid4().int % 100000000:08d}"
    aadhaar = f"{uuid.uuid4().int % 1000000000000:012d}"

    payload = {
        "name": f"Settings Tester {unique_suffix}",
        "email": email,
        "phone": phone,
        "aadhaar_number": aadhaar,
        "district": "NTR District",
        "mandal": "Vijayawada Urban",
        "village": "Bhavanipuram",
        "qualification_level": "UG",
        "reference_admin": "District Nodal Officer (Vijayawada)",
        "password": password,
        "confirm_password": password,
        "terms_accepted": True,
    }
    resp = await client.post("/api/v1/auth/candidate/register", json=payload)
    assert resp.status_code == 201, f"Registration failed: {resp.text}"
    data = resp.json()
    return {
        "email": email,
        "password": password,
        "token": data["access_token"],
        "user_id": data["user"]["id"],
        "candidate_id": data["candidate"]["id"],
    }


# ── 1. Authentication & Authorization Tests ────────────────────────────────────

@pytest.mark.asyncio
async def test_settings_unauthenticated_returns_401():
    """All settings endpoints require authentication."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # GET settings
        r1 = await client.get("/api/v1/candidate/settings")
        assert r1.status_code == 401

        # PATCH notifications
        r2 = await client.patch(
            "/api/v1/candidate/settings/notifications",
            json={"email_job_application_alerts": False},
        )
        assert r2.status_code == 401

        # PATCH privacy
        r3 = await client.patch(
            "/api/v1/candidate/settings/privacy",
            json={"visible_in_recruiter_talent_search": False},
        )
        assert r3.status_code == 401

        # PATCH password
        r4 = await client.patch(
            "/api/v1/candidate/settings/password",
            json={
                "current_password": "old",
                "new_password": "new_password_123",
                "confirm_password": "new_password_123",
            },
        )
        assert r4.status_code == 401

        # DELETE account
        r5 = await client.delete("/api/v1/candidate/account")
        assert r5.status_code == 401


@pytest.mark.asyncio
async def test_settings_admin_role_returns_403():
    """Non-candidate roles cannot access candidate settings endpoints."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "admin1@ntrvikasa.com", "password123", role="ADMIN")
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.get("/api/v1/candidate/settings", headers=headers)
        assert resp.status_code == 403


# ── 2. Settings Defaults & Persistence ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_settings_default_values():
    """Newly registered candidate receives canonical default preferences."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        cand = await _register_fresh_candidate(client)
        headers = {"Authorization": f"Bearer {cand['token']}"}

        resp = await client.get("/api/v1/candidate/settings", headers=headers)
        assert resp.status_code == 200
        data = resp.json()

        assert data["email_job_application_alerts"] is True
        assert data["sms_whatsapp_notifications"] is True
        assert data["upcoming_interview_reminders"] is True
        assert data["weekly_job_recommendation_digest"] is False
        assert data["visible_in_recruiter_talent_search"] is True
        assert data["direct_recruiter_messages"] is True


@pytest.mark.asyncio
async def test_update_notification_preferences_persists():
    """Updating notification preferences persists to database and survives refetch."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        cand = await _register_fresh_candidate(client)
        headers = {"Authorization": f"Bearer {cand['token']}"}

        # Update notifications
        patch_resp = await client.patch(
            "/api/v1/candidate/settings/notifications",
            headers=headers,
            json={
                "email_job_application_alerts": False,
                "sms_whatsapp_notifications": False,
                "upcoming_interview_reminders": True,
                "weekly_job_recommendation_digest": True,
            },
        )
        assert patch_resp.status_code == 200
        patch_data = patch_resp.json()
        assert patch_data["email_job_application_alerts"] is False
        assert patch_data["sms_whatsapp_notifications"] is False
        assert patch_data["upcoming_interview_reminders"] is True
        assert patch_data["weekly_job_recommendation_digest"] is True

        # Refetch settings to verify persistence
        get_resp = await client.get("/api/v1/candidate/settings", headers=headers)
        assert get_resp.status_code == 200
        get_data = get_resp.json()
        assert get_data["email_job_application_alerts"] is False
        assert get_data["sms_whatsapp_notifications"] is False
        assert get_data["weekly_job_recommendation_digest"] is True


@pytest.mark.asyncio
async def test_update_privacy_preferences_persists():
    """Updating privacy preferences persists to database and survives refetch."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        cand = await _register_fresh_candidate(client)
        headers = {"Authorization": f"Bearer {cand['token']}"}

        # Update privacy
        patch_resp = await client.patch(
            "/api/v1/candidate/settings/privacy",
            headers=headers,
            json={
                "visible_in_recruiter_talent_search": False,
                "direct_recruiter_messages": False,
            },
        )
        assert patch_resp.status_code == 200
        patch_data = patch_resp.json()
        assert patch_data["visible_in_recruiter_talent_search"] is False
        assert patch_data["direct_recruiter_messages"] is False

        # Refetch settings
        get_resp = await client.get("/api/v1/candidate/settings", headers=headers)
        assert get_resp.status_code == 200
        get_data = get_resp.json()
        assert get_data["visible_in_recruiter_talent_search"] is False
        assert get_data["direct_recruiter_messages"] is False


# ── 3. Recruiter Search Visibility Rule ───────────────────────────────────────

@pytest.mark.asyncio
async def test_recruiter_talent_search_respects_visibility_setting():
    """Recruiter talent search must omit candidates with visible_in_recruiter_talent_search = False."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        cand_visible = await _register_fresh_candidate(client)
        cand_hidden = await _register_fresh_candidate(client)

        # Set cand_hidden privacy setting to False
        hidden_headers = {"Authorization": f"Bearer {cand_hidden['token']}"}
        resp = await client.patch(
            "/api/v1/candidate/settings/privacy",
            headers=hidden_headers,
            json={"visible_in_recruiter_talent_search": False, "direct_recruiter_messages": True},
        )
        assert resp.status_code == 200

        # Query via CandidateRepository.search_candidates_for_recruiters
        async with AsyncSessionLocal() as db:
            results = await CandidateRepository.search_candidates_for_recruiters(db, limit=500)
            returned_ids = [c.id for c in results]

            assert cand_visible["candidate_id"] in returned_ids
            assert cand_hidden["candidate_id"] not in returned_ids


# ── 4. Password Change Tests ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_change_password_wrong_current_password_returns_401():
    """Incorrect current password must return 401 Unauthorized."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        cand = await _register_fresh_candidate(client, password="initial_password_1")
        headers = {"Authorization": f"Bearer {cand['token']}"}

        resp = await client.patch(
            "/api/v1/candidate/settings/password",
            headers=headers,
            json={
                "current_password": "wrong_password_xyz",
                "new_password": "brand_new_password_123",
                "confirm_password": "brand_new_password_123",
            },
        )
        assert resp.status_code == 401
        assert "Current password is incorrect" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_change_password_mismatch_returns_422():
    """Mismatch between new_password and confirm_password must return 422."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        cand = await _register_fresh_candidate(client, password="initial_password_1")
        headers = {"Authorization": f"Bearer {cand['token']}"}

        resp = await client.patch(
            "/api/v1/candidate/settings/password",
            headers=headers,
            json={
                "current_password": "initial_password_1",
                "new_password": "brand_new_password_123",
                "confirm_password": "completely_different_pass",
            },
        )
        assert resp.status_code == 422
        assert "do not match" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_change_password_too_short_returns_422():
    """New password shorter than 8 characters must return 422."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        cand = await _register_fresh_candidate(client, password="initial_password_1")
        headers = {"Authorization": f"Bearer {cand['token']}"}

        resp = await client.patch(
            "/api/v1/candidate/settings/password",
            headers=headers,
            json={
                "current_password": "initial_password_1",
                "new_password": "short",
                "confirm_password": "short",
            },
        )
        assert resp.status_code == 422


@pytest.mark.asyncio
async def test_change_password_same_as_current_returns_400():
    """Entering the exact same password must return 400 Bad Request."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        cand = await _register_fresh_candidate(client, password="initial_password_1")
        headers = {"Authorization": f"Bearer {cand['token']}"}

        resp = await client.patch(
            "/api/v1/candidate/settings/password",
            headers=headers,
            json={
                "current_password": "initial_password_1",
                "new_password": "initial_password_1",
                "confirm_password": "initial_password_1",
            },
        )
        assert resp.status_code == 400
        assert "different from the current password" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_change_password_success_and_login_with_new_password():
    """Successful password update updates hash; old password fails; new password succeeds."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        old_pass = "old_password_123"
        new_pass = "brand_new_secret_456"

        cand = await _register_fresh_candidate(client, password=old_pass)
        headers = {"Authorization": f"Bearer {cand['token']}"}

        # Update password
        resp = await client.patch(
            "/api/v1/candidate/settings/password",
            headers=headers,
            json={
                "current_password": old_pass,
                "new_password": new_pass,
                "confirm_password": new_pass,
            },
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "success"

        # Try to log in with OLD password -> should fail
        fail_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": cand["email"], "password": old_pass, "role": "CANDIDATE"},
        )
        assert fail_resp.status_code == 401

        # Try to log in with NEW password -> should succeed
        success_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": cand["email"], "password": new_pass, "role": "CANDIDATE"},
        )
        assert success_resp.status_code == 200
        assert "access_token" in success_resp.json()


# ── 5. Account Deletion / Deactivation Tests ──────────────────────────────────

@pytest.mark.asyncio
async def test_delete_account_deactivates_and_prevents_login():
    """DELETE account sets is_active = False and rejects subsequent login attempts."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        cand = await _register_fresh_candidate(client, password="password123")
        headers = {"Authorization": f"Bearer {cand['token']}"}

        # Delete account
        del_resp = await client.delete("/api/v1/candidate/account", headers=headers)
        assert del_resp.status_code == 200
        assert "deleted successfully" in del_resp.json()["message"]

        # Attempt to login again -> must return 403 Forbidden (Account is inactive)
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": cand["email"], "password": "password123", "role": "CANDIDATE"},
        )
        assert login_resp.status_code == 403
        assert "inactive" in login_resp.json()["detail"].lower()

        # Attempt to call protected candidate endpoint with old token -> 403 (Account is inactive)
        prot_resp = await client.get("/api/v1/candidate/settings", headers=headers)
        assert prot_resp.status_code == 403


# ── 6. Candidate Isolation Test ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_candidate_settings_isolation():
    """Candidate A updating settings has no effect on Candidate B's settings."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        cand_a = await _register_fresh_candidate(client)
        cand_b = await _register_fresh_candidate(client)

        headers_a = {"Authorization": f"Bearer {cand_a['token']}"}
        headers_b = {"Authorization": f"Bearer {cand_b['token']}"}

        # Update Candidate A's settings
        await client.patch(
            "/api/v1/candidate/settings/notifications",
            headers=headers_a,
            json={"email_job_application_alerts": False, "weekly_job_recommendation_digest": True},
        )
        await client.patch(
            "/api/v1/candidate/settings/privacy",
            headers=headers_a,
            json={"visible_in_recruiter_talent_search": False},
        )

        # Check Candidate B's settings -> should still have defaults
        resp_b = await client.get("/api/v1/candidate/settings", headers=headers_b)
        assert resp_b.status_code == 200
        b_data = resp_b.json()

        assert b_data["email_job_application_alerts"] is True
        assert b_data["weekly_job_recommendation_digest"] is False
        assert b_data["visible_in_recruiter_talent_search"] is True
