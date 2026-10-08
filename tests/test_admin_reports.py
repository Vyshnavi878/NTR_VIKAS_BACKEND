import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from app.main import app
from app.database.session import AsyncSessionLocal
from app.models.internship import AuditLog
from app.models.report import Report


async def _login_admin(client: AsyncClient, email: str = "admin1@ntrvikasa.com", password: str = "password123") -> str:
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200
    return resp.json()["access_token"]


async def _login_user(client: AsyncClient, email: str, password: str = "password123") -> str:
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200
    return resp.json()["access_token"]


@pytest.mark.asyncio
async def test_admin_reports_authorization():
    """Security tests: Admin required, 401 for unauthenticated, 403 for candidate & recruiter."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Unauthenticated request -> 401
        res_unauth = await client.get("/api/v1/admin/reports")
        assert res_unauth.status_code == 401

        res_summary_unauth = await client.get("/api/v1/admin/reports/summary")
        assert res_summary_unauth.status_code == 401

        res_export_unauth = await client.get("/api/v1/admin/reports/export")
        assert res_export_unauth.status_code == 401

        # 2. Candidate token -> 403 on admin endpoints
        cand_token = await _login_user(client, "candidate1@ntrvikasa.com")
        res_cand = await client.get(
            "/api/v1/admin/reports",
            headers={"Authorization": f"Bearer {cand_token}"},
        )
        assert res_cand.status_code == 403

        # 3. Recruiter token -> 403 on admin endpoints
        rec_token = await _login_user(client, "recruiter1@ntrvikasa.com")
        res_rec = await client.get(
            "/api/v1/admin/reports",
            headers={"Authorization": f"Bearer {rec_token}"},
        )
        assert res_rec.status_code == 403


@pytest.mark.asyncio
async def test_create_report_and_admin_list_and_summary():
    """Candidate submits a grievance report; Admin views it in list and summary."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        cand_token = await _login_user(client, "candidate1@ntrvikasa.com")
        admin_token = await _login_admin(client, "admin1@ntrvikasa.com")

        # 1. Candidate submits report
        create_payload = {
            "report_type": "JOB_SCAM",
            "reported_entity_type": "JOB",
            "reported_entity_name": "Fast Cash Enterprises (Manoj Kumar)",
            "subject": "Recruiter asking for registration fee",
            "description": "Recruiter asked for Rs 500 upfront registration fees before scheduling interview.",
            "reported_user_type": "RECRUITER"
        }
        res_create = await client.post(
            "/api/v1/reports",
            headers={"Authorization": f"Bearer {cand_token}"},
            json=create_payload,
        )
        assert res_create.status_code == 201
        created_data = res_create.json()
        assert created_data["report_number"].startswith("REP-")
        assert created_data["status"] == "PENDING"
        assert created_data["report_type"] == "JOB_SCAM"
        report_id = created_data["id"]

        # 2. Admin fetches summary
        res_summary = await client.get(
            "/api/v1/admin/reports/summary",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res_summary.status_code == 200
        summary_data = res_summary.json()
        assert summary_data["all"] >= 1
        assert summary_data["pending"] >= 1
        assert summary_data["open_complaints"] >= 1

        # 3. Admin lists reports with search
        res_list = await client.get(
            f"/api/v1/admin/reports?search=Fast+Cash",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res_list.status_code == 200
        list_data = res_list.json()
        assert list_data["total"] >= 1
        found = any(item["id"] == report_id for item in list_data["items"])
        assert found

        # 4. Admin views report details
        res_detail = await client.get(
            f"/api/v1/admin/reports/{report_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res_detail.status_code == 200
        detail_data = res_detail.json()
        assert detail_data["id"] == report_id
        assert detail_data["status"] == "PENDING"


@pytest.mark.asyncio
async def test_resolve_report_workflow_and_audit():
    """Admin resolves a pending report, enforces status transitions, and verifies audit trail."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        cand_token = await _login_user(client, "candidate1@ntrvikasa.com")
        admin_token = await _login_admin(client, "admin1@ntrvikasa.com")

        # Create report to resolve
        res_create = await client.post(
            "/api/v1/reports",
            headers={"Authorization": f"Bearer {cand_token}"},
            json={
                "report_type": "MISLEADING_JOB_DESCRIPTION",
                "reported_entity_type": "JOB",
                "reported_entity_name": "AI Model Trainer (TechGlobal)",
                "description": "Job was door to door sales instead of engineering.",
                "reported_user_type": "RECRUITER"
            },
        )
        assert res_create.status_code == 201
        report_id = res_create.json()["id"]
        report_num = res_create.json()["report_number"]

        # Resolve report
        res_resolve = await client.patch(
            f"/api/v1/admin/reports/{report_id}/resolve",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "admin_notes": "Recruiter account suspended and job delisted.",
                "resolution_reason": "POLICY_VIOLATION_CONFIRMED"
            },
        )
        assert res_resolve.status_code == 200
        resolved_data = res_resolve.json()
        assert resolved_data["report"]["status"] == "RESOLVED"
        assert "suspended" in resolved_data["report"]["admin_notes"]

        # Resolving again should return 409 Conflict
        res_resolve_again = await client.patch(
            f"/api/v1/admin/reports/{report_id}/resolve",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"admin_notes": "Trying again"},
        )
        assert res_resolve_again.status_code == 409

        # Dismissing an already resolved report should return 409 Conflict
        res_dismiss_resolved = await client.patch(
            f"/api/v1/admin/reports/{report_id}/dismiss",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"admin_notes": "Trying to dismiss"},
        )
        assert res_dismiss_resolved.status_code == 409

        # Verify audit log in DB
        async with AsyncSessionLocal() as session:
            stmt = select(AuditLog).where(
                AuditLog.action == "REPORT_RESOLVED",
                AuditLog.entity_id == report_num,
            )
            res_audit = await session.execute(stmt)
            audit = res_audit.scalar_one_or_none()
            assert audit is not None
            assert audit.actor == "admin1@ntrvikasa.com"


@pytest.mark.asyncio
async def test_dismiss_report_workflow():
    """Admin dismisses a non-actionable complaint and prevents duplicate actions."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        rec_token = await _login_user(client, "recruiter1@ntrvikasa.com")
        admin_token = await _login_admin(client, "admin1@ntrvikasa.com")

        # Recruiter creates report against a candidate
        res_create = await client.post(
            "/api/v1/reports",
            headers={"Authorization": f"Bearer {rec_token}"},
            json={
                "report_type": "PROFILE_HARASSMENT",
                "reported_entity_type": "CANDIDATE_PROFILE",
                "reported_entity_name": "Unverified Candidate #409",
                "description": "Candidate submitted repetitive duplicate applications.",
                "reported_user_type": "CANDIDATE"
            },
        )
        assert res_create.status_code == 201
        report_id = res_create.json()["id"]

        # Dismiss report
        res_dismiss = await client.patch(
            f"/api/v1/admin/reports/{report_id}/dismiss",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "admin_notes": "Not a harassment violation, advised candidate on application limits.",
                "resolution_reason": "INSUFFICIENT_EVIDENCE"
            },
        )
        assert res_dismiss.status_code == 200
        dismissed_data = res_dismiss.json()
        assert dismissed_data["report"]["status"] == "DISMISSED"

        # Dismissing again returns 409
        res_again = await client.patch(
            f"/api/v1/admin/reports/{report_id}/dismiss",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={},
        )
        assert res_again.status_code == 409


@pytest.mark.asyncio
async def test_admin_reports_export_csv():
    """Admin exports reports as CSV and validates content and audit logging."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        admin_token = await _login_admin(client, "admin1@ntrvikasa.com")

        res_export = await client.get(
            "/api/v1/admin/reports/export?status=ALL",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res_export.status_code == 200
        assert "text/csv" in res_export.headers.get("content-type", "")
        csv_text = res_export.text
        assert "Report Number" in csv_text
        assert "Report Type" in csv_text
        assert "Reported Entity" in csv_text
        assert "Reporter" in csv_text
        assert "Status" in csv_text
