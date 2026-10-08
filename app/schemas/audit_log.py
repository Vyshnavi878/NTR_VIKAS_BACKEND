from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field


class AuditLogItem(BaseModel):
    id: str = Field(..., description="Unique audit event ID")
    action: str = Field(..., description="Audit action name")
    actor: str = Field(..., description="Admin or user identifier who performed the action")
    admin: Optional[str] = Field(None, description="Display name or email of admin/user")
    user: Optional[str] = Field(None, description="Alias for admin/user")
    target: Optional[str] = Field(None, description="Target entity or system component")
    entity: Optional[str] = Field(None, description="Target entity classification")
    entity_id: Optional[str] = Field(None, description="Target entity ID")
    date: str = Field(..., description="Formatted event date (e.g. 2026-10-08)")
    time: str = Field(..., description="Formatted event time (e.g. 02:15 PM)")
    result: str = Field("SUCCESS", description="Operation result status: SUCCESS or FAILED")
    ip_address: Optional[str] = Field(None, description="Client IP address")
    user_agent: Optional[str] = Field(None, description="Client browser / user agent")
    metadata_json: Optional[str] = Field(None, description="JSON metadata containing diffs or context")
    timestamp: datetime = Field(..., description="UTC ISO timestamp of the event")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )


class PaginatedAuditLogResponse(BaseModel):
    items: List[AuditLogItem] = Field(default_factory=list, description="Paginated list of audit records")
    total: int = Field(..., ge=0, description="Total count of matching records")
    page: int = Field(1, ge=1, description="Current page number")
    page_size: int = Field(10, ge=1, le=100, description="Page size limit")
    total_pages: int = Field(1, ge=1, description="Total number of available pages")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )
