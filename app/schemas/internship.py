from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class InternshipCreate(BaseModel):
    title: str = Field(..., min_length=3, description="Internship title")
    stipend_monthly: Optional[int] = None
    stipend: Optional[str] = None
    duration: Optional[str] = "6 Months"
    work_mode: Optional[str] = "Hybrid"
    workMode: Optional[str] = None
    location: Optional[str] = "Bengaluru, Karnataka"
    number_of_interns: Optional[int] = 1
    openings: Optional[int] = None
    description: Optional[str] = None


class InternshipRead(BaseModel):
    id: str
    internship_number: str
    company_id: str
    company_name: Optional[str] = None
    title: str
    stipend_monthly: int
    stipend: Optional[str] = None
    duration: str
    work_mode: str
    workMode: str
    location: Optional[str] = None
    number_of_interns: int
    openings: int
    description: Optional[str] = None
    status: str
    applicantsCount: int = 0
    candidate_count: int = 0
    candidates_count: int = 0
    rejection_reason: Optional[str] = None
    published_at: Optional[str] = None
    closed_at: Optional[str] = None
    postedOn: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class PaginatedInternshipResponse(BaseModel):
    items: List[InternshipRead]
    total: int
    page: int
    page_size: int
    total_pages: int


class AdminInternshipDetail(BaseModel):
    id: str
    internship_number: str
    title: str
    company_id: str
    company_name: str
    company: Optional[str] = None
    recruiter_name: Optional[str] = None
    recruiter: Optional[str] = None
    recruiter_email: Optional[str] = None
    recruiter_phone: Optional[str] = None
    stipend_monthly: int
    stipend: str
    duration: str
    work_mode: str
    location: Optional[str] = None
    number_of_interns: int
    description: Optional[str] = None
    status: str
    applicants_count: int = 0
    rejection_reason: Optional[str] = None
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None
    published_at: Optional[str] = None
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class AdminRejectInternshipRequest(BaseModel):
    reason: str = Field(..., min_length=3, description="Mandatory reason for rejection")
