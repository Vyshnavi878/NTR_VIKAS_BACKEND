import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


async def _login_admin(client: AsyncClient, email: str = "admin1@ntrvikasa.com", password: str = "password123") -> str:
    """Helper to authenticate admin and return JWT access token."""
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200
    return resp.json()["access_token"]


async def _get_role_token(role: str = "CANDIDATE") -> str:
    """Helper to create a dynamic user with specified role and return valid access token."""
    from app.core.security import create_access_token
    from app.models.user import User
    from app.database.session import AsyncSessionLocal
    import uuid
    async with AsyncSessionLocal() as session:
        u = User(
            id=str(uuid.uuid4()),
            email=f"test_{role.lower()}_{uuid.uuid4().hex[:6]}@example.com",
            phone=f"98{uuid.uuid4().int % 100000000:08d}",
            hashed_password="mock",
            role=role,
            is_active=True,
            is_verified=True,
        )
        session.add(u)
        await session.commit()
        return create_access_token(subject=u.id, role=role)


@pytest.mark.asyncio
async def test_admin_audit_logs_authorization():
    """Security tests for authentication and role requirements on /api/v1/admin/audit-logs."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Unauthenticated request -> 401
        res_unauth = await client.get("/api/v1/admin/audit-logs")
        assert res_unauth.status_code == 401

        res_export_unauth = await client.get("/api/v1/admin/audit-logs/export")
        assert res_export_unauth.status_code == 401

        # 2. Candidate token -> 403
        cand_token = await _get_role_token("CANDIDATE")
        res_cand = await client.get(
            "/api/v1/admin/audit-logs",
            headers={"Authorization": f"Bearer {cand_token}"},
        )
        assert res_cand.status_code == 403

        # 3. Recruiter token -> 403
        rec_token = await _get_role_token("RECRUITER")
        res_rec = await client.get(
            "/api/v1/admin/audit-logs",
            headers={"Authorization": f"Bearer {rec_token}"},
        )
        assert res_rec.status_code == 403


@pytest.mark.asyncio
async def test_get_admin_audit_logs_pagination_and_search():
    """Admin successfully fetches paginated audit logs with search filter."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        admin_token = await _login_admin(client, "admin1@ntrvikasa.com")

        # 1. Fetch first page
        res = await client.get(
            "/api/v1/admin/audit-logs?page=1&page_size=5",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res.status_code == 200
        data = res.json()

        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert "total_pages" in data
        assert data["page"] == 1
        assert data["page_size"] == 5
        assert len(data["items"]) <= 5

        # Check item attributes
        if data["items"]:
            item = data["items"][0]
            assert "id" in item
            assert "action" in item
            assert "actor" in item
            assert "target" in item
            assert "date" in item
            assert "time" in item
            assert "result" in item
            assert item["result"] in ["SUCCESS", "FAILED"]

        # 2. Search query
        res_search = await client.get(
            "/api/v1/admin/audit-logs?search=Login",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res_search.status_code == 200
        search_data = res_search.json()
        assert "items" in search_data
        for itm in search_data["items"]:
            assert "login" in itm["action"].lower() or "login" in itm["actor"].lower() or "login" in (itm["target"] or "").lower()


@pytest.mark.asyncio
async def test_export_admin_audit_logs_csv():
    """Admin exports audit logs as CSV stream."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        admin_token = await _login_admin(client, "admin1@ntrvikasa.com")

        res = await client.get(
            "/api/v1/admin/audit-logs/export",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res.status_code == 200
        assert "text/csv" in res.headers["content-type"]
        assert "security_audit_logs.csv" in res.headers.get("content-disposition", "")

        csv_text = res.text
        lines = csv_text.strip().split("\n")
        assert len(lines) >= 1

        # Check header
        header = lines[0].strip()
        assert "Action" in header
        assert "Admin / User" in header
        assert "Target" in header
        assert "Date" in header
        assert "Time" in header
        assert "Result" in header
