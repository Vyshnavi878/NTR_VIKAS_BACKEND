from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field


class PublicCompanyItem(BaseModel):
    id: str
    name: str
    company_name: Optional[str] = None
    logo: Optional[str] = None
    logo_url: Optional[str] = None
    company_logo_path: Optional[str] = None
    industry: str = "Information Technology"
    location: str = "Bengaluru, Karnataka"
    tagline: Optional[str] = None
    description: Optional[str] = None
    website: Optional[str] = None
    size: Optional[str] = "1000+ employees"
    employees: Optional[str] = "1000+"
    company_size: Optional[str] = "1000+ employees"
    openJobs: int = 0
    open_jobs: int = 0
    open_jobs_count: int = 0
    openInternships: int = 0
    open_internships: int = 0
    open_internships_count: int = 0
    rating: Optional[float] = None
    tech_stack: Optional[List[str]] = None
    verified: bool = True

    model_config = ConfigDict(from_attributes=True, extra="ignore")



class PaginatedCompanyResponse(BaseModel):
    items: List[PublicCompanyItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class AdminCompanyVerificationItem(BaseModel):
    id: str
    name: str
    company_name: str
    recruiter_name: str
    recruiter: str
    recruiter_email: str
    recruiter_phone: str
    designation: str
    industry: str
    company_size: str
    location: str
    address: str
    website: str
    description: str
    status: str
    verification_status: str
    verificationStatus: str
    rejection_reason: Optional[str] = None
    rejectionReason: Optional[str] = None
    submitted_at: Optional[str] = None
    reviewed_at: Optional[str] = None
    reviewed_by: Optional[str] = None
    incorporation_document_path: Optional[str] = None
    recruiter_authorization_document_path: Optional[str] = None
    company_logo_path: Optional[str] = None
    open_jobs: int = 0
    openJobs: int = 0

    model_config = ConfigDict(from_attributes=True, extra="ignore")


class CompanyVerificationDecision(BaseModel):
    reason: Optional[str] = Field(None, description="Reason for rejection (mandatory when rejecting)")


class RecruiterCompanyProfileResponse(BaseModel):
    id: str
    company_name: str
    name: str
    industry: str
    primary_industry: str
    tagline: Optional[str] = None
    official_website: Optional[str] = None
    website: Optional[str] = None
    careers_email: Optional[str] = None
    email: Optional[str] = None
    corporate_email: Optional[str] = None
    contact_phone: Optional[str] = None
    phone: Optional[str] = None
    company_phone: Optional[str] = None
    company_size: str
    size: str
    location: str
    headquarters_city_state: str
    registered_office_address: str
    address: str
    about_company: str
    description: str
    company_description: str
    logo_url: Optional[str] = None
    logo: Optional[str] = None
    company_logo_path: Optional[str] = None
    verification_status: str
    status: str
    verified: bool
    cin_number: Optional[str] = None
    cinNumber: Optional[str] = None
    gst_number: Optional[str] = None
    gstNumber: Optional[str] = None
    rejection_reason: Optional[str] = None

    model_config = ConfigDict(from_attributes=True, extra="ignore")


class RecruiterCompanyProfileUpdate(BaseModel):
    company_name: Optional[str] = Field(None, min_length=2, max_length=200, description="Official company legal name")
    name: Optional[str] = Field(None, min_length=2, max_length=200, description="Alias for company_name")
    industry: Optional[str] = Field(None, min_length=2, max_length=100, description="Industry sector")
    primary_industry: Optional[str] = Field(None, min_length=2, max_length=100, description="Alias for industry")
    tagline: Optional[str] = Field(None, max_length=300, description="Corporate tagline or slogan")
    official_website: Optional[str] = Field(None, max_length=255, description="Official website URL")
    website: Optional[str] = Field(None, max_length=255, description="Alias for official_website")
    careers_email: Optional[str] = Field(None, max_length=150, description="Careers or corporate email")
    email: Optional[str] = Field(None, max_length=150, description="Alias for careers_email")
    contact_phone: Optional[str] = Field(None, max_length=30, description="Company contact phone")
    phone: Optional[str] = Field(None, max_length=30, description="Alias for contact_phone")
    company_size: Optional[str] = Field(None, max_length=100, description="Company size / employee bracket")
    size: Optional[str] = Field(None, max_length=100, description="Alias for company_size")
    registered_office_address: Optional[str] = Field(None, max_length=1000, description="Registered office address")
    address: Optional[str] = Field(None, max_length=1000, description="Alias for registered_office_address")
    about_company: Optional[str] = Field(None, max_length=3000, description="Company overview / description")
    description: Optional[str] = Field(None, max_length=3000, description="Alias for about_company")
    location: Optional[str] = Field(None, max_length=150, description="Headquarters city & state")
    cin_number: Optional[str] = Field(None, max_length=50, description="Corporate Identification Number (CIN)")
    cinNumber: Optional[str] = Field(None, max_length=50, description="Alias for cin_number")
    gst_number: Optional[str] = Field(None, max_length=50, description="Goods and Services Tax Number (GST)")
    gstNumber: Optional[str] = Field(None, max_length=50, description="Alias for gst_number")

    model_config = ConfigDict(extra="ignore")


class CompanyLogoUploadResponse(BaseModel):
    logo_url: str
    message: str = "Company logo uploaded successfully."
