from typing import Optional
from pydantic import BaseModel, Field


class RecruiterRegisterResponse(BaseModel):
    message: str = Field(
        default="Recruiter registration submitted successfully for admin approval.",
        description="Submission confirmation message",
    )
    status: str = Field(
        default="PENDING_APPROVAL",
        description="Recruiter registration approval status",
    )
    company_name: Optional[str] = Field(
        default=None,
        description="Registered company name",
    )
