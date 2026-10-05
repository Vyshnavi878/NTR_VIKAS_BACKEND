from typing import List, Optional, Any
from pydantic import BaseModel, Field, ConfigDict


class CandidateBrief(BaseModel):
    id: str
    full_name: str


class StatusCounts(BaseModel):
    all: int = 0
    applied: int = 0
    screening: int = 0
    shortlisted: int = 0
    interview: int = 0
    selected: int = 0
    rejected: int = 0


class TimelineEventItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    status: str
    stage: str
    label: Optional[str] = None
    date: Optional[str] = None
    timestamp: Optional[str] = None
    completed: bool = False
    current: bool = False
    step_order: int = 1


class CandidateApplicationItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    application_id: str
    id: str  # alias for frontend app.id
    appNumber: str  # alias for frontend app.appNumber
    job_id: str
    jobId: str  # alias for frontend app.jobId
    job_title: str
    title: str  # alias for frontend app.title
    company_name: str
    company: str  # alias for frontend app.company
    location: str
    salary: Optional[str] = None
    employment_type: str = "Full-time"
    type: str = "Full-time"  # alias for frontend app.type
    work_mode: str = "On-site"
    mode: str = "On-site"  # alias for frontend app.mode
    applied_at: str
    appliedDate: str  # alias for frontend app.appliedDate
    application_type: str = "Direct Job Application"
    applicationType: str = "Direct Job Application"  # alias for frontend app.applicationType
    job_mela_id: Optional[str] = None
    melaId: Optional[str] = None  # alias for frontend app.melaId
    melaTitle: Optional[str] = None
    status: str
    resume_name: Optional[str] = None
    resumeName: Optional[str] = None
    cover_letter: Optional[str] = None
    coverLetter: Optional[str] = None
    additional_info: Optional[str] = None
    additionalInfo: Optional[str] = None
    match_percentage: Optional[int] = None
    matchScore: Optional[int] = None
    timeline: List[TimelineEventItem] = Field(default_factory=list)


class CandidateApplicationsListResponse(BaseModel):
    candidate: CandidateBrief
    status_counts: StatusCounts
    applications: List[CandidateApplicationItem]


class ApplicationTimelineResponse(BaseModel):
    application_id: str
    timeline: List[TimelineEventItem]


class CandidateApplicationCreate(BaseModel):
    job_id: Any = Field(..., description="Job identifier")
    job_title: Optional[str] = None
    company_name: Optional[str] = None
    location: Optional[str] = None
    salary: Optional[str] = None
    employment_type: Optional[str] = None
    work_mode: Optional[str] = None
    application_type: Optional[str] = None
    mela_id: Optional[str] = None
    mela_title: Optional[str] = None
    cover_letter: Optional[str] = None
    additional_info: Optional[str] = None
    resume_name: Optional[str] = None

