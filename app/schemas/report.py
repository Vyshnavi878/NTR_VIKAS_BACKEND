from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field


class ReportEntityInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    type: str = "RECRUITER"
    name: str = "Target Entity"
    id: Optional[str] = None


class ReporterInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: Optional[str] = None
    name: str = "Platform User"
    email: Optional[str] = None
    user_type: str = "CANDIDATE"


class ReportedUserInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: Optional[str] = None
    name: Optional[str] = None
    email: Optional[str] = None
    user_type: str = "RECRUITER"


class ReportCreate(BaseModel):
    report_type: str = Field(..., description="Report category code or label")
    reported_entity_type: str = Field("JOB", description="Type of entity reported (JOB, INTERNSHIP, JOB_MELA, COMPANY, CANDIDATE_PROFILE, RECRUITER_PROFILE, MESSAGE, APPLICATION, OTHER)")
    reported_entity_id: Optional[str] = Field(None, description="Identifier of the entity")
    reported_user_id: Optional[str] = Field(None, description="User ID of the violator if known")
    reported_user_type: Optional[str] = Field(None, description="CANDIDATE or RECRUITER")
    reported_entity_name: Optional[str] = Field(None, description="Display name of target entity")
    subject: Optional[str] = Field(None, description="Short subject or title")
    description: str = Field(..., description="Full grievance description or evidence details")


class ReportResolveRequest(BaseModel):
    admin_notes: Optional[str] = Field(None, description="Administrative notes regarding the investigation/action")
    resolution_reason: Optional[str] = Field("POLICY_VIOLATION_CONFIRMED", description="Categorical reason for resolution")


class ReportDismissRequest(BaseModel):
    admin_notes: Optional[str] = Field(None, description="Administrative justification for dismissing the report")
    resolution_reason: Optional[str] = Field("INSUFFICIENT_EVIDENCE", description="Categorical reason for dismissal")


class ReportItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    report_number: str
    report_type: str
    report_type_label: str
    reported_entity: ReportEntityInfo
    reported_user_type: str
    reported_user: Optional[ReportedUserInfo] = None
    reporter: ReporterInfo
    subject: Optional[str] = None
    description: Optional[str] = None
    details: Optional[str] = None  # UI alias for description
    reason: Optional[str] = None   # UI alias for description
    date: Optional[str] = None     # YYYY-MM-DD format for UI
    status: str
    action_taken: Optional[str] = None
    admin_notes: Optional[str] = None
    resolution_reason: Optional[str] = None
    resolved_at: Optional[datetime] = None
    dismissed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class ReportDetailResponse(ReportItemResponse):
    pass


class ReportListResponse(BaseModel):
    items: List[ReportItemResponse]
    page: int
    page_size: int
    total: int
    total_pages: int


class ReportSummaryResponse(BaseModel):
    all: int
    pending: int
    resolved: int
    dismissed: int
    open_complaints: int


class ReportActionResponse(BaseModel):
    message: str
    report: Optional[ReportItemResponse] = None
