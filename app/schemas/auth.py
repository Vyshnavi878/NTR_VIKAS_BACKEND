import re
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict

from app.core.constants import NTR_MANDALS, REFERENCE_ADMINS, DISTRICT_LOCATIONS


class CandidateRegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=150, description="Full name of candidate")
    email: EmailStr = Field(..., description="Valid personal email address")
    phone: str = Field(..., description="10-digit Indian mobile number")
    password: str = Field(..., min_length=6, max_length=100, description="Account password")
    aadhaar_number: str = Field(..., description="12-digit Aadhaar number")

    # Dropdown Selected Values
    district: str = Field(
        default="NTR District",
        description="District selected from frontend dropdown"
    )
    mandal: str = Field(
        default="Vijayawada Urban",
        description="Mandal selected from NTR District mandals dropdown"
    )
    village: Optional[str] = Field(
        default=None,
        description="Village / locality / ward"
    )
    qualification_level: str = Field(
        default="10TH",
        description="Qualification tier selected from dropdown (10TH, INTER, UG, PG, etc.)"
    )
    reference_admin: Optional[str] = Field(
        default="Direct Student Self-Registration",
        description="Referring officer or authority selected from dropdown"
    )
    terms_accepted: bool = Field(
        default=True,
        description="Whether candidate agreed to Terms & Conditions and Privacy Policy"
    )

    @field_validator("terms_accepted")
    @classmethod
    def validate_terms(cls, v: bool) -> bool:
        if not v:
            raise ValueError("Terms & Conditions and Privacy Policy must be accepted.")
        return v

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        clean = re.sub(r"[\s\-()]", "", v)
        if not re.match(r"^[6-9]\d{9}$", clean):
            raise ValueError("Phone number must be a valid 10-digit Indian mobile number starting with 6-9")
        return clean

    @field_validator("aadhaar_number")
    @classmethod
    def validate_aadhaar(cls, v: str) -> str:
        clean = re.sub(r"[\s\-]", "", v)
        if not re.match(r"^\d{12}$", clean):
            raise ValueError("Aadhaar number must be exactly 12 numeric digits")
        return clean

    @field_validator("qualification_level")
    @classmethod
    def validate_qualification_level(cls, v: str) -> str:
        if not v or not v.strip():
            return "10TH"
        normalized = v.upper().strip()
        mapping = {
            "10TH CLASS (SSC)": "10TH",
            "SSC": "10TH",
            "10TH": "10TH",
            "INTERMEDIATE": "INTER",
            "10+2": "INTER",
            "INTER": "INTER",
            "UNDERGRADUATE": "UG",
            "GRADUATE": "UG",
            "BTECH": "UG",
            "DEGREE": "UG",
            "UG": "UG",
            "POSTGRADUATE": "PG",
            "POST_GRADUATE": "PG",
            "PG": "PG",
            "DIPLOMA": "DIPLOMA",
            "ITI": "ITI",
            "OTHER": "OTHER",
        }
        val = mapping.get(normalized, normalized)
        valid_tiers = {"10TH", "INTER", "UG", "PG", "DIPLOMA", "ITI", "OTHER"}
        if val not in valid_tiers:
            raise ValueError(f"Invalid qualification tier. Must be one of: {', '.join(sorted(valid_tiers))}")
        return val

    @field_validator("mandal")
    @classmethod
    def validate_mandal(cls, v: str) -> str:
        if not v or not v.strip():
            return "Vijayawada Urban"
        cleaned = v.strip()
        matched = next((m for m in NTR_MANDALS if m.lower() == cleaned.lower()), None)
        if not matched:
            raise ValueError(f"Invalid mandal '{cleaned}'. Must be a valid Mandal from NTR District.")
        return matched

    @field_validator("reference_admin")
    @classmethod
    def validate_reference_admin(cls, v: Optional[str]) -> str:
        if not v or not v.strip():
            return "Direct Student Self-Registration"
        cleaned = v.strip()
        matched = next((r for r in REFERENCE_ADMINS if r.lower() == cleaned.lower()), None)
        if not matched:
            raise ValueError(f"Invalid reference admin '{cleaned}'. Must be an approved referring authority.")
        return matched

    @field_validator("district")
    @classmethod
    def validate_district(cls, v: str) -> str:
        if not v or not v.strip():
            return "NTR District"
        cleaned = v.strip()
        matched = next((d for d in DISTRICT_LOCATIONS if d.lower() == cleaned.lower()), None)
        if not matched:
            # Check if cleaned contains any known district name
            matched = next((d for d in DISTRICT_LOCATIONS if d.lower() in cleaned.lower()), None)
        if not matched:
            raise ValueError(f"Invalid district location '{cleaned}'. Must be an approved district.")
        # Return cleaned district name without parenthetical suffix
        return matched.replace("(Vijayawada)", "").strip() or "NTR District"


class UserSummary(BaseModel):
    id: str
    email: str
    phone: Optional[str] = None
    role: str = "CANDIDATE"
    is_active: bool = True
    is_verified: bool = True

    model_config = ConfigDict(from_attributes=True)


class CandidateSummary(BaseModel):
    id: str
    user_id: str
    name: str
    phone: Optional[str] = None
    district: Optional[str] = None
    mandal: Optional[str] = None
    village: Optional[str] = None
    qualification_level: Optional[str] = None
    reference_admin: Optional[str] = None
    profile_completion: Optional[int] = 35
    verified: Optional[bool] = True

    model_config = ConfigDict(from_attributes=True)


class CandidateRegisterResponse(BaseModel):
    status: str = "success"
    message: str = "Candidate account created successfully. Welcome to NTR VIKASA!"
    access_token: Optional[str] = None
    token_type: Optional[str] = "bearer"
    user: UserSummary
    candidate: CandidateSummary

    model_config = ConfigDict(from_attributes=True)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr = Field(..., description="Registered email address")


class ForgotPasswordResponse(BaseModel):
    message: str = "If an account exists with this email, a password reset link has been sent."


class ResetPasswordRequest(BaseModel):
    token: str = Field(..., min_length=10, description="One-time password reset token")
    new_password: str = Field(..., min_length=8, max_length=100, description="New secure password")
    confirm_password: str = Field(..., min_length=8, max_length=100, description="Confirm new password")

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v: str, info) -> str:
        if "new_password" in info.data and v != info.data["new_password"]:
            raise ValueError("New password and confirm password do not match.")
        return v


class ResetPasswordResponse(BaseModel):
    message: str = "Password reset successfully."


class LoginRequest(BaseModel):
    email: EmailStr = Field(..., description="Registered email address")
    password: str = Field(..., min_length=1, max_length=100, description="Account password")
    role: Optional[str] = Field(default=None, description="Optional role hint (CANDIDATE, RECRUITER, ADMIN)")


class UserSummaryWithRole(BaseModel):
    id: str
    email: str
    name: Optional[str] = None
    role: str = "CANDIDATE"
    is_active: bool = True
    is_verified: bool = True

    model_config = ConfigDict(from_attributes=True)


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    user: UserSummaryWithRole

    model_config = ConfigDict(from_attributes=True)


