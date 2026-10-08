import re
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator


class AdminProfileResponse(BaseModel):
    """Admin profile information response schema."""
    id: str
    full_name: str
    email: str
    role: str
    designation: Optional[str] = None
    contact_phone: Optional[str] = None
    department: Optional[str] = None
    status: str = "ACTIVE"
    profile_image_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AdminProfileUpdate(BaseModel):
    """Admin profile update request schema."""
    full_name: Optional[str] = Field(None, min_length=2, max_length=150, description="Administrator full display name")
    email: Optional[EmailStr] = Field(None, description="Official Administrator email address")
    designation: Optional[str] = Field(None, max_length=150, description="Administrator designation")
    contact_phone: Optional[str] = Field(None, max_length=30, description="Contact phone number")

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v_clean = v.strip()
            if not v_clean:
                raise ValueError("Full name cannot be blank.")
            if len(v_clean) < 2:
                raise ValueError("Full name must be at least 2 characters long.")
            return v_clean
        return v

    @field_validator("designation")
    @classmethod
    def validate_designation(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v_clean = v.strip()
            return v_clean if v_clean else None
        return v

    @field_validator("contact_phone")
    @classmethod
    def validate_contact_phone(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v_clean = v.strip()
            if not v_clean:
                return None
            cleaned_digits = re.sub(r"[^\d]", "", v_clean)
            if len(cleaned_digits) < 10 or len(cleaned_digits) > 13:
                raise ValueError("Contact phone number must be a valid Indian phone number (10-13 digits).")
            return v_clean
        return v


class AdminProfileImageResponse(BaseModel):
    """Admin profile image upload response schema."""
    profile_image_url: str
    message: str = "Profile image updated successfully."
