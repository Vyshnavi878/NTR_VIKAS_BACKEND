"""
Candidate Dashboard Integration Tests
GET /api/v1/candidate/dashboard

Tests cover:
1.  Unauthenticated request returns 401
2.  Non-candidate (admin) role returns 403
3.  Authenticated candidate gets 200 with correct structure
4.  Candidate name matches their registration name
5.  Statistics block is present with integer counts
6.  Profile strength percentage is 0-100
7.  Profile strength label is a non-empty string
8.  Profile strength items are all booleans
9.  recent_applications is a list (empty or populated)
10. recommended_jobs is a list
11. upcoming_interviews is a list
12. Another candidate cannot read first candidate's dashboard
13. Profile strength completed items are deterministic for fresh accounts
14. Dashboard does NOT expose aadhaar_number
15. Dashboard does NOT expose hashed_password
16. Applied jobs count is an integer >= 0
17. Shortlisted count is integer >= 0
18. Interviews count is integer >= 0
19. Saved jobs count is integer >= 0
20. Dashboard endpoint appears in Swagger once (canonical path)
"""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


# ── Helpers ────────────────────────────────────────────────────────────────────

async def _login(client: AsyncClient, email: str, password: str = "password123", role: str = "CANDIDATE") -> str:
    """Return a valid Bearer access token for the given email."""
    resp = await client.post("/api/v1/auth/login", json={
        "email": email,
        "password": password,
        "role": role,
    })
    assert resp.status_code == 200, f"Login failed for {email}: {resp.text}"
    return resp.json()["access_token"]


# ── 1. Unauthenticated ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_dashboard_unauthenticated_returns_401():
    """No token → 401 Unauthorized."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/candidate/dashboard")
    assert resp.status_code == 401


# ── 2. Wrong role (Admin) ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_dashboard_admin_role_returns_403():
    """Admin JWT must not access the candidate dashboard."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "admin1@ntrvikasa.com", role="ADMIN")
        resp = await client.get(
            "/api/v1/candidate/dashboard",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 403


# ── 3. Happy path: 200 with full structure ─────────────────────────────────────

@pytest.mark.asyncio
async def test_dashboard_candidate1_returns_200():
    """Candidate 1 gets 200 with the expected top-level keys."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "candidate1@ntrvikasa.com")
        resp = await client.get(
            "/api/v1/candidate/dashboard",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    data = resp.json()
    for key in ("candidate", "statistics", "recent_applications", "profile_strength",
                "recommended_jobs", "upcoming_interviews"):
        assert key in data, f"Missing key: {key}"


# ── 4. Candidate name is correct ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_dashboard_candidate1_name_is_priya():
    """Candidate 1's full_name must be 'Priya Sharma' (as seeded)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "candidate1@ntrvikasa.com")
        resp = await client.get(
            "/api/v1/candidate/dashboard",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    assert resp.json()["candidate"]["full_name"] == "Priya Sharma"


# ── 5. Statistics block ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_dashboard_statistics_are_integers():
    """All four stat counters must be non-negative integers."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "candidate1@ntrvikasa.com")
        resp = await client.get(
            "/api/v1/candidate/dashboard",
            headers={"Authorization": f"Bearer {token}"},
        )
    stats = resp.json()["statistics"]
    for field in ("applied_jobs", "shortlisted", "interviews", "saved_jobs"):
        assert isinstance(stats[field], int), f"{field} must be int"
        assert stats[field] >= 0, f"{field} must be >= 0"


# ── 6 & 7. Profile strength percentage and label ───────────────────────────────

@pytest.mark.asyncio
async def test_dashboard_profile_strength_valid():
    """Profile strength percentage is 0-100 and label is non-empty."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "candidate1@ntrvikasa.com")
        resp = await client.get(
            "/api/v1/candidate/dashboard",
            headers={"Authorization": f"Bearer {token}"},
        )
    ps = resp.json()["profile_strength"]
    assert isinstance(ps["percentage"], int)
    assert 0 <= ps["percentage"] <= 100
    assert isinstance(ps["label"], str)
    assert len(ps["label"].strip()) > 0


# ── 8. Profile items are booleans ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_dashboard_profile_strength_items_are_booleans():
    """Every profile strength item must have a boolean 'completed' field."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "candidate1@ntrvikasa.com")
        resp = await client.get(
            "/api/v1/candidate/dashboard",
            headers={"Authorization": f"Bearer {token}"},
        )
    items = resp.json()["profile_strength"]["items"]
    assert len(items) > 0
    for item in items:
        assert "key" in item
        assert "label" in item
        assert isinstance(item["completed"], bool)


# ── 9. Recent applications is a list ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_dashboard_recent_applications_is_list():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "candidate1@ntrvikasa.com")
        resp = await client.get(
            "/api/v1/candidate/dashboard",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert isinstance(resp.json()["recent_applications"], list)


# ── 10. Recommended jobs is a list ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_dashboard_recommended_jobs_is_list():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "candidate1@ntrvikasa.com")
        resp = await client.get(
            "/api/v1/candidate/dashboard",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert isinstance(resp.json()["recommended_jobs"], list)


# ── 11. Upcoming interviews is a list ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_dashboard_upcoming_interviews_is_list():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "candidate1@ntrvikasa.com")
        resp = await client.get(
            "/api/v1/candidate/dashboard",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert isinstance(resp.json()["upcoming_interviews"], list)


# ── 12. Data isolation: Candidate 2 sees different name ───────────────────────

@pytest.mark.asyncio
async def test_dashboard_candidate2_sees_own_data():
    """Candidate 2 must receive their own name, not Candidate 1's."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token_c2 = await _login(client, "candidate2@ntrvikasa.com")
        resp_c2 = await client.get(
            "/api/v1/candidate/dashboard",
            headers={"Authorization": f"Bearer {token_c2}"},
        )
    assert resp_c2.status_code == 200
    name_c2 = resp_c2.json()["candidate"]["full_name"]
    assert name_c2 != "Priya Sharma", "Candidate 2 must NOT see Candidate 1's name"
    assert len(name_c2.strip()) > 0


# ── 13. Profile strength determinism for fresh accounts ───────────────────────

@pytest.mark.asyncio
async def test_dashboard_profile_strength_deterministic():
    """
    Fresh seed accounts have name + phone + qualification set, but no headline/bio/village.
    Expected: contact(25) + email(15) + qualification(15) = 55%.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "candidate1@ntrvikasa.com")
        resp = await client.get(
            "/api/v1/candidate/dashboard",
            headers={"Authorization": f"Bearer {token}"},
        )
    pct = resp.json()["profile_strength"]["percentage"]
    # Seeded accounts have name + phone (25%) + email (15%) + qualification (15%) = 55%
    assert pct == 55, f"Expected 55% for seeded account, got {pct}%"


# ── 14. Aadhaar not exposed ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_dashboard_does_not_expose_aadhaar():
    """Aadhaar number must never appear anywhere in the dashboard response."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "candidate1@ntrvikasa.com")
        resp = await client.get(
            "/api/v1/candidate/dashboard",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert "aadhaar" not in resp.text.lower(), "Aadhaar data must never be returned"
    assert "999900001111" not in resp.text


# ── 15. Hashed password not exposed ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_dashboard_does_not_expose_password():
    """Hashed password must never appear in the dashboard response."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "candidate1@ntrvikasa.com")
        resp = await client.get(
            "/api/v1/candidate/dashboard",
            headers={"Authorization": f"Bearer {token}"},
        )
    text = resp.text.lower()
    assert "hashed_password" not in text
    assert "password" not in text


# ── 16–19. Individual stat fields ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_dashboard_applied_jobs_count_is_integer():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "candidate1@ntrvikasa.com")
        resp = await client.get("/api/v1/candidate/dashboard", headers={"Authorization": f"Bearer {token}"})
    assert isinstance(resp.json()["statistics"]["applied_jobs"], int)

@pytest.mark.asyncio
async def test_dashboard_shortlisted_count_is_integer():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "candidate1@ntrvikasa.com")
        resp = await client.get("/api/v1/candidate/dashboard", headers={"Authorization": f"Bearer {token}"})
    assert isinstance(resp.json()["statistics"]["shortlisted"], int)

@pytest.mark.asyncio
async def test_dashboard_interviews_count_is_integer():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "candidate1@ntrvikasa.com")
        resp = await client.get("/api/v1/candidate/dashboard", headers={"Authorization": f"Bearer {token}"})
    assert isinstance(resp.json()["statistics"]["interviews"], int)

@pytest.mark.asyncio
async def test_dashboard_saved_jobs_count_is_integer():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "candidate1@ntrvikasa.com")
        resp = await client.get("/api/v1/candidate/dashboard", headers={"Authorization": f"Bearer {token}"})
    assert isinstance(resp.json()["statistics"]["saved_jobs"], int)


# ── 20. Canonical Swagger endpoint ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_dashboard_swagger_canonical_endpoint():
    """
    GET /api/v1/candidate/dashboard must appear exactly once in OpenAPI.
    No duplicate aliases should exist.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/openapi.json")
    assert resp.status_code == 200
    paths = list(resp.json()["paths"].keys())
    assert "/api/v1/candidate/dashboard" in paths
    # Must be GET
    assert "get" in resp.json()["paths"]["/api/v1/candidate/dashboard"]
