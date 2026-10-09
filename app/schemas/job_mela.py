from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class JobMelaRead(BaseModel):
    id: str
    mela_number: str
    title: str
    description: Optional[str] = None
    event_date: str
    start_time: Optional[str] = "09:00 AM"
    end_time: Optional[str] = "05:30 PM"
    venue: str
    city: str
    district: Optional[str] = None
    status: str = "PUBLISHED"

    model_config = ConfigDict(from_attributes=True)

class RecruiterJobMelaItem(BaseModel):
    id: str
    participation_id: Optional[str] = None
    mela_number: str
    title: str
    date: str
    time: str
    venue: str
    city: str
    district: Optional[str] = None
    state: str = "Andhra Pradesh"
    participation_status: str = "NOT_REGISTERED"
    status: str = "NOT_REGISTERED"
    booth_number: Optional[str] = None
    boothNumber: Optional[str] = None
    booth_location: Optional[str] = None
    positions: Optional[str] = None
    showcasedPositions: Optional[List[str]] = None
    target_hires: int = 0
    expectedHires: int = 0
    registeredCandidatesAtBooth: int = 0
    candidatesCount: int = 0
    spotInterviewsConducted: int = 0
    interviewsCount: int = 0
    spotOffersGiven: int = 0
    spotOffers: int = 0
    registered_at: Optional[str] = None


class JobMelaParticipationRequest(BaseModel):
    job_mela_id: Optional[str] = None
    title: Optional[str] = None
    openings: Optional[str] = None
    positions: Optional[str] = None
    target_hires: Optional[int] = 1
    expectedHires: Optional[int] = None
    expected_hires: Optional[int] = None


class JobMelaParticipationResponse(BaseModel):
    id: str
    job_mela_id: str
    mela_title: str
    company_id: str
    company_name: str
    openings: Optional[str] = None
    target_hires: int = 1
    status: str = "PENDING"
    booth_number: Optional[str] = None
    registered_at: str
    message: str = "Participation request submitted successfully and is pending administrative review."


class AdminParticipationItem(BaseModel):
    id: str
    participation_id: str
    company_id: str
    company_name: str
    companyName: str
    recruiter_name: str
    recruiterName: str
    recruiter_phone: str
    recruiterPhone: str
    job_mela_id: str
    event_name: str
    eventName: str
    event_date: str
    status: str
    allocated_booth: Optional[str] = None
    allocatedBooth: Optional[str] = None
    openings: Optional[str] = None
    hiring_positions: List[str] = []
    hiringPositions: List[str] = []
    target_hires: int = 1
    expected_hires: int = 1
    expectedHires: int = 1
    registered_at: str
    requested_date: str
    requestedDate: str
    rejection_reason: Optional[str] = None


class AdminApproveParticipationRequest(BaseModel):
    booth_number: Optional[str] = None
    booth_location: Optional[str] = None


class AdminRejectParticipationRequest(BaseModel):
    rejection_reason: str = Field(..., min_length=3, description="Mandatory reason for rejecting participation")


class CandidateMelaCompanyItem(BaseModel):
    company_id: str
    company_name: str
    industry: Optional[str] = None
    openings: Optional[str] = None
    positions_list: List[str] = []
    target_hires: int = 1
    booth_number: Optional[str] = None
    booth_location: Optional[str] = None
    status: str = "APPROVED"


class CandidateJobMelaCard(BaseModel):
    id: str
    mela_number: str
    melaId: Optional[str] = None
    title: str
    event: Optional[str] = None
    description: Optional[str] = None
    event_date: str
    date: Optional[str] = None
    start_time: Optional[str] = "09:00 AM"
    end_time: Optional[str] = "05:30 PM"
    time: Optional[str] = "09:00 AM - 05:30 PM"
    venue: str
    city: str
    district: Optional[str] = None
    state: str = "Andhra Pradesh"
    status: str = "PUBLISHED"
    organizer_type: str = "ADMIN"
    companies_count: int = 0
    participating_companies_count: int = 0
    candidates_count: int = 0
    candidate_count: int = 0
    image_url: Optional[str] = None
    flyer_url: Optional[str] = None
    poster_url: Optional[str] = None
    registration_required: bool = True
    registration_deadline: Optional[str] = None
    candidate_registered: bool = False
    candidate_pass_id: Optional[str] = None
    candidate_registration_status: Optional[str] = None
    participating_companies: List[CandidateMelaCompanyItem] = []

    model_config = ConfigDict(from_attributes=True)


class JobMelaCounts(BaseModel):
    all: int = 0
    upcoming: int = 0
    ongoing: int = 0
    completed: int = 0


class CandidateJobMelasListResponse(BaseModel):
    items: List[CandidateJobMelaCard]
    counts: JobMelaCounts
    total: int
    page: int
    page_size: int
    total_pages: int


class CandidateJobMelaRegistrationRequest(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    resume: Optional[str] = None
    time_slot: Optional[str] = "Morning Session (09:00 AM - 01:00 PM)"


class CandidateJobMelaRegistrationItem(BaseModel):
    id: str
    registration_id: str
    job_mela_id: str
    mela_id: str
    melaId: Optional[str] = None
    mela_number: str
    title: str
    event: Optional[str] = None
    event_title: str
    event_date: str
    date: Optional[str] = None
    start_time: str
    end_time: str
    time: str
    venue: str
    city: str
    state: str = "Andhra Pradesh"
    pass_id: str
    passId: Optional[str] = None
    entry_token: str
    status: str = "CONFIRMED"
    gate_number: str = "Gate 2 (General Fast-Track)"
    gateNumber: Optional[str] = None
    time_slot: str
    timeSlot: Optional[str] = None
    qr_code_url: str
    entry_qr_code: str
    entryQrCode: Optional[str] = None
    registered_at: str
    registered_on: str
    registeredOn: Optional[str] = None
    application_id: Optional[str] = None
    candidate_name: Optional[str] = None
    candidate_email: Optional[str] = None
    candidate_phone: Optional[str] = None


class CandidateJobMelaApplyCompanyRequest(BaseModel):
    company_name: str
    company_id: Optional[str] = None
    company_entry_id: Optional[str] = None
    role: str
    salary: Optional[str] = None
    location: Optional[str] = None
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    resume: Optional[str] = None
    skills: Optional[str] = None
    experience: Optional[str] = None
    education: Optional[str] = None
    cover_note: Optional[str] = None


class CandidateJobMelaApplyCompanyResponse(BaseModel):
    id: str
    application_number: str
    job_mela_id: str
    company_name: str
    job_title: str
    status: str = "APPLIED"
    applied_date: str
    message: str = "Application submitted successfully for Job Mela interview."


# ── Admin Job Mela Schemas ──────────────────────────────────────────────────

class AdminJobMelaCompanyItem(BaseModel):
    id: str
    companyId: Optional[str] = None
    company: str
    recruiter: Optional[str] = None
    position: Optional[str] = None
    qualification: Optional[str] = None
    experience: Optional[str] = None
    salary: Optional[str] = None
    vacancies: int = 15
    applications: int = 0
    location: Optional[str] = None
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AdminJobMelaItem(BaseModel):
    id: str
    mela_number: Optional[str] = None
    event: str
    title: str
    description: Optional[str] = None
    date: str
    startTime: Optional[str] = "09:00 AM"
    endTime: Optional[str] = "05:30 PM"
    time: Optional[str] = "09:00 AM - 05:30 PM"
    regStartDate: Optional[str] = None
    regEndDate: Optional[str] = None
    maxCapacity: Optional[int] = 5000
    capacity: Optional[int] = 5000
    venue: str
    city: str
    district: Optional[str] = None
    state: Optional[str] = "Andhra Pradesh"
    location: Optional[str] = None
    address: Optional[str] = None
    organizer: Optional[str] = None
    client: Optional[str] = None
    createdForClient: Optional[bool] = False
    createdByAdmin: bool = True
    status: str
    companiesCount: int = 0
    vacanciesCount: int = 0
    registeredCandidatesCount: int = 0
    banner: Optional[str] = None
    posterImage: Optional[str] = None
    image: Optional[str] = None
    flyer_url: Optional[str] = None
    participatingCompanies: List[AdminJobMelaCompanyItem] = []
    eligibleMandals: Optional[List[str]] = None
    eligibleVillages: Optional[str] = None
    eligibleQualifications: Optional[List[str]] = None

    model_config = ConfigDict(from_attributes=True)


class AdminCreateJobMelaRequest(BaseModel):
    title: str
    description: Optional[str] = None
    date: str
    startTime: Optional[str] = "09:00"
    endTime: Optional[str] = "18:00"
    venue: str
    address: Optional[str] = None
    city: str
    state: Optional[str] = "Andhra Pradesh"
    regStartDate: Optional[str] = None
    regEndDate: Optional[str] = None
    maxCapacity: Optional[int] = 3500
    createdForClient: Optional[bool] = False
    client: Optional[str] = None
    clientId: Optional[str] = None
    clientContactPerson: Optional[str] = None
    clientContactPhone: Optional[str] = None
    eligibleMandals: Optional[List[str]] = None
    eligibleVillages: Optional[str] = None
    eligibleQualifications: Optional[List[str]] = None
    banner: Optional[str] = None
    posterImage: Optional[str] = None
    image: Optional[str] = None
    status: Optional[str] = "APPROVED"
    participatingCompanies: Optional[List[dict]] = []


class AdminUpdateJobMelaStatusRequest(BaseModel):
    status: str


class AdminJobMelaRequestItem(BaseModel):
    id: str
    request_number: Optional[str] = None
    event: str
    title: str
    description: Optional[str] = None
    organizer: str
    company: Optional[str] = None
    requestingOrganization: Optional[str] = None
    date: str
    time: Optional[str] = "09:00 AM - 05:00 PM"
    venue: str
    location: Optional[str] = None
    city: str
    state: Optional[str] = "Andhra Pradesh"
    address: Optional[str] = None
    requestDate: str
    createdAt: Optional[str] = None
    status: str
    capacity: Optional[int] = 2000
    maxCapacity: Optional[int] = 2000
    vacancies: Optional[int] = 500
    contactPerson: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    rejectionReason: Optional[str] = None
    linkedJobMelaId: Optional[str] = None
    participatingCompanies: Optional[List[dict]] = []

    model_config = ConfigDict(from_attributes=True)


class AdminApproveMelaRequest(BaseModel):
    reviewNotes: Optional[str] = None
    autoPublish: Optional[bool] = True


class AdminRejectMelaRequest(BaseModel):
    rejection_reason: Optional[str] = None
    reason: Optional[str] = None


class AdminJobMelaMetricsResponse(BaseModel):
    totalRegisteredCandidates: int = 0
    totalEventCapacity: int = 0
    turnoutFillRate: int = 0
    totalEvents: int = 0
    totalAdminMelas: int = 0
    totalRequests: int = 0
    pendingRequests: int = 0
    approvedRequests: int = 0
    rejectedRequests: int = 0
    totalVacancies: int = 0


