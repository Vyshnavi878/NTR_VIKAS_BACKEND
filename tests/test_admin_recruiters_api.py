import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


async def get_admin_token(client: AsyncClient) -> str:
    resp = await client.post("/api/v1/auth/login", json={"email": "admin1@ntrvikasa.com", "password": "password123"})
    assert resp.status_code == 200
    return resp.json()["access_token"]


@pytest.mark.asyncio
async def test_admin_list_recruiters():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        admin_token = await get_admin_token(client)
        res = await client.get(
            "/api/v1/admin/recruiters",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert "items" in data
        assert "total" in data
        assert "verified_count" in data
        assert "pending_count" in data
        assert "suspended_count" in data
        assert data["total"] >= 10
        assert len(data["items"]) > 0

        # Check fields in first item
        first = data["items"][0]
        assert "name" in first
        assert "email" in first
        assert "company" in first
        assert "verification_status" in first
        assert "account_status" in first


@pytest.mark.asyncio
async def test_admin_filter_recruiters_by_status():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        admin_token = await get_admin_token(client)
        # Verified
        res_v = await client.get(
            "/api/v1/admin/recruiters?status=VERIFIED",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res_v.status_code == 200
        for item in res_v.json()["items"]:
            assert item["verification_status"] == "VERIFIED"

        # Suspended
        res_s = await client.get(
            "/api/v1/admin/recruiters?status=SUSPENDED",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res_s.status_code == 200
        for item in res_s.json()["items"]:
            assert item["account_status"] == "SUSPENDED" or item["verification_status"] == "SUSPENDED"


@pytest.mark.asyncio
async def test_admin_filter_recruiters_by_company():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        admin_token = await get_admin_token(client)
        res = await client.get(
            "/api/v1/admin/recruiters?company=ABC Technologies Pvt Ltd",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["total"] >= 1
        for item in data["items"]:
            assert "ABC Technologies" in item["company"]


@pytest.mark.asyncio
async def test_admin_create_recruiter_existing_company():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        admin_token = await get_admin_token(client)
        import uuid
        rnd = uuid.uuid4().hex[:6]
        payload = {
            "name": f"Pooja Sharma {rnd}",
            "email": f"pooja_{rnd}@abctech.example.com",
            "phone": f"+91 99887 {rnd[:5]}",
            "designation": "Senior Campus Recruiter",
            "company_type": "EXISTING",
            "selected_company": "ABC Technologies Pvt Ltd",
            "industry": "Information Technology & Services",
            "location": "Vijayawada, NTR District",
        }
        res = await client.post(
            "/api/v1/admin/recruiters",
            json=payload,
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res.status_code == 201
        data = res.json()
        assert data["name"] == payload["name"]
        assert data["email"] == payload["email"]
        assert data["company"] == "ABC Technologies Pvt Ltd"
        assert data["verification_status"] == "VERIFIED"
        assert data["account_status"] == "ACTIVE"
        rec_id = data["id"]

        # Verify account status update (suspend then activate)
        suspend_res = await client.patch(
            f"/api/v1/admin/recruiters/{rec_id}/account-status",
            json={"status": "SUSPENDED", "reason": "Audit review temporary hold"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert suspend_res.status_code == 200
        assert suspend_res.json()["account_status"] == "SUSPENDED"

        activate_res = await client.patch(
            f"/api/v1/admin/recruiters/{rec_id}/account-status",
            json={"status": "ACTIVE"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert activate_res.status_code == 200
        assert activate_res.json()["account_status"] == "ACTIVE"


@pytest.mark.asyncio
async def test_admin_patch_job_approval():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        admin_token = await get_admin_token(client)
        # Get any job
        jobs_res = await client.get(
            "/api/v1/admin/jobs?page=1&page_size=5",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert jobs_res.status_code == 200
        jobs = jobs_res.json().get("items", [])
        if jobs:
            job_id = jobs[0]["id"]
            res = await client.patch(
                f"/api/v1/admin/jobs/{job_id}/approval",
                json={"status": "approved"},
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            assert res.status_code in [200, 400]


@pytest.mark.asyncio
async def test_admin_patch_internship_approval():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        admin_token = await get_admin_token(client)
        # Get any internship
        interns_res = await client.get(
            "/api/v1/admin/internships?page=1&page_size=5",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert interns_res.status_code == 200
        interns = interns_res.json().get("items", [])
        if interns:
            intern_id = interns[0]["id"]
            res = await client.patch(
                f"/api/v1/admin/internships/{intern_id}/approval",
                json={"status": "approved"},
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            assert res.status_code in [200, 400]


@pytest.mark.asyncio
async def test_admin_recruiter_security_and_duplicates():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Unauthenticated -> 401
        res_unauth = await client.get("/api/v1/admin/recruiters")
        assert res_unauth.status_code == 401

        admin_token = await get_admin_token(client)

        # 2. Duplicate email rejection -> 400
        dup_payload = {
            "name": "Duplicate Tester",
            "email": "recruiter1@ntrvikasa.com",  # Already in DB
            "phone": "+91 99999 11111",
            "company_type": "EXISTING",
            "selected_company": "ABC Technologies Pvt Ltd",
        }
        res_dup = await client.post(
            "/api/v1/admin/recruiters",
            json=dup_payload,
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res_dup.status_code == 400
        assert "already exists" in res_dup.json()["detail"].lower()


@pytest.mark.asyncio
async def test_admin_recruiter_export_and_actions():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        admin_token = await get_admin_token(client)
        # Fetch any recruiter
        res = await client.get(
            "/api/v1/admin/recruiters?page=1&page_size=5",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res.status_code == 200
        items = res.json()["items"]
        assert len(items) > 0
        rec_id = items[0]["id"]

        # Export
        exp_res = await client.get(
            f"/api/v1/admin/recruiters/{rec_id}/export",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert exp_res.status_code == 200
        assert "recruiter" in exp_res.json()

        # Action: verify
        ver_res = await client.post(
            f"/api/v1/admin/recruiters/{rec_id}/verify",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert ver_res.status_code == 200
        assert ver_res.json()["verification_status"] == "VERIFIED"

