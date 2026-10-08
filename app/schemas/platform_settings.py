from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator


class PlatformSettingsResponse(BaseModel):
    id: int = 1
    platform_display_name: str = "NTR VIKASA State Job Portal Administration"
    primary_support_email: str = "support@ntrvikasa.com"
    grievance_redressal_email: str = "grievance@ntrvikasa.com"
    mandatory_recruiter_legal_verification: bool = True
    pre_publish_job_moderation_queue: bool = True
    strict_zero_fee_candidate_rule: bool = True
    platform_maintenance_mode: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None

    # Frontend camelCase compatibility aliases
    platformName: Optional[str] = None
    supportEmail: Optional[str] = None
    grievanceEmail: Optional[str] = None
    requireRecruiterVerification: Optional[bool] = None
    requireJobModeration: Optional[bool] = None
    enforceZeroCandidateFee: Optional[bool] = None
    enableMaintenanceMode: Optional[bool] = None

    model_config = ConfigDict(from_attributes=True)


class PlatformSettingsUpdate(BaseModel):
    platform_display_name: Optional[str] = Field(None, min_length=1, max_length=255)
    platformName: Optional[str] = Field(None, min_length=1, max_length=255)

    primary_support_email: Optional[EmailStr] = None
    supportEmail: Optional[EmailStr] = None

    grievance_redressal_email: Optional[EmailStr] = None
    grievanceEmail: Optional[EmailStr] = None

    mandatory_recruiter_legal_verification: Optional[bool] = None
    requireRecruiterVerification: Optional[bool] = None

    pre_publish_job_moderation_queue: Optional[bool] = None
    requireJobModeration: Optional[bool] = None

    strict_zero_fee_candidate_rule: Optional[bool] = None
    enforceZeroCandidateFee: Optional[bool] = None

    platform_maintenance_mode: Optional[bool] = None
    enableMaintenanceMode: Optional[bool] = None

    @field_validator("platform_display_name", "platformName")
    @classmethod
    def validate_non_blank(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            cleaned = v.strip()
            if not cleaned:
                raise ValueError("Platform display name cannot be blank.")
            return cleaned
        return v
