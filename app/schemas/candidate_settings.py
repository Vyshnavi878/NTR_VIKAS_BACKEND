from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class CandidateSettingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    email_job_application_alerts: bool = True
    sms_whatsapp_notifications: bool = True
    upcoming_interview_reminders: bool = True
    weekly_job_recommendation_digest: bool = False
    visible_in_recruiter_talent_search: bool = True
    direct_recruiter_messages: bool = True


class NotificationSettingsUpdate(BaseModel):
    email_job_application_alerts: Optional[bool] = None
    sms_whatsapp_notifications: Optional[bool] = None
    upcoming_interview_reminders: Optional[bool] = None
    weekly_job_recommendation_digest: Optional[bool] = None


class PrivacySettingsUpdate(BaseModel):
    visible_in_recruiter_talent_search: Optional[bool] = None
    direct_recruiter_messages: Optional[bool] = None


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1, description="Candidate current password")
    new_password: str = Field(..., min_length=8, description="New strong password, minimum 8 characters")
    confirm_password: str = Field(..., min_length=8, description="Confirmation of new password")


class MessageResponse(BaseModel):
    status: str = "success"
    message: str
