from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, ConfigDict, Field



class JobCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=200, description="Job title")
    department: Optional[str] = Field("Core Engineering", description="Department / Functional area")
    job_type: Optional[str] = Field("Full-time", description="Employment type")
    employment_type: Optional[str] = Field(None, description="Alias for job_type")
    work_mode: Optional[str] = Field("Hybrid", description="Workplace policy")
    workplace_policy: Optional[str] = Field(None, description="Alias for work_mode")
    location: Optional[str] = Field("Bengaluru, Karnataka", description="Office location")
    experience: Optional[str] = Field("3-5 years", description="Experience required")
    experience_level: Optional[str] = Field(None, description="Alias for experience")
    salary: Optional[str] = Field(None, description="Salary text e.g. ₹16,00,000 - ₹24,00,000 / year")
    salary_min: Optional[int] = Field(None, description="Minimum CTC")
    salary_max: Optional[int] = Field(None, description="Maximum CTC")
    salary_currency: Optional[str] = Field("INR", description="Currency")
    openings: Optional[int] = Field(1, ge=1, le=500, description="Number of openings")
    number_of_openings: Optional[int] = Field(None, ge=1, le=500, description="Alias for openings")
    deadline: Optional[str] = Field(None, description="Application deadline date")
    application_deadline: Optional[str] = Field(None, description="Alias for deadline")
    description: Optional[str] = Field(None, description="Job summary / overview")
    job_summary: Optional[str] = Field(None, description="Alias for description")
    responsibilities: Optional[str] = Field(None, description="Key responsibilities")
    key_responsibilities: Optional[str] = Field(None, description="Alias for responsibilities")
    requirements: Optional[str] = Field(None, description="Technical requirements & skills")
    technical_requirements: Optional[str] = Field(None, description="Alias for requirements")
    qualifications: Optional[str] = Field(None, description="Educational qualifications")
    educational_qualifications: Optional[str] = Field(None, description="Alias for qualifications")
    skills: Optional[List[str]] = Field(default_factory=list, description="List of required skills/tags")

    model_config = ConfigDict(extra="ignore")


class JobUpdate(BaseModel):
    title: Optional[str] = None
    department: Optional[str] = None
    job_type: Optional[str] = None
    employment_type: Optional[str] = None
    work_mode: Optional[str] = None
    workplace_policy: Optional[str] = None
    location: Optional[str] = None
    experience: Optional[str] = None
    experience_level: Optional[str] = None
    salary: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    salary_currency: Optional[str] = None
    openings: Optional[int] = None
    number_of_openings: Optional[int] = None
    deadline: Optional[str] = None
    application_deadline: Optional[str] = None
    description: Optional[str] = None
    job_summary: Optional[str] = None
    responsibilities: Optional[str] = None
    key_responsibilities: Optional[str] = None
    requirements: Optional[str] = None
    technical_requirements: Optional[str] = None
    qualifications: Optional[str] = None
    educational_qualifications: Optional[str] = None
    skills: Optional[List[str]] = None
    status: Optional[str] = None

    model_config = ConfigDict(extra="ignore")


class JobRead(BaseModel):
    id: str
    job_id: str
    job_number: str
    company_name: str
    company_id: Optional[str] = None
    title: str
    department: str
    job_type: str
    employment_type: str
    work_mode: str
    workMode: str
    location: str
    experience: str
    experience_level: str
    salary: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    salary_currency: Optional[str] = "INR"
    openings: int = 1
    number_of_openings: int = 1
    status: str
    description: Optional[str] = None
    job_summary: Optional[str] = None
    responsibilities: Optional[str] = None
    key_responsibilities: Optional[str] = None
    requirements: Optional[str] = None
    technical_requirements: Optional[str] = None
    qualifications: Optional[str] = None
    educational_qualifications: Optional[str] = None
    skills: List[str] = []
    deadline: Optional[str] = None
    application_deadline: Optional[str] = None
    posted_at: Optional[str] = None
    createdAt: Optional[str] = None
    closed_at: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    rejection_reason: Optional[str] = None
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None
    applicantsCount: int = 0
    applicant_count: int = 0
    shortlistedCount: int = 0
    shortlisted_count: int = 0
    interviewsCount: int = 0
    interview_count: int = 0
    company: Optional[Union[Dict[str, Any], str]] = None
    company_verified: bool = True
    company_logo: Optional[str] = None
    company_logo_path: Optional[str] = None
    industry: Optional[str] = None
    tags: List[str] = []
    is_saved: bool = False
    has_applied: bool = False
    match_score: Optional[int] = None
    is_active: bool = True

    model_config = ConfigDict(from_attributes=True)


class PaginatedJobResponse(BaseModel):
    items: List[JobRead]
    total: int
    page: int
    page_size: int
    total_pages: int


class AdminJobDetail(JobRead):
    recruiter_name: Optional[str] = None
    recruiter: Optional[str] = None
    recruiter_email: Optional[str] = None
    recruiter_phone: Optional[str] = None
    company: Optional[Union[Dict[str, Any], str]] = None



class AdminRejectJobRequest(BaseModel):
    reason: str = Field(..., min_length=3, description="Mandatory reason for rejecting job requisition")
