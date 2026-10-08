from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class AdminModerationQueueResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    pending_recruiter_verifications: int
    pending_company_verifications: int
    pending_job_approvals: int
    pending_internship_approvals: int
    pending_job_mela_approvals: int
    open_moderation_reports: int
    total_pending: int


class AdminPlatformOverviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_candidates: int
    total_recruiters: int
    verified_companies: int
    active_jobs: int
    submitted_applications: int
    job_mela_registrations: int


class AdminModerationStreamItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    type: str
    name: str
    entity: str
    time: Optional[str] = None
    created_at: Optional[datetime] = None
    link: str


class AdminRecentAuditLogItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    action: str
    target: str
    actor: str
    adminUser: Optional[str] = None
    result: str = "SUCCESS"
    time: Optional[str] = None
    date: Optional[str] = None
    created_at: Optional[datetime] = None


class AdminDashboardResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    moderation_queue: AdminModerationQueueResponse
    platform_overview: AdminPlatformOverviewResponse
    pending_moderation_stream: List[AdminModerationStreamItemResponse]
    recent_audit_logs: List[AdminRecentAuditLogItemResponse]
