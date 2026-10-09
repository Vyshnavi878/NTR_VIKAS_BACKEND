import uuid
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, EmailStr
from datetime import datetime


class AdminRecruiterItem(BaseModel):
    id: str
    user_id: Optional[str] = None
    name: str
    recruiter_name: Optional[str] = None
    email: str
    work_email: Optional[str] = None
    phone: Optional[str] = None
    mobile_phone: Optional[str] = None
    designation: Optional[str] = "Talent Acquisition Manager"
    company: str
    company_name: Optional[str] = None
    company_id: Optional[str] = None
    industry: Optional[str] = "Information Technology & Services"
    location: Optional[str] = "Vijayawada, NTR District"
    district: Optional[str] = "NTR District"
    mandal: Optional[str] = "Vijayawada Urban"
    village: Optional[str] = None
    registration_date: Optional[str] = None
    registrationDate: Optional[str] = None
    created_at: Optional[str] = None
    verification_status: str = "VERIFIED"  # VERIFIED | PENDING | REJECTED | SUSPENDED
    verificationStatus: Optional[str] = "VERIFIED"
    account_status: str = "ACTIVE"  # ACTIVE | SUSPENDED
    accountStatus: Optional[str] = "ACTIVE"
    posted_jobs_count: int = 0
    postedJobsCount: Optional[int] = 0
    open_jobs: Optional[int] = 0
    open_internships: Optional[int] = 0
    applications_count: Optional[int] = 0
    onboarded_by: Optional[str] = None

    class Config:
        from_attributes = True


class PaginatedAdminRecruiterResponse(BaseModel):
    items: List[AdminRecruiterItem]
    total: int
    page: int
    page_size: int
    total_pages: int
    verified_count: int
    pending_count: int
    suspended_count: int


class AdminCreateRecruiterRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=150, description="Recruiter full name")
    email: str = Field(..., description="Official work email")
    phone: Optional[str] = Field(None, max_length=25, description="Mobile phone number")
    designation: Optional[str] = Field("Talent Acquisition Manager", max_length=150)
    company_type: Optional[str] = Field("EXISTING", description="'EXISTING' or 'NEW'")
    company: Optional[str] = Field(None, description="Company name or ID")
    company_id: Optional[str] = Field(None, description="Existing Company Profile ID")
    selected_company: Optional[str] = Field(None, description="Selected existing company name")
    new_company_name: Optional[str] = Field(None, description="New company name if company_type is NEW")
    industry: Optional[str] = Field("Information Technology & Services", max_length=100)
    location: Optional[str] = Field("Vijayawada, NTR District", max_length=200)
    district: Optional[str] = Field("NTR District", max_length=100)
    mandal: Optional[str] = Field("Vijayawada Urban", max_length=100)
    village: Optional[str] = Field(None, max_length=100)


class AdminRecruiterVerificationUpdate(BaseModel):
    status: str = Field(..., description="Status: VERIFIED, REJECTED, PENDING")
    notes: Optional[str] = Field(None, description="Administrative audit notes")
    reason: Optional[str] = Field(None, description="Rejection reason if applicable")


class AdminRecruiterAccountStatusUpdate(BaseModel):
    status: str = Field(..., description="Status: ACTIVE or SUSPENDED")
    reason: Optional[str] = Field(None, description="Reason for suspension or activation")


class AdminRecruiterDetail(AdminRecruiterItem):
    company_website: Optional[str] = None
    company_size: Optional[str] = None
    company_type: Optional[str] = None
    registered_office_address: Optional[str] = None
    company_description: Optional[str] = None
    cin_number: Optional[str] = None
    gst_number: Optional[str] = None
    company_logo_path: Optional[str] = None
    rejection_reason: Optional[str] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[str] = None
    onboarded_by_admin_id: Optional[str] = None
    jobs: List[Dict[str, Any]] = []
    internships: List[Dict[str, Any]] = []
    audit_events: List[Dict[str, Any]] = []
