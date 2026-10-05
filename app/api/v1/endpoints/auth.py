from typing import Optional
from fastapi import APIRouter, Depends, Form, File, UploadFile, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.schemas.auth import (
    CandidateRegisterRequest,
    CandidateRegisterResponse,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    ResetPasswordRequest,
    ResetPasswordResponse,
    LoginRequest,
    LoginResponse,
)
from app.schemas.recruiter import RecruiterRegisterResponse
from app.services.candidate_service import CandidateService
from app.services.recruiter_service import RecruiterService
from app.services.password_reset_service import PasswordResetService
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication & Password Management"])


@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate user and obtain JWT tokens",
)
async def login(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Canonical Login Endpoint (POST /api/v1/auth/login):
    1. Validates user credentials against MySQL using bcrypt hash verification.
    2. Enforces active account status.
    3. Issues cryptographically signed JWT access and refresh tokens.
    4. Returns safe user profile summary with role.
    """
    return await AuthService.authenticate_user(payload=payload, db=db)


@router.post(
    "/token",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="OAuth2 Password Flow token endpoint (Swagger UI compatibility)",
    description="Authenticate via standard OAuth2 password flow (form-encoded username and password) for Swagger UI Authorize dialog.",
)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> LoginResponse:
    """
    OAuth2 Password Request Form Endpoint (POST /api/v1/auth/token):
    Accepts standard form-data (username=email, password=password) and returns access_token.
    Enables Swagger UI 'Authorize' button to authenticate directly.
    """
    login_request = LoginRequest(
        email=form_data.username,
        password=form_data.password,
    )
    return await AuthService.authenticate_user(payload=login_request, db=db)


@router.post(
    "/candidate/register",
    response_model=CandidateRegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new Candidate directly",
)
async def register_candidate(
    payload: CandidateRegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Direct Candidate Registration Endpoint (POST /api/v1/auth/candidate/register):
    1. Validates candidate data via Pydantic v2 (Aadhaar, Phone, Email, Dropdown choices, Terms)
    2. CandidateService validates dropdown values against NTR District master lists & checks duplicates
    3. Persists records to MySQL users and candidate_profiles tables asynchronously
    4. Returns HTTP 201 created response (Aadhaar omitted for privacy)
    """
    return await CandidateService.register_candidate(payload=payload, db=db)


@router.post(
    "/recruiter/register",
    response_model=RecruiterRegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new Recruiter with company details and verification documents",
    responses={
        201: {
            "description": "Recruiter registration application submitted successfully for admin approval",
            "model": RecruiterRegisterResponse,
        },
        409: {
            "description": "Duplicate account details (work email or mobile phone already exists)",
        },
        422: {
            "description": "Validation error (invalid field formats, unapproved dropdown choices, or file type/size limits)",
        },
        500: {
            "description": "Unexpected server error",
        },
    },
)
async def register_recruiter(
    recruiter_name: str = Form(..., description="Recruiter / HR Full Name"),
    designation: str = Form(..., description="Official Corporate Designation"),
    work_email: str = Form(..., description="Corporate/Work Email Address"),
    mobile_phone: str = Form(..., description="10-digit Indian Mobile Phone"),
    password: str = Form(..., description="Create account password (min 8 characters)"),
    confirm_password: str = Form(..., description="Confirm account password"),
    company_name: str = Form(..., description="Company / Organization Name"),
    company_website: str = Form(..., description="Official Company Website URL"),
    corporate_email: Optional[str] = Form(None, description="Optional Corporate General Email"),
    company_phone: Optional[str] = Form(None, description="Optional Company Landline/Phone"),
    primary_industry: str = Form(..., description="Industry selected from approved options"),
    company_size: str = Form(..., description="Company size tier selected from approved options"),
    headquarters_city_state: str = Form(..., description="Headquarters District/City selected from approved list"),
    registered_office_address: str = Form(..., description="Full Registered Office Physical Address"),
    company_description: str = Form(..., description="Brief Company Overview & Description"),
    terms_accepted: str = Form(..., description="Consent to Terms & Conditions and Privacy Policy (true/false)"),
    incorporation_document: Optional[UploadFile] = File(None, description="Certificate of Incorporation / CIN / GST Proof (PDF/JPG/PNG max 5MB)"),
    recruiter_authorization_document: Optional[UploadFile] = File(None, description="Authorized Recruiter Official ID / Letter (PDF/JPG/PNG max 5MB)"),
    company_logo: Optional[UploadFile] = File(None, description="Optional Company Official Logo (PNG/SVG/JPG max 2MB)"),
    db: AsyncSession = Depends(get_db),
):
    """
    Canonical Recruiter Registration Endpoint (POST /api/v1/auth/recruiter/register):
    Accepts multipart/form-data for 3-step recruiter signup:
    - Step 1: Recruiter Contact Info & Credentials
    - Step 2: Company Details & Approved Dropdown Values
    - Step 3: Mandatory Verification Documents & Terms Acceptance
    Creates recruiter profile in MySQL with initial status PENDING_APPROVAL.
    """
    is_terms_accepted = str(terms_accepted).strip().lower() in ("true", "1", "yes")

    return await RecruiterService.register_recruiter(
        recruiter_name=recruiter_name,
        designation=designation,
        work_email=work_email,
        mobile_phone=mobile_phone,
        password=password,
        confirm_password=confirm_password,
        company_name=company_name,
        company_website=company_website,
        corporate_email=corporate_email,
        company_phone=company_phone,
        primary_industry=primary_industry,
        company_size=company_size,
        headquarters_city_state=headquarters_city_state,
        registered_office_address=registered_office_address,
        company_description=company_description,
        terms_accepted=is_terms_accepted,
        incorporation_document=incorporation_document,
        recruiter_authorization_document=recruiter_authorization_document,
        company_logo=company_logo,
        db=db,
    )


@router.post(
    "/forgot-password",
    response_model=ForgotPasswordResponse,
    status_code=status.HTTP_200_OK,
    summary="Request a password reset link sent to email",
)
async def forgot_password(
    payload: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Forgot Password Request (POST /api/v1/auth/forgot-password):
    1. Validates email format and normalizes input.
    2. Searches for user in MySQL users table.
    3. Generates a cryptographically secure random token, hashes it, and stores in MySQL with 30-min expiry.
    4. Dispatches password reset email containing one-time link.
    5. Returns generic 200 response to prevent email enumeration.
    """
    return await PasswordResetService.request_password_reset(payload=payload, db=db)


@router.post(
    "/reset-password",
    response_model=ResetPasswordResponse,
    status_code=status.HTTP_200_OK,
    summary="Reset password using one-time token from email link",
)
async def reset_password(
    payload: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Reset Password Endpoint (POST /api/v1/auth/reset-password):
    1. Hashes incoming token and queries MySQL password_reset_tokens table.
    2. Verifies token is valid, unused, and not expired.
    3. Hashes new password securely with bcrypt and updates user record.
    4. Marks token as used (single-use enforcement).
    5. Returns success response.
    """
    return await PasswordResetService.reset_password(payload=payload, db=db)
