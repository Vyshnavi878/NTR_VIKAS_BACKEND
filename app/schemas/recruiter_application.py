"""
Pydantic Schemas for Recruiter Applications.
Provides type validation for:
- Recruiter application listing with pagination, summary counts, and job posting breakdowns
- Application detailed view with candidate profile, resume, and timeline
- Application status transitions
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class CandidateInfo(BaseModel):
    id: str
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    experience_years: Optional[float] = None
    experience: Optional[str] = None
    location: Optional[str] = None
    notice_period: Optional[str] = None
    expected_salary: Optional[str] = None
    headline: Optional[str] = None
    skills: List[str] = Field(default_factory=list)
    education: Optional[List[Dict[str, Any]]] = None
    work_experience: Optional[List[Dict[str, Any]]] = None


class JobInfo(BaseModel):
    job_id: str
    title: str
    company_name: str
    department: Optional[str] = None
    job_type: Optional[str] = None
    location: Optional[str] = None


class JobMelaInfo(BaseModel):
    mela_id: str
    mela_name: str
    registration_pass_id: Optional[str] = None
    event_number: Optional[str] = None
    company_sequence: Optional[str] = None
    application_sequence: Optional[str] = None


class ResumeInfo(BaseModel):
    file_name: Optional[str] = None
    file_url: Optional[str] = None
    file_size: Optional[str] = None


class InterviewInfo(BaseModel):
    id: str
    status: str
    scheduled_at: Optional[str] = None
    date: Optional[str] = None
    time: Optional[str] = None
    format: Optional[str] = None
    meeting_link: Optional[str] = None
    interviewer: Optional[str] = None


class TimelineEventInfo(BaseModel):
    id: Optional[str] = None
    stage: str
    status: str
    label: Optional[str] = None
    date: Optional[str] = None
    completed: bool = False
    current: bool = False
    step_order: int = 1


class RecruiterApplicationItem(BaseModel):
    application_id: str
    id: str
    application_number: str
    app_number: str
    application_type: str
    status: str
    candidate: CandidateInfo
    job: JobInfo
    match_score: Optional[int] = None
    applied_at: Optional[str] = None
    applied_date: Optional[str] = None
    job_mela: Optional[JobMelaInfo] = None
    interview: Optional[InterviewInfo] = None
    cover_letter: Optional[str] = None
    additional_info: Optional[str] = None
    resume: Optional[ResumeInfo] = None


class RecruiterApplicationDetail(RecruiterApplicationItem):
    timeline: List[TimelineEventInfo] = Field(default_factory=list)


class PaginationMeta(BaseModel):
    page: int
    page_size: int
    total_items: int
    total_pages: int
    has_next: bool
    has_previous: bool


class SummaryCounts(BaseModel):
    total_received: int
    screening: int
    shortlisted: int
    interviews: int
    selected_hired: int
    rejected: int


class JobPostingSummary(BaseModel):
    job_id: str
    title: str
    application_count: int


class RecruiterApplicationsResponse(BaseModel):
    items: List[RecruiterApplicationItem]
    pagination: PaginationMeta
    summary: SummaryCounts
    job_postings: List[JobPostingSummary]


class ApplicationStatusUpdateRequest(BaseModel):
    status: str = Field(..., description="Target status (e.g. SCREENING, SHORTLISTED, INTERVIEW, SELECTED, REJECTED)")
    notes: Optional[str] = Field(None, description="Optional recruitment notes or remarks")
