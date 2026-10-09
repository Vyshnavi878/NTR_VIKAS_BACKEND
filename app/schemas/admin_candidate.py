import re
from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator


class AdminCreateCandidateRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=150, description="Student Full Name")
    email: EmailStr = Field(..., description="Student Email Address")
    mobile_number: str = Field(..., min_length=10, max_length=20, description="Mobile Phone Number")
    gender: str = Field(default="Male", description="Gender: Male, Female, Other")
    aadhaar_number: str = Field(..., description="Exactly 12-digit Aadhaar Card Number")
    referred_by: str = Field(default="Admin User (State Operations)", description="Referring Admin / Officer")
    custom_referrer: Optional[str] = Field(default=None, description="Custom referrer when referred_by is Other")
    placement_status: Optional[str] = Field(default="NOT_PLACED", description="Placement Status: PLACED or NOT_PLACED")
    placed_company: Optional[str] = Field(default=None, description="Company name if placed")
    placed_role: Optional[str] = Field(default=None, description="Designation / role if placed")
    placed_salary: Optional[str] = Field(default=None, description="Package / salary if placed")
    placed_date: Optional[str] = Field(default=None, description="Placement Date if placed")

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v: Any) -> str:
        if isinstance(v, str):
            return v.strip().lower()
        return v

    @field_validator("mobile_number")
    @classmethod
    def validate_mobile(cls, v: str) -> str:
        clean = re.sub(r"[^\d+]", "", v)
        digits_only = re.sub(r"\D", "", clean)
        if len(digits_only) < 10:
            raise ValueError("Mobile number must contain at least 10 numeric digits")
        return clean

    @field_validator("gender")
    @classmethod
    def validate_gender(cls, v: str) -> str:
        norm = v.strip().capitalize()
        if norm not in ["Male", "Female", "Other"]:
            raise ValueError("Gender must be one of 'Male', 'Female', or 'Other'")
        return norm

    @field_validator("aadhaar_number")
    @classmethod
    def validate_aadhaar(cls, v: str) -> str:
        digits = re.sub(r"\D", "", v)
        if len(digits) != 12:
            raise ValueError("Aadhaar Card Number must be exactly 12 numeric digits")
        return digits

    @model_validator(mode="after")
    def validate_custom_referrer_and_placement(self) -> "AdminCreateCandidateRequest":
        # Check custom referrer when "Other" is selected
        if self.referred_by and self.referred_by.strip().lower() == "other":
            if not self.custom_referrer or not self.custom_referrer.strip():
                raise ValueError("Custom referrer description is required when 'Other' is selected as referring officer")

        # Normalize placement status
        raw_status = (self.placement_status or "NOT_PLACED").strip().upper()
        if raw_status in ["PLACED", "HIRED"]:
            self.placement_status = "PLACED"
        else:
            self.placement_status = "NOT_PLACED"

        return self


class AdminUpdateCandidatePlacementRequest(BaseModel):
    placement_status: str = Field(..., description="Placement status: PLACED or NOT_PLACED")
    placed_company: Optional[str] = Field(default=None, description="Company name if placed")
    placed_role: Optional[str] = Field(default=None, description="Job designation if placed")
    placed_salary: Optional[str] = Field(default=None, description="Salary / Package if placed")
    placed_date: Optional[str] = Field(default=None, description="Placement date if placed")

    @field_validator("placement_status")
    @classmethod
    def normalize_placement_status(cls, v: str) -> str:
        clean = v.strip().upper()
        if clean in ["PLACED", "HIRED"]:
            return "PLACED"
        return "NOT_PLACED"


class AdminUpdateCandidateStatusRequest(BaseModel):
    status: str = Field(..., description="Account status: ACTIVE or SUSPENDED")
    reason: Optional[str] = Field(default=None, description="Administrative reason")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        clean = v.strip().upper()
        if clean not in ["ACTIVE", "SUSPENDED"]:
            raise ValueError("Status must be 'ACTIVE' or 'SUSPENDED'")
        return clean


class AdminCandidateItem(BaseModel):
    id: str
    user_id: str
    name: str
    email: str
    phone: Optional[str] = None
    gender: Optional[str] = "Male"
    aadhaar_masked: str
    district: Optional[str] = "NTR District"
    mandal: Optional[str] = None
    village: Optional[str] = None
    location: Optional[str] = None
    qualification_level: Optional[str] = None
    education: Optional[str] = None
    headline: Optional[str] = None
    profile_completion: int = 35
    profile_status: str = "BASIC_REGISTERED"
    placement_status: str = "NOT_PLACED"
    placed_company: Optional[str] = None
    placed_role: Optional[str] = None
    placed_salary: Optional[str] = None
    placed_date: Optional[str] = None
    reference_admin: Optional[str] = None
    custom_referrer: Optional[str] = None
    account_status: str = "ACTIVE"
    registration_date: Optional[str] = None
    created_at: Optional[datetime] = None
    applications_count: int = 0


class PaginatedAdminCandidateResponse(BaseModel):
    items: List[AdminCandidateItem]
    total: int
    page: int
    page_size: int
    total_registered: int
    placed_students: int
    ssc_count: int
    inter_count: int
    ug_pg_count: int
