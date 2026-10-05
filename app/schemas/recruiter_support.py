from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator

RECRUITER_SUPPORT_CATEGORIES = [
    "Job Posting Approval & Moderation",
    "Candidate Applications & Pipeline",
    "Interview Scheduling & Virtual Links",
    "Company Verification & Documents",
    "Hiring Team & Collaborators",
    "Job Mela Participation & Stalls",
    "Other Employer Support Query",
]


class RecruiterSupportRequestCreate(BaseModel):
    issue_category: str = Field(
        ...,
        description="Issue category chosen from approved categories",
        json_schema_extra={"example": "Job Posting Approval & Moderation"},
    )
    subject: str = Field(
        ...,
        min_length=3,
        max_length=255,
        description="Subject summary of the query",
        json_schema_extra={"example": "Question regarding job approval status"},
    )
    description: str = Field(
        ...,
        min_length=5,
        max_length=5000,
        description="Detailed description of problem or question",
        json_schema_extra={"example": "Please provide an update regarding my pending job approval."},
    )


    @field_validator("issue_category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        clean = (v or "").strip()
        matched = next(
            (c for c in RECRUITER_SUPPORT_CATEGORIES if c.lower() == clean.lower()),
            None,
        )
        if not matched:
            raise ValueError(
                f"Invalid issue category '{clean}'. Allowed categories: {', '.join(RECRUITER_SUPPORT_CATEGORIES)}"
            )
        return matched

    @field_validator("subject")
    @classmethod
    def validate_subject(cls, v: str) -> str:
        clean = (v or "").strip()
        if len(clean) < 3:
            raise ValueError("Subject must contain at least 3 characters.")
        return clean

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str) -> str:
        clean = (v or "").strip()
        if len(clean) < 5:
            raise ValueError("Description must contain at least 5 characters.")
        return clean


class RecruiterSupportRequestResponse(BaseModel):
    message: str = "Support request submitted successfully."
    ticket_number: str
    status: str = "OPEN"


class RecruiterSupportRequestItem(BaseModel):
    id: str
    ticket_number: str
    recruiter_id: str
    company_name: str
    recruiter_name: str
    registered_email: str
    issue_category: str
    subject: str
    description: str
    status: str
    priority: str
    created_at: datetime
    updated_at: Optional[datetime] = None


class RecruiterSupportRequestListResponse(BaseModel):
    items: List[RecruiterSupportRequestItem]
    total: int
