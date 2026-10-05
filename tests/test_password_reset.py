import pytest
import random
import hashlib
from datetime import datetime, timedelta, timezone
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from app.main import app
from app.database.session import AsyncSessionLocal
from app.models.user import User
from app.models.password_reset_token import PasswordResetToken
from app.services.email_service import EmailService
from app.core.security import verify_password


@pytest.mark.asyncio
async def test_forgot_password_generic_response_and_email_dispatch():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create a candidate user first
        rand = random.randint(100000, 999999)
        email = f"reset_test_{rand}@example.com"
        reg_payload = {
            "name": "Reset Test User",
            "email": email,
            "phone": f"9876{rand:06d}",
            "password": "OldPassword123!",
            "aadhaar_number": f"2222{rand:08d}",
            "district": "NTR District",
            "mandal": "Vijayawada Urban",
            "village": "Gollapudi",
            "qualification_level": "10TH",
            "terms_accepted": True,
        }
        reg_resp = await client.post("/api/v1/auth/candidate/register", json=reg_payload)
        assert reg_resp.status_code == 201

        EmailService.sent_emails_history.clear()

        # 1. Forgot password with valid email
        valid_resp = await client.post("/api/v1/auth/forgot-password", json={"email": email})
        assert valid_resp.status_code == 200
        valid_data = valid_resp.json()

        # 2. Forgot password with unknown email
        unknown_resp = await client.post("/api/v1/auth/forgot-password", json={"email": "nonexistent_email_123456@test.com"})
        assert unknown_resp.status_code == 200
        unknown_data = unknown_resp.json()

        # 3. Generic response must match exactly for both cases (no enumeration)
        assert valid_data["message"] == "If an account exists with this email, a password reset link has been sent."
        assert unknown_data["message"] == "If an account exists with this email, a password reset link has been sent."

        # 12. Sensitive values are not returned
        assert "token" not in valid_data
        assert "password" not in valid_data
        assert "token" not in unknown_data

        # 13. Email service called correctly for existing user
        assert len(EmailService.sent_emails_history) >= 1
        last_email = EmailService.sent_emails_history[-1]
        assert last_email["to"] == email
        assert last_email["subject"] == "Reset your NTR Vikasa password"
        assert last_email["has_reset_url"] is True


@pytest.mark.asyncio
async def test_password_reset_flow_and_security():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        rand = random.randint(100000, 999999)
        email = f"reset_flow_{rand}@example.com"
        reg_payload = {
            "name": "Flow Test User",
            "email": email,
            "phone": f"9865{rand:06d}",
            "password": "InitialPassword123!",
            "aadhaar_number": f"3333{rand:08d}",
            "district": "NTR District",
            "mandal": "Vijayawada Urban",
            "terms_accepted": True,
        }
        await client.post("/api/v1/auth/candidate/register", json=reg_payload)

        # Request reset
        await client.post("/api/v1/auth/forgot-password", json={"email": email})

        # 4. Reset token generation: verify stored hashed in MySQL
        async with AsyncSessionLocal() as session:
            user_stmt = select(User).where(User.email == email)
            user_res = await session.execute(user_stmt)
            user = user_res.scalar_one()

            token_stmt = select(PasswordResetToken).where(
                PasswordResetToken.user_id == user.id,
                PasswordResetToken.used_at.is_(None)
            )
            token_res = await session.execute(token_stmt)
            token_record = token_res.scalar_one()
            assert token_record is not None
            assert len(token_record.token_hash) == 64  # SHA-256 length

        # 9. Password confirmation mismatch
        mismatch_resp = await client.post("/api/v1/auth/reset-password", json={
            "token": "dummy_token_1234567890",
            "new_password": "NewSecretPassword123!",
            "confirm_password": "DifferentPassword123!",
        })
        assert mismatch_resp.status_code == 422

        # 6. Invalid token
        invalid_resp = await client.post("/api/v1/auth/reset-password", json={
            "token": "completely_invalid_token_xyz_1234567890",
            "new_password": "NewSecretPassword123!",
            "confirm_password": "NewSecretPassword123!",
        })
        assert invalid_resp.status_code == 400
        assert "Password reset link is invalid or has expired." in invalid_resp.json()["detail"]

        # 5. Token expiry test: create an expired token manually in MySQL
        raw_expired_token = f"expired_raw_token_{rand}_abcdef12345"
        expired_hash = hashlib.sha256(raw_expired_token.encode("utf-8")).hexdigest()
        async with AsyncSessionLocal() as session:
            exp_rec = PasswordResetToken(
                user_id=user.id,
                token_hash=expired_hash,
                expires_at=datetime.now(timezone.utc) - timedelta(minutes=5),
            )
            session.add(exp_rec)
            await session.commit()

        expired_resp = await client.post("/api/v1/auth/reset-password", json={
            "token": raw_expired_token,
            "new_password": "NewSecretPassword123!",
            "confirm_password": "NewSecretPassword123!",
        })
        assert expired_resp.status_code == 400
        assert "Password reset link is invalid or has expired." in expired_resp.json()["detail"]

        # 8. Successful password reset with valid token
        raw_valid_token = f"valid_raw_token_{rand}_abcdef12345"
        valid_hash = hashlib.sha256(raw_valid_token.encode("utf-8")).hexdigest()
        async with AsyncSessionLocal() as session:
            valid_rec = PasswordResetToken(
                user_id=user.id,
                token_hash=valid_hash,
                expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
            )
            session.add(valid_rec)
            await session.commit()

        success_resp = await client.post("/api/v1/auth/reset-password", json={
            "token": raw_valid_token,
            "new_password": "BrandNewPassword123!",
            "confirm_password": "BrandNewPassword123!",
        })
        assert success_resp.status_code == 200
        assert success_resp.json()["message"] == "Password reset successfully."

        # 10. Verify password is stored hashed in MySQL
        async with AsyncSessionLocal() as session:
            refreshed_user = await session.get(User, user.id)
            assert refreshed_user.hashed_password != "BrandNewPassword123!"
            assert verify_password("BrandNewPassword123!", refreshed_user.hashed_password) is True

        # 7 & 11. Already used token & token becomes unusable after reset
        reuse_resp = await client.post("/api/v1/auth/reset-password", json={
            "token": raw_valid_token,
            "new_password": "AnotherNewPassword123!",
            "confirm_password": "AnotherNewPassword123!",
        })
        assert reuse_resp.status_code == 400
        assert "Password reset link is invalid or has expired." in reuse_resp.json()["detail"]
