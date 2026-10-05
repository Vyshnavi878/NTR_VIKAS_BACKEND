"""
Recruiter Dashboard — Pydantic Schemas
GET /api/v1/recruiter/dashboard
"""
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class RecruiterCompanyBrief(BaseModel):
    """Brief company info for nested recruiter profile."""
    id: Optional[str] = None
    name: str


class RecruiterProfileBrief(BaseModel):
    """Authenticated recruiter profile details."""
    id: str
    name: str
    email: str
    designation: Optional[str] = None
    phone: Optional[str] = None
    company_id: Optional[str] = None
    company_name: str
    company: Optional[RecruiterCompanyBrief] = None


class RecruiterDashboardSummary(BaseModel):
    """Aggregate statistics for the 5 dashboard summary cards."""
    active_jobs: int = 0
    pending_approvals: int = 0
    total_applications: int = 0
    shortlisted_pool: int = 0
    upcoming_interviews: int = 0


class RecruiterDashboardPipeline(BaseModel):
    """Funnel counts for the active recruitment pipeline."""
    applications: int = 0
    under_review: int = 0
    shortlisted: int = 0
    interviews: int = 0
    selected_hired: int = 0


class RecruiterDashboardApplication(BaseModel):
    """Recent application record for recruiter dashboard."""
    id: str
    application_number: str
    candidate_id: Optional[str] = None
    candidate_name: str
    candidateName: Optional[str] = None
    job_id: str
    job_title: str
    jobTitle: Optional[str] = None
    experience: Optional[str] = None
    match_percentage: Optional[int] = None
    matchScore: Optional[int] = None
    applied_at: str
    applied_date: Optional[str] = None
    appliedDate: Optional[str] = None
    status: str


class RecruiterDashboardJob(BaseModel):
    """Active job posting record for recruiter dashboard."""
    id: str
    job_id: str
    title: str
    department: Optional[str] = None
    location: str
    job_type: str
    type: Optional[str] = None
    status: str
    applications_count: int = 0
    applicantsCount: Optional[int] = None


class RecruiterDashboardInterview(BaseModel):
    """Upcoming interview card for recruiter dashboard."""
    id: str
    interview_number: Optional[str] = None
    candidate_id: Optional[str] = None
    candidate_name: str
    candidateName: Optional[str] = None
    job_id: Optional[str] = None
    job_title: str
    jobTitle: Optional[str] = None
    round_name: str
    interview_type: str
    type: Optional[str] = None
    date: Optional[str] = None
    time: Optional[str] = None
    scheduled_at: str
    meeting_platform: str
    meeting_link: Optional[str] = None
    meetingLink: Optional[str] = None
    status: str


class RecruiterDashboardResponse(BaseModel):
    """
    Unified canonical response for GET /api/v1/recruiter/dashboard.
    Strictly scoped to the authenticated recruiter.
    """
    recruiter: RecruiterProfileBrief
    summary: RecruiterDashboardSummary
    pipeline: RecruiterDashboardPipeline
    recent_applications: List[RecruiterDashboardApplication] = []
    active_jobs: List[RecruiterDashboardJob] = []
    upcoming_interviews: List[RecruiterDashboardInterview] = []
