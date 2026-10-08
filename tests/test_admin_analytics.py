import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from app.main import app
from app.database.session import AsyncSessionLocal
from app.models.internship import AuditLog


async def _login_admin(client: AsyncClient, email: str = "admin1@ntrvikasa.com", password: str = "password123") -> str:
    """Helper to authenticate admin and return JWT access token."""
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200
    return resp.json()["access_token"]


async def _login_user(client: AsyncClient, email: str, password: str = "password123") -> str:
    """Helper to authenticate non-admin user and return JWT access token."""
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200
    return resp.json()["access_token"]


@pytest.mark.asyncio
async def test_admin_analytics_authorization():
    """Security tests: Admin required, 401 for unauthenticated, 403 for candidate & recruiter."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Unauthenticated request -> 401
        res_unauth = await client.get("/api/v1/admin/analytics")
        assert res_unauth.status_code == 401

        res_export_unauth = await client.get("/api/v1/admin/analytics/export")
        assert res_export_unauth.status_code == 401

        # 2. Candidate token -> 403
        cand_token = await _login_user(client, "candidate1@ntrvikasa.com")
        res_cand = await client.get(
            "/api/v1/admin/analytics",
            headers={"Authorization": f"Bearer {cand_token}"},
        )
        assert res_cand.status_code == 403

        # 3. Recruiter token -> 403
        rec_token = await _login_user(client, "recruiter1@ntrvikasa.com")
        res_rec = await client.get(
            "/api/v1/admin/analytics",
            headers={"Authorization": f"Bearer {rec_token}"},
        )
        assert res_rec.status_code == 403


@pytest.mark.asyncio
async def test_get_admin_analytics_success_and_structure():
    """Admin successfully fetches platform analytics with all 8 KPIs, sector demand, and monthly trajectory."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        admin_token = await _login_admin(client, "admin1@ntrvikasa.com")

        res = await client.get(
            "/api/v1/admin/analytics?period=30d",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res.status_code == 200
        data = res.json()

        # 1. Period
        assert "period" in data
        assert data["period"]["type"] == "30d"
        assert "start_date" in data["period"]
        assert "end_date" in data["period"]
        assert data["period"]["label"] == "Last 30 Days"

        # 2. KPIs
        kpis = data["kpis"]
        assert "total_platform_users" in kpis
        assert "active_candidates" in kpis
        assert "verified_recruiters" in kpis
        assert "registered_companies" in kpis
        assert "live_posted_jobs" in kpis
        assert "submitted_applications" in kpis
        assert "active_internships" in kpis
        assert "mela_registrations" in kpis

        assert isinstance(kpis["total_platform_users"], int)
        assert isinstance(kpis["live_posted_jobs"], int)

        # 3. Hiring demand by sector
        sectors = data["hiring_demand_by_sector"]
        assert isinstance(sectors, list)
        assert len(sectors) == 5
        sector_names = [s["name"] for s in sectors]
        assert "Information Technology & Software" in sector_names
        assert "Banking, Financial Services & Insurance" in sector_names
        assert "Healthcare Diagnostics & Pharma" in sector_names
        assert "E-Commerce, Logistics & Retail" in sector_names
        assert "Core Engineering & Manufacturing" in sector_names

        for s in sectors:
            assert "job_count" in s
            assert "percentage" in s
            assert "share" in s
            assert "color" in s

        # 4. Monthly placement trajectory
        trajectory = data["monthly_placement_trajectory"]
        assert isinstance(trajectory, list)
        assert len(trajectory) > 0
        for m in trajectory:
            assert "month" in m
            assert "candidates" in m
            assert "active_jobs" in m
            assert "placements" in m


@pytest.mark.asyncio
async def test_admin_analytics_periods():
    """Verify 7d, 30d, 90d, 1y period filtering."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        admin_token = await _login_admin(client, "admin1@ntrvikasa.com")

        for p, expected in [("7d", "7d"), ("30d", "30d"), ("90d", "90d"), ("1y", "1y")]:
            res = await client.get(
                f"/api/v1/admin/analytics?period={p}",
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            assert res.status_code == 200
            assert res.json()["period"]["type"] == expected


@pytest.mark.asyncio
async def test_admin_analytics_custom_date_range_and_validation():
    """Verify custom date range functionality and validation error on invalid ranges."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        admin_token = await _login_admin(client, "admin1@ntrvikasa.com")

        # 1. Valid custom date range
        res_valid = await client.get(
            "/api/v1/admin/analytics?period=custom&start_date=2026-08-01&end_date=2026-08-31",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res_valid.status_code == 200
        data = res_valid.json()
        assert data["period"]["type"] == "custom"
        assert data["period"]["start_date"] == "2026-08-01"
        assert data["period"]["end_date"] == "2026-08-31"

        # 2. Invalid date range (from > to) -> 422
        res_invalid = await client.get(
            "/api/v1/admin/analytics?period=custom&start_date=2026-09-01&end_date=2026-08-01",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res_invalid.status_code == 422
        assert "cannot be after" in res_invalid.json()["detail"].lower() or "from date" in res_invalid.json()["detail"].lower()

        # 3. Missing date range params -> 422
        res_missing = await client.get(
            "/api/v1/admin/analytics?period=custom",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res_missing.status_code == 422


@pytest.mark.asyncio
async def test_admin_analytics_export_csv_and_audit():
    """Verify CSV export and audit log generation."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        admin_token = await _login_admin(client, "admin1@ntrvikasa.com")

        res = await client.get(
            "/api/v1/admin/analytics/export?period=30d",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res.status_code == 200
        assert "text/csv" in res.headers["content-type"]
        assert "platform_analytics_report.csv" in res.headers.get("content-disposition", "")

        csv_text = res.text
        assert "PLATFORM SCALE KPIS" in csv_text
        assert "HIRING DEMAND BY INDUSTRY SECTOR" in csv_text
        assert "MONTHLY PLATFORM PLACEMENT TRAJECTORY" in csv_text
        assert "Total Platform Users" in csv_text

        # Verify audit log recorded in MySQL
        async with AsyncSessionLocal() as session:
            audit_stmt = (
                select(AuditLog)
                .where(AuditLog.action == "ADMIN_ANALYTICS_EXPORT")
                .order_by(AuditLog.timestamp.desc())
            )
            audit_result = await session.execute(audit_stmt)
            latest_audit = audit_result.scalars().first()
            assert latest_audit is not None
            assert latest_audit.action == "ADMIN_ANALYTICS_EXPORT"
            assert latest_audit.entity == "ANALYTICS"
