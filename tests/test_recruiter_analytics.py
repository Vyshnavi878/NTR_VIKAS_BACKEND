"""
Recruiter Hiring Analytics Integration Tests
GET /api/v1/recruiter/analytics
GET /api/v1/recruiter/analytics/export

Tests cover:
1.  Unauthenticated request to /analytics returns 401
2.  Candidate token returns 403 Forbidden
3.  Admin token returns 403 Forbidden
4.  Authenticated recruiter gets 200 with complete response structure
5.  Preset ranges (7d, 30d, 90d, 1y) return 200 with appropriate bounds
6.  Invalid preset range returns 422 Unprocessable Entity
7.  Custom date range with valid start_date and end_date returns 200
8.  Inverted custom date range (start_date > end_date) returns 422
9.  Invalid date string format returns 422
10. Unauthenticated request to /analytics/export returns 401
11. Candidate token to /analytics/export returns 403
12. Authenticated recruiter gets 200 CSV export with proper headers and content
13. CSV export with custom date range returns 200
14. Recruiter isolation: Recruiter 2 sees only their own metrics (0 jobs/applications)
15. Zero applications safe calculation (no ZeroDivisionError, 0.0% conversion)
16. OpenAPI schema contains both analytics endpoints with documentation
"""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


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


# ── 1. Unauthenticated ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_recruiter_analytics_unauthenticated_returns_401():
    """No token → 401 Unauthorized."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/recruiter/analytics")
    assert resp.status_code == 401


# ── 2. Candidate Role Forbidden ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_recruiter_analytics_candidate_role_returns_403():
    """Candidate JWT must not access recruiter analytics."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "candidate1@ntrvikasa.com", role="CANDIDATE")
        resp = await client.get(
            "/api/v1/recruiter/analytics",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 403
    assert "Recruiter account required" in resp.json()["detail"]


# ── 3. Admin Role Forbidden ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_recruiter_analytics_admin_role_returns_403():
    """Admin JWT must not access recruiter analytics directly."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "admin1@ntrvikasa.com", role="ADMIN")
        resp = await client.get(
            "/api/v1/recruiter/analytics",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 403


# ── 4. Happy Path: 200 with full structure (default 30d) ───────────────────────

@pytest.mark.asyncio
async def test_recruiter_analytics_returns_200_default_30d():
    """Recruiter gets 200 with complete response structure."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "recruiter1@ntrvikasa.com", role="RECRUITER")
        resp = await client.get(
            "/api/v1/recruiter/analytics",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    data = resp.json()

    # Top-level keys verification
    required_keys = (
        "date_range",
        "summary",
        "recruitment_funnel",
        "application_velocity",
        "job_posting_performance",
        "candidate_sourcing",
        "job_mela_insight",
    )
    for key in required_keys:
        assert key in data, f"Missing top-level key: {key}"

    # Date Range validation
    dr = data["date_range"]
    assert dr["type"] == "30d"
    assert "start_date" in dr
    assert "end_date" in dr

    # Summary KPIs validation
    summary = data["summary"]
    for field in ("total_applications", "shortlist_conversion", "interviews_conducted", "average_time_to_hire_days"):
        assert field in summary, f"Missing summary metric: {field}"
        assert isinstance(summary[field], (int, float))

    # Recruitment Funnel validation
    funnel = data["recruitment_funnel"]
    for field in ("applications_received", "profile_shortlisted", "technical_interviews", "final_offers_hires"):
        assert field in funnel, f"Missing funnel metric: {field}"
        assert isinstance(funnel[field], int)

    # Application Velocity validation
    velocity = data["application_velocity"]
    assert isinstance(velocity, list)
    if velocity:
        first_v = velocity[0]
        assert "period" in first_v
        assert "total_applicants" in first_v
        assert "hired_candidates" in first_v

    # Job Posting Performance validation
    perf = data["job_posting_performance"]
    assert isinstance(perf, list)
    for item in perf:
        assert "job_id" in item
        assert "job_title" in item
        assert "applicants" in item
        assert "shortlisted" in item
        assert "interviews" in item
        assert "status" in item

    # Candidate Sourcing Breakdown validation
    sourcing = data["candidate_sourcing"]
    assert isinstance(sourcing, list)
    assert len(sourcing) == 4
    for item in sourcing:
        assert "source" in item
        assert "applicants" in item
        assert "percentage" in item
        assert "color" in item

    # Job Mela Insight validation
    insight = data["job_mela_insight"]
    assert "enabled" in insight
    assert "message" in insight


# ── 5. Preset Ranges ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.parametrize("preset", ["7d", "30d", "90d", "1y"])
async def test_recruiter_analytics_preset_ranges(preset):
    """Preset date ranges return 200 with appropriate range type."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "recruiter1@ntrvikasa.com", role="RECRUITER")
        resp = await client.get(
            f"/api/v1/recruiter/analytics?date_range={preset}",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["date_range"]["type"] == preset


# ── 6. Invalid Preset Range ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_recruiter_analytics_invalid_preset_range_returns_422():
    """Invalid date_range query parameter returns 422."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "recruiter1@ntrvikasa.com", role="RECRUITER")
        resp = await client.get(
            "/api/v1/recruiter/analytics?date_range=invalid_range",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 422
    assert "Invalid date_range" in resp.json()["detail"]


# ── 7. Custom Date Range Valid ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_recruiter_analytics_custom_date_range_valid():
    """Custom start_date and end_date return 200 with type 'custom'."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "recruiter1@ntrvikasa.com", role="RECRUITER")
        resp = await client.get(
            "/api/v1/recruiter/analytics?date_range=custom&start_date=2026-01-01&end_date=2026-10-05",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    dr = resp.json()["date_range"]
    assert dr["type"] == "custom"
    assert dr["start_date"] == "2026-01-01"
    assert dr["end_date"] == "2026-10-05"


# ── 8. Inverted Custom Date Range ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_recruiter_analytics_custom_date_range_inverted_returns_422():
    """start_date after end_date returns 422 Unprocessable Entity."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "recruiter1@ntrvikasa.com", role="RECRUITER")
        resp = await client.get(
            "/api/v1/recruiter/analytics?date_range=custom&start_date=2026-10-05&end_date=2026-01-01",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 422
    assert "start_date cannot be later than end_date" in resp.json()["detail"]


# ── 9. Invalid Custom Date Format ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_recruiter_analytics_custom_date_range_invalid_format_returns_422():
    """Invalid date string format returns 422."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "recruiter1@ntrvikasa.com", role="RECRUITER")
        resp = await client.get(
            "/api/v1/recruiter/analytics?date_range=custom&start_date=01-01-2026&end_date=2026-10-05",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 422
    assert "Invalid date format" in resp.json()["detail"]


# ── 10. Export Unauthenticated ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_recruiter_analytics_export_unauthenticated_returns_401():
    """No token on /export → 401 Unauthorized."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/recruiter/analytics/export")
    assert resp.status_code == 401


# ── 11. Export Candidate Role Forbidden ────────────────────────────────────────

@pytest.mark.asyncio
async def test_recruiter_analytics_export_candidate_role_returns_403():
    """Candidate token on /export → 403 Forbidden."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "candidate1@ntrvikasa.com", role="CANDIDATE")
        resp = await client.get(
            "/api/v1/recruiter/analytics/export",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 403


# ── 12. Export Happy Path: CSV download ────────────────────────────────────────

@pytest.mark.asyncio
async def test_recruiter_analytics_export_returns_csv():
    """Authenticated recruiter gets 200 CSV with report sections."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "recruiter1@ntrvikasa.com", role="RECRUITER")
        resp = await client.get(
            "/api/v1/recruiter/analytics/export?date_range=30d",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    assert "Content-Disposition" in resp.headers
    assert "attachment; filename=" in resp.headers["Content-Disposition"]
    assert ".csv" in resp.headers["Content-Disposition"]

    content = resp.text
    # Verify CSV sections exist
    assert "NTR VIKASA - RECRUITER HIRING & RECRUITMENT ANALYTICS REPORT" in content
    assert "Date Range Type,30d" in content
    assert "1. SUMMARY PERFORMANCE METRICS" in content
    assert "Total Applications" in content
    assert "Shortlist Conversion Rate (%)," in content
    assert "2. RECRUITMENT FUNNEL" in content
    assert "3. JOB POSTING PERFORMANCE" in content
    assert "4. APPLICATION VELOCITY & HIRES TREND" in content
    assert "5. CANDIDATE SOURCING BREAKDOWN" in content


# ── 13. Export with Custom Range ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_recruiter_analytics_export_with_custom_range():
    """Export with custom start_date and end_date returns 200 CSV."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "recruiter1@ntrvikasa.com", role="RECRUITER")
        resp = await client.get(
            "/api/v1/recruiter/analytics/export?date_range=custom&start_date=2026-01-01&end_date=2026-10-05",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    assert "Date Range Type,custom" in resp.text
    assert "Start Date,2026-01-01" in resp.text
    assert "End Date,2026-10-05" in resp.text


# ── 14. Recruiter Data Isolation ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_recruiter_analytics_data_isolation():
    """Recruiter 2 does not see Recruiter 1's analytics data."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "recruiter2@ntrvikasa.com", role="RECRUITER")
        resp = await client.get(
            "/api/v1/recruiter/analytics?date_range=1y",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    data = resp.json()

    # Recruiter 2 has zero jobs and zero applications
    assert data["summary"]["total_applications"] == 0
    assert data["summary"]["shortlist_conversion"] == 0.0
    assert data["summary"]["interviews_conducted"] == 0
    assert data["recruitment_funnel"]["applications_received"] == 0
    assert len(data["job_posting_performance"]) == 0

    # Sourcing items exist for canonical categories with 0 applicants and 0.0%
    for item in data["candidate_sourcing"]:
        assert item["applicants"] == 0
        assert item["percentage"] == 0.0


# ── 15. Zero Applications Safe Calculation ─────────────────────────────────────

@pytest.mark.asyncio
async def test_recruiter_analytics_zero_applications_safe():
    """When a date range has 0 applications, calculations remain safe without ZeroDivisionError."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "recruiter1@ntrvikasa.com", role="RECRUITER")
        # Far past date range with no applications
        resp = await client.get(
            "/api/v1/recruiter/analytics?date_range=custom&start_date=2020-01-01&end_date=2020-01-02",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["summary"]["total_applications"] == 0
    assert data["summary"]["shortlist_conversion"] == 0.0
    assert data["summary"]["average_time_to_hire_days"] == 0


# ── 16. OpenAPI / Swagger Verification ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_recruiter_analytics_in_openapi():
    """OpenAPI schema documents both /analytics and /analytics/export with Bearer security."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/openapi.json")
    assert resp.status_code == 200
    schema = resp.json()

    paths = schema["paths"]
    assert "/api/v1/recruiter/analytics" in paths
    assert "get" in paths["/api/v1/recruiter/analytics"]

    assert "/api/v1/recruiter/analytics/export" in paths
    assert "get" in paths["/api/v1/recruiter/analytics/export"]

    # Verify security requirement is present
    analytics_get = paths["/api/v1/recruiter/analytics"]["get"]
    assert "security" in analytics_get
    export_get = paths["/api/v1/recruiter/analytics/export"]["get"]
    assert "security" in export_get
