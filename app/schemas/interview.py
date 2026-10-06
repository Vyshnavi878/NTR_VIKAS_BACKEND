import json
from datetime import datetime
from typing import Optional, List, Union, Dict, Any
from pydantic import BaseModel, Field, field_validator


class CandidateSummary(BaseModel):
    id: Optional[str] = None
    name: str
    email: Optional[str] = None


class JobSummary(BaseModel):
    id: Optional[str] = None
    title: str


class InterviewCreate(BaseModel):
    application_id: Optional[Union[str, int]] = Field(
        None,
        description="Candidate application identifier or application_number",
    )
    scheduled_date: Optional[str] = Field(
        None,
        description="Interview scheduled date in YYYY-MM-DD format",
    )
    start_time: Optional[str] = Field(
        None,
        description="Start time (e.g. 11:00 or 11:00 AM)",
    )
    end_time: Optional[str] = Field(
        None,
        description="End time (e.g. 12:00 or 12:00 PM)",
    )
    format: str = Field(
        default="ONLINE",
        description="Interview format: ONLINE or OFFLINE",
    )
    meeting_link: Optional[str] = Field(
        None,
        description="Meeting URL for ONLINE interviews",
    )
    venue: Optional[str] = Field(
        None,
        description="Physical venue address for OFFLINE interviews",
    )
    interviewer_panel: Optional[Union[List[str], str]] = Field(
        None,
        description="Interviewer panel names or array",
    )
    agenda_notes: Optional[str] = Field(
        None,
        description="Interview round agenda, notes, or instructions",
    )
    timezone: str = Field(
        default="Asia/Kolkata",
        description="Timezone (default: Asia/Kolkata)",
    )

    # Optional compatibility fields for direct submissions
    candidate_name: Optional[str] = None
    candidate_email: Optional[str] = None
    job_title: Optional[str] = None
    job_id: Optional[str] = None
    date: Optional[str] = None
    time: Optional[str] = None
    type: Optional[str] = None
    interviewer: Optional[str] = None
    notes: Optional[str] = None

    @field_validator("format", mode="before")
    @classmethod
    def normalize_format(cls, v: Any) -> str:
        if not v:
            return "ONLINE"
        v_str = str(v).strip().upper()
        if "ONLINE" in v_str or "GOOGLE" in v_str or "TEAMS" in v_str or "ZOOM" in v_str or "VIDEO" in v_str:
            return "ONLINE"
        if "OFFLINE" in v_str or "PERSON" in v_str or "OFFICE" in v_str:
            return "OFFLINE"
        return "ONLINE"


class InterviewUpdate(BaseModel):
    scheduled_date: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    format: Optional[str] = None
    meeting_link: Optional[str] = None
    venue: Optional[str] = None
    interviewer_panel: Optional[Union[List[str], str]] = None
    agenda_notes: Optional[str] = None
    timezone: Optional[str] = "Asia/Kolkata"

    # Compatibility fields
    date: Optional[str] = None
    time: Optional[str] = None
    interviewer: Optional[str] = None
    notes: Optional[str] = None


class InterviewCancel(BaseModel):
    reason: str = Field(..., min_length=1, description="Reason for cancelling the interview")


class InterviewComplete(BaseModel):
    notes: Optional[str] = Field(
        None,
        description="Interview feedback, screening score, and completion evaluation notes",
    )


class InterviewResponse(BaseModel):
    id: str
    application_id: Optional[str] = None
    candidate: CandidateSummary
    job: JobSummary

    # Top-level direct identifiers & camelCase aliases for seamless frontend compatibility
    candidate_name: str
    candidate_email: Optional[str] = None
    candidateName: str
    candidateEmail: Optional[str] = None

    job_title: str
    jobTitle: str

    status: str
    scheduled_date: Optional[str] = None
    date: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    time: Optional[str] = None
    timezone: str = "Asia/Kolkata"

    format: str = "ONLINE"
    type: Optional[str] = None
    meeting_link: Optional[str] = None
    meetingLink: Optional[str] = None
    venue: Optional[str] = None

    interviewer_panel: Optional[List[str]] = None
    interviewer: Optional[str] = None
    agenda_notes: Optional[str] = None
    notes: Optional[str] = None

    company_name: Optional[str] = None
    companyName: Optional[str] = None
    company: Optional[str] = None

    title: Optional[str] = None
    interview_title: Optional[str] = None
    role: Optional[str] = None
    mode: Optional[str] = None

    meeting_platform: Optional[str] = "Google Meet"
    meetingPlatform: Optional[str] = "Google Meet"
    meetingUrl: Optional[str] = None

    panel: Optional[str] = None
    instructions: Optional[str] = None
    preparation_note: Optional[str] = None
    result: Optional[str] = None

    completed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    cancellation_reason: Optional[str] = None
    rescheduled_from_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class InterviewListResponse(BaseModel):
    items: List[InterviewResponse]
    total: int
    page: int = 1
    page_size: int = 50
    tab_counts: Optional[Dict[str, int]] = None


class CandidateInterviewCounts(BaseModel):
    all: int = 0
    upcoming: int = 0
    today: int = 0
    completed: int = 0


class CandidateInterviewListResponse(BaseModel):
    items: List[InterviewResponse]
    total: int
    page: int = 1
    page_size: int = 9
    total_pages: int = 1
    counts: CandidateInterviewCounts

