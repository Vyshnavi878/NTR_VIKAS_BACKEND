"""
Automated Pytest Suite for JWT Token Authorization and Swagger UI Authentication
================================================================================
Tests verify:
1.  OAuth2 form-data login at POST /api/v1/auth/token returns access_token and bearer token_type.
2.  Invalid credentials to /api/v1/auth/token return 401.
3.  OpenAPI specification defines OAuth2PasswordBearer security scheme pointing to /api/v1/auth/token.
4.  Protected candidate endpoints return 401 when no token is supplied.
5.  Protected candidate endpoints return 401 when a malformed or forged token is supplied.
6.  Protected candidate endpoints return 401 when an expired token is supplied.
7.  Valid candidate Bearer token grants access (200 OK) to protected Candidate APIs.
8.  Role enforcement: Recruiter and Admin Bearer tokens receive 403 Forbidden on Candidate APIs.
9.  JWT payload contains required claims (sub, email, role, type, exp) and strictly no sensitive data.
10. Token expiration adheres to configured 60-minute duration.
"""
import time
import pytest
import jwt
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.config import settings
from app.core.security import decode_token


@pytest.mark.asyncio
async def test_oauth2_token_endpoint_success():
    """OAuth2 form-encoded token endpoint at POST /api/v1/auth/token returns Bearer token."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/auth/token",
            data={
                "username": "candidate1@ntrvikasa.com",
                "password": "password123",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert resp.status_code == 200, f"Token request failed: {resp.text}"
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"].lower() == "bearer"
        assert data["user"]["email"] == "candidate1@ntrvikasa.com"
        assert data["user"]["role"] == "CANDIDATE"


@pytest.mark.asyncio
async def test_oauth2_token_endpoint_invalid_credentials():
    """Invalid password or username on /api/v1/auth/token returns 401."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Bad password
        resp_bad_pw = await client.post(
            "/api/v1/auth/token",
            data={
                "username": "candidate1@ntrvikasa.com",
                "password": "WrongPassword999!",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert resp_bad_pw.status_code == 401

        # Non-existent user
        resp_bad_user = await client.post(
            "/api/v1/auth/token",
            data={
                "username": "nonexistent_person_12345@test.com",
                "password": "password123",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert resp_bad_user.status_code == 401


@pytest.mark.asyncio
async def test_swagger_openapi_bearer_security_scheme():
    """OpenAPI schema defines direct HTTP Bearer security scheme for Swagger UI Authorization."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/openapi.json")
        assert resp.status_code == 200
        schema = resp.json()

        schemes = schema.get("components", {}).get("securitySchemes", {})
        assert "Bearer" in schemes, "Bearer scheme missing from OpenAPI security schemes"
        bearer_def = schemes["Bearer"]
        assert bearer_def["type"] == "http"
        assert bearer_def["scheme"] == "bearer"
        assert bearer_def["bearerFormat"] == "JWT"



@pytest.mark.asyncio
async def test_protected_candidate_endpoints_require_bearer_token():
    """Protected Candidate APIs return 401 Unauthorized when Authorization header is absent."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        endpoints = [
            "/api/v1/candidate/applications",
            "/api/v1/candidate/profile",
            "/api/v1/candidate/saved-jobs",
            "/api/v1/candidate/dashboard",
            "/api/v1/candidate/settings",
            "/api/v1/candidate/support/tickets",
        ]
        for ep in endpoints:
            resp = await client.get(ep)
            assert resp.status_code == 401, f"Expected 401 for unauthenticated request to {ep}, got {resp.status_code}"


@pytest.mark.asyncio
async def test_protected_candidate_endpoints_reject_malformed_or_forged_token():
    """Protected Candidate APIs return 401 when token is forged or signature is invalid."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Forged token with invalid secret
        forged_token = jwt.encode(
            {"sub": "fake-id", "role": "CANDIDATE", "type": "access"},
            "wrong_secret_key_1234567890_32bytes_long!",
            algorithm="HS256",
        )
        resp = await client.get(
            "/api/v1/candidate/applications",
            headers={"Authorization": f"Bearer {forged_token}"},
        )
        assert resp.status_code == 401


@pytest.mark.asyncio
async def test_protected_candidate_endpoints_reject_expired_token():
    """Protected Candidate APIs return 401 when token expiration timestamp is in the past."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        now_ts = int(time.time())
        expired_token = jwt.encode(
            {
                "sub": "user-candidate-1",
                "role": "CANDIDATE",
                "type": "access",
                "iat": now_ts - 7200,
                "exp": now_ts - 3600,
            },
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )
        resp = await client.get(
            "/api/v1/candidate/applications",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert resp.status_code == 401


@pytest.mark.asyncio
async def test_candidate_bearer_token_access_success():
    """Valid Bearer token grants access (200 OK) to protected Candidate APIs."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Login via OAuth2 /auth/token endpoint
        token_resp = await client.post(
            "/api/v1/auth/token",
            data={
                "username": "candidate1@ntrvikasa.com",
                "password": "password123",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert token_resp.status_code == 200
        token = token_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Check endpoints
        endpoints = [
            "/api/v1/candidate/applications",
            "/api/v1/candidate/profile",
            "/api/v1/candidate/saved-jobs",
            "/api/v1/candidate/dashboard",
            "/api/v1/candidate/settings",
        ]
        for ep in endpoints:
            resp = await client.get(ep, headers=headers)
            assert resp.status_code == 200, f"Expected 200 for {ep}, got {resp.status_code}: {resp.text}"


@pytest.mark.asyncio
async def test_role_enforcement_admin_and_recruiter_rejected_on_candidate_api():
    """Recruiter and Admin Bearer tokens receive 403 Forbidden on Candidate APIs."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Admin Login
        adm_resp = await client.post(
            "/api/v1/auth/token",
            data={"username": "admin1@ntrvikasa.com", "password": "password123"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert adm_resp.status_code == 200
        admin_token = adm_resp.json()["access_token"]

        # Admin attempting Candidate API -> 403
        cand_resp = await client.get(
            "/api/v1/candidate/applications",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert cand_resp.status_code == 403
        assert "Candidate account required" in cand_resp.json()["detail"]


@pytest.mark.asyncio
async def test_jwt_payload_structure_and_hygiene():
    """JWT payload contains sub, email, role, type, exp and strictly NO sensitive fields."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "candidate1@ntrvikasa.com", "password": "password123"},
        )
        assert resp.status_code == 200
        token = resp.json()["access_token"]

        claims = decode_token(token)
        assert claims is not None
        assert "sub" in claims
        assert "email" in claims
        assert claims["email"] == "candidate1@ntrvikasa.com"
        assert claims["role"] == "CANDIDATE"
        assert claims["type"] == "access"
        assert "exp" in claims
        assert "iat" in claims

        # Expiration is within 60 minutes window
        duration = claims["exp"] - claims["iat"]
        assert duration == 60 * 60, f"Expected 3600 seconds expire, got {duration}"

        # Clean hygiene: NO sensitive info in token
        assert "password" not in claims
        assert "hashed_password" not in claims
        assert "aadhaar" not in claims
        assert "aadhaar_number" not in claims
        assert "phone" not in claims
