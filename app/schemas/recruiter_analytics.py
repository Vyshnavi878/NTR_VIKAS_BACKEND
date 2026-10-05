from typing import List, Optional
from pydantic import BaseModel, Field


class DateRangeInfo(BaseModel):
    type: str = Field(..., description="Range type, e.g. 7d, 30d, 90d, 1y, custom")
    start_date: str = Field(..., description="ISO start date YYYY-MM-DD")
    end_date: str = Field(..., description="ISO end date YYYY-MM-DD")


class AnalyticsSummary(BaseModel):
    total_applications: int = Field(0, description="Total applications received in period")
    shortlist_conversion: float = Field(0.0, description="Percentage of applications shortlisted")
    interviews_conducted: int = Field(0, description="Interviews conducted/scheduled in period")
    average_time_to_hire_days: int = Field(0, description="Average days from application to hire")


class RecruitmentFunnel(BaseModel):
    applications_received: int = Field(0, description="Total applications in period")
    profile_shortlisted: int = Field(0, description="Applications shortlisted or further")
    technical_interviews: int = Field(0, description="Interviews conducted or applications at interview stage")
    final_offers_hires: int = Field(0, description="Applications selected or hired")


class ApplicationVelocityItem(BaseModel):
    period: str = Field(..., description="Period label, e.g. 2026-09 or Sep")
    total_applicants: int = Field(0, description="Total applicants in period")
    hired_candidates: int = Field(0, description="Hired candidates in period")
    month: Optional[str] = None
    applicants: Optional[int] = None
    hired: Optional[int] = None
    interviews: Optional[int] = 0


class JobPostingPerformanceItem(BaseModel):
    job_id: str
    job_title: str
    department: Optional[str] = "Engineering"
    work_mode: Optional[str] = "Hybrid"
    applicants: int = 0
    shortlisted: int = 0
    interviews: int = 0
    status: str = "PUBLISHED"


class CandidateSourcingItem(BaseModel):
    source: str
    applicants: int = 0
    percentage: float = 0.0
    color: Optional[str] = None


class JobMelaInsight(BaseModel):
    enabled: bool = True
    message: str = (
        "Job Mela participation increased qualified applicant inflow by +38%."
    )


class RecruiterAnalyticsResponse(BaseModel):
    date_range: DateRangeInfo
    summary: AnalyticsSummary
    recruitment_funnel: RecruitmentFunnel
    application_velocity: List[ApplicationVelocityItem]
    job_posting_performance: List[JobPostingPerformanceItem]
    candidate_sourcing: List[CandidateSourcingItem]
    job_mela_insight: JobMelaInsight
