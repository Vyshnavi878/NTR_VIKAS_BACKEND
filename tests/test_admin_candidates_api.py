import pytest
import uuid
import random
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.security import create_access_token


async def get_admin_token(client: AsyncClient) -> str:
    resp = await client.post("/api/v1/auth/login", json={"email": "admin1@ntrvikasa.com", "password": "password123"})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def get_candidate_token() -> str:
    return create_access_token(subject="00091ae8-0252-45cc-8303-bfb75667e5f7", role="CANDIDATE")


def generate_credentials():
    rnd_num = str(random.randint(10000000, 99999999))
    uid = str(uuid.uuid4())[:6]
    email = f"test_cand_{uid}_{rnd_num}@example.com"
    phone = f"984{rnd_num[:7]}"
    aadhaar = f"1234{rnd_num}"  # exactly 12 digits
    return email, phone, aadhaar


@pytest.mark.asyncio
async def test_admin_list_candidates():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        admin_token = await get_admin_token(client)
        headers = {"Authorization": f"Bearer {admin_token}"}
        res = await client.get("/api/v1/admin/candidates?page=1&page_size=10", headers=headers)
        assert res.status_code == 200, res.text
        data = res.json()
        assert "items" in data
        assert "total" in data
        assert "total_registered" in data
        assert "placed_students" in data
        assert isinstance(data["items"], list)
        if data["items"]:
            first = data["items"][0]
            assert "aadhaar_masked" in first
            assert "XXXX" in first["aadhaar_masked"]
            assert "hashed_password" not in first


@pytest.mark.asyncio
async def test_admin_create_candidate_success():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        admin_token = await get_admin_token(client)
        headers = {"Authorization": f"Bearer {admin_token}"}

        email, phone, aadhaar = generate_credentials()

        payload = {
            "full_name": "Ramesh Babu Test",
            "email": email,
            "mobile_number": phone,
            "gender": "Male",
            "aadhaar_number": aadhaar,
            "referred_by": "Admin User (State Operations)",
            "placement_status": "NOT_PLACED",
        }

        res = await client.post("/api/v1/admin/candidates", json=payload, headers=headers)
        assert res.status_code == 201, res.text
        data = res.json()
        assert data["name"] == "Ramesh Babu Test"
        assert data["email"] == email.lower()
        assert data["placement_status"] == "NOT_PLACED"
        assert "aadhaar_masked" in data
        assert data["aadhaar_masked"].endswith(aadhaar[-4:])
        assert "password" not in data


@pytest.mark.asyncio
async def test_admin_create_candidate_with_placement():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        admin_token = await get_admin_token(client)
        headers = {"Authorization": f"Bearer {admin_token}"}

        email, phone, aadhaar = generate_credentials()

        payload = {
            "full_name": "Priya Sharma Test",
            "email": email,
            "mobile_number": phone,
            "gender": "Female",
            "aadhaar_number": aadhaar,
            "referred_by": "District Nodal Officer (Vijayawada)",
            "placement_status": "PLACED",
            "placed_company": "TechCorp India",
            "placed_role": "Associate Engineer",
            "placed_salary": "₹3,80,000 / year",
        }

        res = await client.post("/api/v1/admin/candidates", json=payload, headers=headers)
        assert res.status_code == 201, res.text
        data = res.json()
        assert data["placement_status"] == "PLACED"
        assert data["placed_company"] == "TechCorp India"
        assert data["placed_role"] == "Associate Engineer"
        assert data["placed_salary"] == "₹3,80,000 / year"


@pytest.mark.asyncio
async def test_admin_create_candidate_custom_referrer():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        admin_token = await get_admin_token(client)
        headers = {"Authorization": f"Bearer {admin_token}"}

        email, phone, aadhaar = generate_credentials()

        # Missing custom referrer when Other is selected should return 422
        payload_bad = {
            "full_name": "Anil Kumar Test",
            "email": email,
            "mobile_number": phone,
            "gender": "Male",
            "aadhaar_number": aadhaar,
            "referred_by": "Other",
            "custom_referrer": "",
        }

        res_bad = await client.post("/api/v1/admin/candidates", json=payload_bad, headers=headers)
        assert res_bad.status_code == 422, res_bad.text

        # Providing custom referrer should succeed
        payload_good = {
            **payload_bad,
            "custom_referrer": "Kondapalli Gram Panchayat Placement Desk",
        }
        res_good = await client.post("/api/v1/admin/candidates", json=payload_good, headers=headers)
        assert res_good.status_code == 201, res_good.text
        data = res_good.json()
        assert data["custom_referrer"] == "Kondapalli Gram Panchayat Placement Desk"


@pytest.mark.asyncio
async def test_admin_create_candidate_duplicate_rejection():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        admin_token = await get_admin_token(client)
        headers = {"Authorization": f"Bearer {admin_token}"}

        email, phone, aadhaar = generate_credentials()

        payload = {
            "full_name": "Duplicate Tester",
            "email": email,
            "mobile_number": phone,
            "gender": "Male",
            "aadhaar_number": aadhaar,
            "referred_by": "Admin User (State Operations)",
        }

        res1 = await client.post("/api/v1/admin/candidates", json=payload, headers=headers)
        assert res1.status_code == 201

        # Duplicate email
        payload_dup_email = {
            **payload,
            "mobile_number": "9848999999",
            "aadhaar_number": "123456789999",
        }
        res2 = await client.post("/api/v1/admin/candidates", json=payload_dup_email, headers=headers)
        assert res2.status_code == 409
        assert "already registered" in res2.text

        # Duplicate Aadhaar
        payload_dup_aadhaar = {
            **payload,
            "email": f"different_{email}",
            "mobile_number": "9848888888",
        }
        res3 = await client.post("/api/v1/admin/candidates", json=payload_dup_aadhaar, headers=headers)
        assert res3.status_code == 409
        assert "already linked" in res3.text


@pytest.mark.asyncio
async def test_admin_update_candidate_placement():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        admin_token = await get_admin_token(client)
        headers = {"Authorization": f"Bearer {admin_token}"}

        email, phone, aadhaar = generate_credentials()

        payload = {
            "full_name": "Placement Update Candidate",
            "email": email,
            "mobile_number": phone,
            "gender": "Male",
            "aadhaar_number": aadhaar,
            "referred_by": "Admin User (State Operations)",
            "placement_status": "NOT_PLACED",
        }

        create_res = await client.post("/api/v1/admin/candidates", json=payload, headers=headers)
        assert create_res.status_code == 201
        cand_id = create_res.json()["id"]

        # Update placement
        update_payload = {
            "placement_status": "PLACED",
            "placed_company": "Wipro Regional Hub",
            "placed_role": "Junior Analyst",
            "placed_salary": "₹3,40,000 / year",
            "placed_date": "2026-10-09",
        }
        patch_res = await client.patch(
            f"/api/v1/admin/candidates/{cand_id}/placement",
            json=update_payload,
            headers=headers,
        )
        assert patch_res.status_code == 200, patch_res.text
        updated = patch_res.json()
        assert updated["placement_status"] == "PLACED"
        assert updated["placed_company"] == "Wipro Regional Hub"
        assert updated["placed_role"] == "Junior Analyst"


@pytest.mark.asyncio
async def test_admin_candidate_security():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # No auth
        res_no_auth = await client.get("/api/v1/admin/candidates")
        assert res_no_auth.status_code == 401

        # Candidate token attempting admin endpoint
        cand_token = get_candidate_token()
        res_forbidden = await client.get(
            "/api/v1/admin/candidates",
            headers={"Authorization": f"Bearer {cand_token}"},
        )
        assert res_forbidden.status_code == 403
