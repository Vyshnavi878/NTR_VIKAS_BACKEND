from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class CandidateSummaryBrief(BaseModel):
    id: str
    full_name: str


class SavedJobItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    saved_job_id: str
    job_id: str
    id: str  # alias for frontend job.id compatibility
    title: str
    company_name: str
    company: str  # alias for frontend job.company compatibility
    company_verified: bool = True
    location: str
    salary: Optional[str] = None
    experience: Optional[str] = None
    employment_type: str = "Full-time"
    type: str = "Full-time"  # alias for frontend job.type compatibility
    work_mode: str = "Hybrid"
    mode: str = "Hybrid"  # alias for frontend job.mode compatibility
    skills: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)  # alias for frontend job.tags compatibility
    saved_at: str
    is_applied: bool = False


class SavedJobsListResponse(BaseModel):
    candidate: CandidateSummaryBrief
    saved_jobs_count: int
    saved_jobs: List[SavedJobItem]


class SaveJobRequest(BaseModel):
    job_id: str
    title: Optional[str] = "Senior Software Engineer"
    company_name: Optional[str] = "TechCorp India"
    company_verified: Optional[bool] = True
    location: Optional[str] = "Bengaluru, Karnataka"
    salary: Optional[str] = "₹14 - ₹22 LPA"
    experience: Optional[str] = "3-5 years"
    employment_type: Optional[str] = "Full-time"
    work_mode: Optional[str] = "Hybrid"
    skills: Optional[List[str]] = Field(default_factory=list)


class SavedJobDeleteResponse(BaseModel):
    message: str = "Job removed from saved jobs."


class SavedJobActionResponse(BaseModel):
    message: str
    saved_job: Optional[SavedJobItem] = None
