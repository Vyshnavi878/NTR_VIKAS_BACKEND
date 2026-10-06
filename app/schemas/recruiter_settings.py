from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr, Field, field_validator


# ── 1. Profile Schemas ────────────────────────────────────────────────────────
class RecruiterProfileSettingsResponse(BaseModel):
    id: str
    full_name: str
    name: str
    designation: str
    work_email: str
    email: str
    phone: Optional[str] = None
    mobile_phone: Optional[str] = None
    company_id: str
    company_name: str
    companyName: str
    role: str
    status: str

    model_config = {"from_attributes": True}


class RecruiterProfileSettingsUpdate(BaseModel):
    full_name: Optional[str] = Field(None, max_length=150)
    name: Optional[str] = Field(None, max_length=150)
    designation: Optional[str] = Field(None, max_length=150)
    phone: Optional[str] = Field(None, max_length=20)
    mobile_phone: Optional[str] = Field(None, max_length=20)


# ── 2. Team Member & Invitation Schemas ───────────────────────────────────────
class TeamMemberResponse(BaseModel):
    id: str
    user_id: Optional[str] = None
    full_name: str
    name: str
    work_email: str
    email: str
    role: str
    status: str
    joined_at: Optional[str] = None
    invitation_token: Optional[str] = None
    invitationToken: Optional[str] = None

    model_config = {"from_attributes": True}


class TeamInvitationCreate(BaseModel):
    full_name: Optional[str] = Field(None, max_length=150)
    name: Optional[str] = Field(None, max_length=150)
    email: EmailStr
    role: str = "TECHNICAL_RECRUITER"

    @field_validator("role")
    @classmethod
    def normalize_role(cls, v: str) -> str:
        role_map = {
            "COMPANY_OWNER": "COMPANY_OWNER",
            "Company Owner": "COMPANY_OWNER",
            "TECHNICAL_RECRUITER": "TECHNICAL_RECRUITER",
            "Technical Recruiter": "TECHNICAL_RECRUITER",
            "HIRING_MANAGER": "HIRING_MANAGER",
            "Hiring Manager": "HIRING_MANAGER",
            "INTERVIEW_PANELIST": "INTERVIEW_PANELIST",
            "Interview Panelist": "INTERVIEW_PANELIST",
        }
        clean = v.strip()
        if clean in role_map:
            return role_map[clean]
        return clean.upper().replace(" ", "_")


class TeamInvitationResponse(BaseModel):
    id: str
    email: str
    full_name: str
    name: str
    role: str
    status: str = "INVITED"
    invitation_token: Optional[str] = None
    invitationToken: Optional[str] = None
    invite_url: Optional[str] = None
    expires_at: str
    message: Optional[str] = "Invitation sent successfully."


class ValidateInvitationResponse(BaseModel):
    valid: bool
    email: Optional[str] = None
    full_name: Optional[str] = None
    name: Optional[str] = None
    role: Optional[str] = None
    company_id: Optional[str] = None
    company_name: Optional[str] = None
    companyName: Optional[str] = None
    company_logo: Optional[str] = None
    invited_by: Optional[str] = None
    expires_at: Optional[str] = None
    message: Optional[str] = None


class AcceptInvitationRequest(BaseModel):
    token: str
    password: str = Field(..., min_length=6)
    confirm_password: Optional[str] = None
    confirmPassword: Optional[str] = None
    name: Optional[str] = None


class AcceptInvitationResponse(BaseModel):
    status: str = "success"
    message: str = "Account created and invitation accepted successfully."
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    user: Optional[Dict[str, Any]] = None


# ── 3. Notification Preferences ───────────────────────────────────────────────
class RecruiterNotificationPreferencesResponse(BaseModel):
    instant_new_applicant_alerts: bool = True
    interview_confirmation_reminders: bool = True
    weekly_hiring_digest: bool = True
    job_mela_alerts: bool = True
    applicant_alerts: bool = True
    interview_alerts: bool = True
    weekly_digest: bool = True
    applicantAlerts: bool = True
    interviewAlerts: bool = True
    weeklyDigest: bool = True
    jobMelaAlerts: bool = True
    updated_at: Optional[str] = None

    model_config = {"from_attributes": True}


class RecruiterNotificationPreferencesUpdate(BaseModel):
    instant_new_applicant_alerts: Optional[bool] = None
    interview_confirmation_reminders: Optional[bool] = None
    weekly_hiring_digest: Optional[bool] = None
    job_mela_alerts: Optional[bool] = None
    applicantAlerts: Optional[bool] = None
    interviewAlerts: Optional[bool] = None
    weeklyDigest: Optional[bool] = None
    jobMelaAlerts: Optional[bool] = None


# ── 4. Change Password ─────────────────────────────────────────────────────────
class RecruiterChangePasswordRequest(BaseModel):
    current_password: Optional[str] = None
    currentPassword: Optional[str] = None
    new_password: Optional[str] = None
    newPassword: Optional[str] = None
    confirm_password: Optional[str] = None
    confirmPassword: Optional[str] = None
