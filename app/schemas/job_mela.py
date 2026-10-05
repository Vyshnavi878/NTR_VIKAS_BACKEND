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
    target_hires: int = 1
    booth_number: Optional[str] = None
    status: str = "APPROVED"
