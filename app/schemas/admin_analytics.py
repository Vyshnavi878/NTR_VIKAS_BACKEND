from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field


class AnalyticsPeriod(BaseModel):
    type: str = Field(..., description="Period identifier: 7d, 30d, 90d, 1y, custom")
    start_date: str = Field(..., description="Start date in YYYY-MM-DD format")
    end_date: str = Field(..., description="End date in YYYY-MM-DD format")
    label: str = Field(..., description="Human readable label e.g. Last 30 Days")


class AnalyticsKPIs(BaseModel):
    total_platform_users: int = Field(0, description="Total active registered users across all roles")
    active_candidates: int = Field(0, description="Active job seekers with candidate profiles")
    verified_recruiters: int = Field(0, description="Approved and verified corporate recruiters")
    registered_companies: int = Field(0, description="Unique registered employer organizations")
    live_posted_jobs: int = Field(0, description="Currently active and published job vacancies")
    submitted_applications: int = Field(0, description="Total candidate job and internship applications")
    active_internships: int = Field(0, description="Approved and active student internship postings")
    mela_registrations: int = Field(0, description="Candidate registrations for Mega Job Melas")


class SectorDemandItem(BaseModel):
    name: str = Field(..., description="Industry sector name e.g. Information Technology & Software")
    sector: Optional[str] = Field(None, description="Alias for sector name")
    share: str = Field(..., description="Formatted percentage share e.g. 48.5%")
    percentage: float = Field(..., description="Numeric percentage value")
    count: str = Field(..., description="Formatted job count string e.g. 2,140 Jobs")
    job_count: int = Field(..., description="Numeric job count")
    color: str = Field("#3b82f6", description="Sector theme color for progress bar")


class MonthlyPlacementItem(BaseModel):
    month: str = Field(..., description="Formatted month e.g. Jul 2026")
    date_key: Optional[str] = Field(None, description="ISO month key YYYY-MM")
    candidates: int = Field(0, description="Total candidate registrations in month")
    active_jobs: int = Field(0, description="Total active jobs in month")
    placements: int = Field(0, description="Successful placements / hires in month")


class AdminAnalyticsResponse(BaseModel):
    period: AnalyticsPeriod
    kpis: AnalyticsKPIs
    hiring_demand_by_sector: List[SectorDemandItem] = Field(default_factory=list)
    monthly_placement_trajectory: List[MonthlyPlacementItem] = Field(default_factory=list)

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )
