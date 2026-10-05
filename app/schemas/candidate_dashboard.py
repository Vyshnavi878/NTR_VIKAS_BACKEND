"""
Candidate Dashboard — Pydantic Schemas
GET /api/v1/candidate/dashboard
"""
from typing import List, Optional
from pydantic import BaseModel


class CandidateSummary(BaseModel):
    """Core candidate identity returned in every dashboard response."""
    id: str
    full_name: str
    email: str
    district: Optional[str] = None
    mandal: Optional[str] = None
    qualification_level: Optional[str] = None
    headline: Optional[str] = None


class DashboardStatistics(BaseModel):
    """Aggregate counts for the four dashboard stat cards."""
    applied_jobs: int = 0
    shortlisted: int = 0
    interviews: int = 0
    saved_jobs: int = 0


class RecentApplication(BaseModel):
    """Single recent application record shown in the dashboard list."""
    application_id: str
    job_title: str
    company_name: str
    location: str
    applied_at: str
    status: str


class ProfileStrengthItem(BaseModel):
    """Individual checklist item for profile completion."""
    key: str
    label: str
    completed: bool


class ProfileStrength(BaseModel):
    """Calculated profile strength for the progress-bar card."""
    percentage: int
    label: str
    items: List[ProfileStrengthItem]


class RecommendedJob(BaseModel):
    """Single recommended job card."""
    job_id: str
    title: str
    company_name: str
    location: str
    salary: Optional[str] = None
    experience: Optional[str] = None
    employment_type: Optional[str] = None
    match_percentage: Optional[int] = None
    tags: List[str] = []
    is_applied: bool = False
    is_saved: bool = False


class UpcomingInterview(BaseModel):
    """Upcoming interview card."""
    interview_id: str
    job_title: str
    company_name: str
    scheduled_date: str
    start_time: str
    end_time: Optional[str] = None
    platform: Optional[str] = None
    meeting_url: Optional[str] = None
    mode: Optional[str] = None
    status: str


class CandidateDashboardResponse(BaseModel):
    """
    Single unified response for GET /api/v1/candidate/dashboard.
    Contains all data required by the Candidate Dashboard UI.
    """
    candidate: CandidateSummary
    statistics: DashboardStatistics
    recent_applications: List[RecentApplication] = []
    profile_strength: ProfileStrength
    recommended_jobs: List[RecommendedJob] = []
    upcoming_interviews: List[UpcomingInterview] = []
