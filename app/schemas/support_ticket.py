from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, field_validator

SUPPORT_ISSUE_CATEGORIES = [
    "Application Status & Tracker",
    "Resume Upload / ATS Optimization",
    "Job Mela Registration & QR Pass",
    "Interview Scheduling & Links",
    "Profile & Skills Updating",
    "Other Support Request",
]


class SupportTicketCreate(BaseModel):
    issue_category: str = Field(..., description="Issue category chosen from approved options")
    subject: str = Field(..., min_length=3, max_length=255, description="Brief summary of the issue")
    description: str = Field(..., min_length=5, max_length=5000, description="Detailed problem description")

    @field_validator("issue_category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Issue category is required.")
        clean = v.strip()
        matched = next((c for c in SUPPORT_ISSUE_CATEGORIES if c.lower() == clean.lower()), None)
        if not matched:
            raise ValueError(
                f"Invalid issue category '{clean}'. Allowed categories: {', '.join(SUPPORT_ISSUE_CATEGORIES)}"
            )
        return matched

    @field_validator("subject")
    @classmethod
    def validate_subject(cls, v: str) -> str:
        clean = v.strip() if v else ""
        if not clean:
            raise ValueError("Subject cannot be empty or whitespace only.")
        if len(clean) < 3:
            raise ValueError("Subject must be at least 3 characters long.")
        if len(clean) > 255:
            raise ValueError("Subject cannot exceed 255 characters.")
        return clean

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str) -> str:
        clean = v.strip() if v else ""
        if not clean:
            raise ValueError("Description cannot be empty or whitespace only.")
        if len(clean) < 5:
            raise ValueError("Description must be at least 5 characters long.")
        if len(clean) > 5000:
            raise ValueError("Description cannot exceed 5000 characters.")
        return clean


class SupportTicketItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    ticket_number: str
    candidate_id: str
    candidate_name: str
    registered_email: str
    issue_category: str
    subject: str
    description: str
    status: str
    priority: str
    created_at: str
    updated_at: Optional[str] = None
    resolved_at: Optional[str] = None
    closed_at: Optional[str] = None


class SupportTicketCreateResponse(BaseModel):
    message: str = "Support request submitted successfully."
    ticket: SupportTicketItem


class SupportTicketListResponse(BaseModel):
    items: List[SupportTicketItem]
    total: int
