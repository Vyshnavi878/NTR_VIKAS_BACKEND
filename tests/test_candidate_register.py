import pytest
import random
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_candidate_registration_and_duplicate_validation():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        rand_digits = f"{random.randint(100000, 999999)}"
        email = f"test_{rand_digits}@example.com"
        phone = f"9876{rand_digits}"
        aadhaar = f"111122{rand_digits}"

        payload = {
            "name": "Integration Test Candidate",
            "email": email,
            "phone": phone,
            "password": "password123",
            "aadhaar_number": aadhaar,
            "district": "NTR District",
            "mandal": "Vijayawada Urban",
            "village": "Bhavanipuram",
            "qualification_level": "GRADUATE",
            "terms_accepted": True,
        }

        # 1. Success Direct Registration (No OTP)
        resp = await client.post("/api/v1/auth/candidate/register", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "success"
        assert data["user"]["email"] == email
        assert "access_token" in data
        # Security Assertion: Aadhaar must NEVER be exposed in response
        assert "aadhaar_number" not in data["candidate"]
        assert aadhaar not in str(data)

        # 2. Duplicate Email Check
        dup_email_payload = dict(payload)
        dup_email_payload["phone"] = f"9875{rand_digits}"
        dup_email_payload["aadhaar_number"] = f"222233{rand_digits}"
        dup_email_resp = await client.post("/api/v1/auth/candidate/register", json=dup_email_payload)
        assert dup_email_resp.status_code == 409
        assert "Email is already registered" in dup_email_resp.json()["detail"]

        # 3. Duplicate Mobile Check
        dup_phone_payload = dict(payload)
        dup_phone_payload["email"] = f"diff_{rand_digits}@example.com"
        dup_phone_payload["aadhaar_number"] = f"333344{rand_digits}"
        dup_phone_resp = await client.post("/api/v1/auth/candidate/register", json=dup_phone_payload)
        assert dup_phone_resp.status_code == 409
        assert "Mobile number is already registered" in dup_phone_resp.json()["detail"]

        # 4. Duplicate Aadhaar Check
        dup_aadhaar_payload = dict(payload)
        dup_aadhaar_payload["email"] = f"diff2_{rand_digits}@example.com"
        dup_aadhaar_payload["phone"] = f"9874{rand_digits}"
        dup_aadhaar_resp = await client.post("/api/v1/auth/candidate/register", json=dup_aadhaar_payload)
        assert dup_aadhaar_resp.status_code == 409
        assert "Aadhaar number is already linked" in dup_aadhaar_resp.json()["detail"]

        # 5. Terms & Conditions Validation (terms_accepted=False)
        invalid_terms_payload = dict(payload)
        invalid_terms_payload["email"] = f"diff3_{rand_digits}@example.com"
        invalid_terms_payload["phone"] = f"9873{rand_digits}"
        invalid_terms_payload["aadhaar_number"] = f"444455{rand_digits}"
        invalid_terms_payload["terms_accepted"] = False
        terms_resp = await client.post("/api/v1/auth/candidate/register", json=invalid_terms_payload)
        assert terms_resp.status_code == 422

        # 6. Invalid Mandal Validation
        invalid_mandal_payload = dict(payload)
        invalid_mandal_payload["email"] = f"diff4_{rand_digits}@example.com"
        invalid_mandal_payload["phone"] = f"9872{rand_digits}"
        invalid_mandal_payload["aadhaar_number"] = f"555566{rand_digits}"
        invalid_mandal_payload["mandal"] = "NonExistentMandalXYZ"
        mandal_resp = await client.post("/api/v1/auth/candidate/register", json=invalid_mandal_payload)
        assert mandal_resp.status_code == 422


@pytest.mark.asyncio
async def test_swagger_and_no_candidate_otp_endpoints():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/openapi.json")
        assert resp.status_code == 200
        schema = resp.json()
        paths = schema["paths"]

        # Canonical endpoint exists
        assert "/api/v1/auth/candidate/register" in paths

        # No duplicate/alias candidate registration endpoint
        assert "/api/v1/auth/register/candidate" not in paths

        # No candidate OTP endpoints exist
        for path in paths:
            if "candidate" in path.lower():
                assert "otp" not in path.lower(), f"Unexpected OTP path found for candidate: {path}"
                assert "verify" not in path.lower(), f"Unexpected verify path found for candidate: {path}"
