import pytest
import random
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from app.main import app
from app.database.session import AsyncSessionLocal
from app.models.user import User
from app.core.security import decode_token, hash_password


@pytest.mark.asyncio
async def test_successful_logins_all_roles():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Candidate Login
        cand_resp = await client.post("/api/v1/auth/login", json={
            "email": "candidate1@ntrvikasa.com",
            "password": "password123",
        })
        assert cand_resp.status_code == 200
        cand_data = cand_resp.json()
        assert "access_token" in cand_data
        assert cand_data["token_type"] == "bearer"
        assert cand_data["user"]["email"] == "candidate1@ntrvikasa.com"
        assert cand_data["user"]["role"] == "CANDIDATE"
        # 11 & 12. Security Assertions: No password or Aadhaar returned
        assert "password" not in cand_data
        assert "hashed_password" not in cand_data
        assert "aadhaar" not in str(cand_data).lower()

        # 9. JWT token validation
        claims = decode_token(cand_data["access_token"])
        assert claims is not None
        assert claims["role"] == "CANDIDATE"
        assert claims["type"] == "access"

        # 2. Recruiter Login
        rec_resp = await client.post("/api/v1/auth/login", json={
            "email": "recruiter1@ntrvikasa.com",
            "password": "password123",
        })
        assert rec_resp.status_code == 200
        rec_data = rec_resp.json()
        assert rec_data["user"]["role"] == "RECRUITER"

        # 3. Admin Login
        adm_resp = await client.post("/api/v1/auth/login", json={
            "email": "admin1@ntrvikasa.com",
            "password": "password123",
        })
        assert adm_resp.status_code == 200
        adm_data = adm_resp.json()
        assert adm_data["user"]["role"] == "ADMIN"


@pytest.mark.asyncio
async def test_login_validation_and_error_handling():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 4. Invalid Password (generic error to prevent enumeration)
        bad_pwd_resp = await client.post("/api/v1/auth/login", json={
            "email": "candidate1@ntrvikasa.com",
            "password": "WrongPassword999!",
        })
        assert bad_pwd_resp.status_code == 401
        assert bad_pwd_resp.json()["detail"] == "Invalid email or password."

        # 4. Non-existent Email (must return the EXACT SAME generic error)
        bad_email_resp = await client.post("/api/v1/auth/login", json={
            "email": "nonexistent_random_user_999@test.com",
            "password": "SomePassword123!",
        })
        assert bad_email_resp.status_code == 401
        assert bad_email_resp.json()["detail"] == "Invalid email or password."

        # 5. Missing Email
        missing_email_resp = await client.post("/api/v1/auth/login", json={
            "password": "password123",
        })
        assert missing_email_resp.status_code == 422

        # 6. Missing Password
        missing_pwd_resp = await client.post("/api/v1/auth/login", json={
            "email": "candidate1@ntrvikasa.com",
        })
        assert missing_pwd_resp.status_code == 422

        # 7. Invalid Email Format
        invalid_email_resp = await client.post("/api/v1/auth/login", json={
            "email": "not-an-email",
            "password": "password123",
        })
        assert invalid_email_resp.status_code == 422


@pytest.mark.asyncio
async def test_inactive_account_login():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        rand = random.randint(100000, 999999)
        inactive_email = f"inactive_{rand}@test.com"

        # Create inactive user in MySQL
        async with AsyncSessionLocal() as session:
            inactive_user = User(
                id=f"inactive-{rand}",
                email=inactive_email,
                phone=f"9879{rand:06d}",
                hashed_password=hash_password("password123"),
                role="CANDIDATE",
                is_active=False,
                is_verified=True,
            )
            session.add(inactive_user)
            await session.commit()

        # 8. Inactive account login
        resp = await client.post("/api/v1/auth/login", json={
            "email": inactive_email,
            "password": "password123",
        })
        assert resp.status_code == 403
        assert "inactive or disabled" in resp.json()["detail"]
