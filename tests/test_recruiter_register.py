"""
Recruiter Registration Integration Tests
POST /api/v1/auth/recruiter/register

Tests cover:
1. Missing mandatory document - 422
2. Invalid work email format - 422
3. Invalid mobile phone - 422
4. Short password - 422
5. Password mismatch - 422
6. Terms not accepted - 422
7. Invalid industry dropdown - 422
8. Invalid company size dropdown - 422
9. Invalid headquarters city - 422
10. Swagger contains canonical endpoint only
"""
import io
import pytest
import random
from httpx import AsyncClient, ASGITransport
from app.main import app


def _make_valid_pdf() -> bytes:
    """Returns minimal valid PDF bytes."""
    return b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>
endobj
xref
0 4
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
trailer
<< /Size 4 /Root 1 0 R >>
startxref
190
%%EOF"""


def _make_valid_png() -> bytes:
    """Returns minimal valid PNG header bytes (1x1 black pixel)."""
    return (
        b"\x89PNG\r\n\x1a\n"
        b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02"
        b"\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00"
        b"\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
    )


def _build_valid_form(rand_digits: str) -> dict:
    """Build a complete valid multipart form payload."""
    return {
        "recruiter_name": "HR Manager Test",
        "designation": "Head of Talent Acquisition",
        "work_email": f"recruiter_test_{rand_digits}@testcompany.com",
        "mobile_phone": f"9876{rand_digits}",
        "password": "SecurePass@123",
        "confirm_password": "SecurePass@123",
        "company_name": f"TestCorp Solutions {rand_digits}",
        "company_website": "https://testcorp.com",
        "primary_industry": "Information Technology",
        "company_size": "51-200 employees (Mid-sized)",
        "headquarters_city_state": "Visakhapatnam",
        "registered_office_address": "Plot 42, HITEC City, Visakhapatnam - 530001",
        "company_description": "We are a digital product studio building enterprise cloud solutions.",
        "terms_accepted": "true",
    }


def _build_files(
    include_coi: bool = True,
    include_auth: bool = True,
    include_logo: bool = False,
    pdf_bytes: bytes = None,
    png_bytes: bytes = None,
) -> list[tuple]:
    """Build a files list for httpx multipart."""
    files = []
    pdf = pdf_bytes or _make_valid_pdf()
    png = png_bytes or _make_valid_png()

    if include_coi:
        files.append(
            ("incorporation_document", ("incorporation.pdf", io.BytesIO(pdf), "application/pdf"))
        )
    if include_auth:
        files.append(
            ("recruiter_authorization_document", ("auth_letter.pdf", io.BytesIO(pdf), "application/pdf"))
        )
    if include_logo:
        files.append(
            ("company_logo", ("logo.png", io.BytesIO(png), "image/png"))
        )
    return files


@pytest.mark.asyncio
async def test_recruiter_registration_missing_coi_document():
    """Missing Certificate of Incorporation must return 422."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        rand_digits = f"{random.randint(100000, 999999)}"
        form = _build_valid_form(rand_digits)

        # Only send auth letter, NOT COI
        files = _build_files(include_coi=False, include_auth=True)

        resp = await client.post(
            "/api/v1/auth/recruiter/register",
            data=form,
            files=files,
        )
        assert resp.status_code == 422, f"Expected 422 for missing COI, got {resp.status_code}: {resp.text}"


@pytest.mark.asyncio
async def test_recruiter_registration_missing_authorization_document():
    """Missing Authorization Letter must return 422."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        rand_digits = f"{random.randint(100000, 999999)}"
        form = _build_valid_form(rand_digits)

        # Only send COI, NOT auth letter
        files = _build_files(include_coi=True, include_auth=False)

        resp = await client.post(
            "/api/v1/auth/recruiter/register",
            data=form,
            files=files,
        )
        assert resp.status_code == 422, f"Expected 422 for missing auth letter, got {resp.status_code}: {resp.text}"


@pytest.mark.asyncio
async def test_recruiter_registration_invalid_email():
    """Invalid work email format must return 422."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        rand_digits = f"{random.randint(100000, 999999)}"
        form = _build_valid_form(rand_digits)
        form["work_email"] = "not-a-valid-email"

        files = _build_files()
        resp = await client.post(
            "/api/v1/auth/recruiter/register",
            data=form,
            files=files,
        )
        assert resp.status_code == 422, f"Expected 422 for invalid email, got {resp.status_code}: {resp.text}"


@pytest.mark.asyncio
async def test_recruiter_registration_invalid_mobile():
    """Invalid mobile phone must return 422."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        rand_digits = f"{random.randint(100000, 999999)}"
        form = _build_valid_form(rand_digits)
        form["mobile_phone"] = "12345"  # Invalid: not 10 digits starting with 6-9

        files = _build_files()
        resp = await client.post(
            "/api/v1/auth/recruiter/register",
            data=form,
            files=files,
        )
        assert resp.status_code == 422, f"Expected 422 for invalid mobile, got {resp.status_code}: {resp.text}"


@pytest.mark.asyncio
async def test_recruiter_registration_short_password():
    """Password shorter than 8 characters must return 422."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        rand_digits = f"{random.randint(100000, 999999)}"
        form = _build_valid_form(rand_digits)
        form["password"] = "abc"
        form["confirm_password"] = "abc"

        files = _build_files()
        resp = await client.post(
            "/api/v1/auth/recruiter/register",
            data=form,
            files=files,
        )
        assert resp.status_code == 422, f"Expected 422 for short password, got {resp.status_code}: {resp.text}"


@pytest.mark.asyncio
async def test_recruiter_registration_password_mismatch():
    """Mismatched confirm password must return 422."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        rand_digits = f"{random.randint(100000, 999999)}"
        form = _build_valid_form(rand_digits)
        form["confirm_password"] = "DifferentPassword999"

        files = _build_files()
        resp = await client.post(
            "/api/v1/auth/recruiter/register",
            data=form,
            files=files,
        )
        assert resp.status_code == 422, f"Expected 422 for password mismatch, got {resp.status_code}: {resp.text}"


@pytest.mark.asyncio
async def test_recruiter_registration_terms_not_accepted():
    """Submitting with terms_accepted=false must return 422."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        rand_digits = f"{random.randint(100000, 999999)}"
        form = _build_valid_form(rand_digits)
        form["terms_accepted"] = "false"

        files = _build_files()
        resp = await client.post(
            "/api/v1/auth/recruiter/register",
            data=form,
            files=files,
        )
        assert resp.status_code == 422, f"Expected 422 for terms not accepted, got {resp.status_code}: {resp.text}"


@pytest.mark.asyncio
async def test_recruiter_registration_invalid_industry_dropdown():
    """Unapproved industry string must return 422."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        rand_digits = f"{random.randint(100000, 999999)}"
        form = _build_valid_form(rand_digits)
        form["primary_industry"] = "Space Tourism Industry XYZ"

        files = _build_files()
        resp = await client.post(
            "/api/v1/auth/recruiter/register",
            data=form,
            files=files,
        )
        assert resp.status_code == 422, f"Expected 422 for invalid industry, got {resp.status_code}: {resp.text}"
        assert "Invalid Primary Industry" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_recruiter_registration_invalid_company_size_dropdown():
    """Unapproved company size must return 422."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        rand_digits = f"{random.randint(100000, 999999)}"
        form = _build_valid_form(rand_digits)
        form["company_size"] = "50-200"  # Old non-canonical value

        files = _build_files()
        resp = await client.post(
            "/api/v1/auth/recruiter/register",
            data=form,
            files=files,
        )
        assert resp.status_code == 422, f"Expected 422 for invalid company size, got {resp.status_code}: {resp.text}"
        assert "Invalid Company Size" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_recruiter_registration_invalid_headquarters_city():
    """Invalid headquarters city/state must return 422."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        rand_digits = f"{random.randint(100000, 999999)}"
        form = _build_valid_form(rand_digits)
        form["headquarters_city_state"] = "Mumbai"  # Not in AP districts

        files = _build_files()
        resp = await client.post(
            "/api/v1/auth/recruiter/register",
            data=form,
            files=files,
        )
        assert resp.status_code == 422, f"Expected 422 for invalid HQ city, got {resp.status_code}: {resp.text}"
        assert "Invalid Headquarters City" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_recruiter_registration_swagger_canonical_endpoint():
    """
    Swagger should include exactly ONE recruiter register endpoint:
    POST /api/v1/auth/recruiter/register
    No alias /api/v1/auth/register/recruiter should exist.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/openapi.json")
        assert resp.status_code == 200
        schema = resp.json()
        paths = list(schema["paths"].keys())

        # Canonical endpoint must exist
        assert "/api/v1/auth/recruiter/register" in paths, \
            f"Canonical endpoint not found in paths: {paths}"

        # Alias must NOT exist
        assert "/api/v1/auth/register/recruiter" not in paths, \
            f"Stale alias endpoint found in paths: {paths}"

        # Verify it is a POST
        assert "post" in schema["paths"]["/api/v1/auth/recruiter/register"]
