from datetime import datetime, timezone
from typing import List, Optional, Union
from pydantic import BaseModel, ConfigDict, computed_field, Field, field_validator


class NotificationItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    category: str
    title: str
    message: str
    link: Optional[str] = None
    application_id: Optional[str] = None
    interview_id: Optional[str] = None
    job_id: Optional[str] = None
    job_mela_id: Optional[str] = None
    is_read: bool = False
    is_dismissed: bool = False
    created_at: datetime
    read_at: Optional[datetime] = None
    dismissed_at: Optional[datetime] = None

    @computed_field
    @property
    def read(self) -> bool:
        """Alias for frontend compatibility (n.read)."""
        return self.is_read

    @computed_field
    @property
    def time(self) -> str:
        """Human-readable relative time representation."""
        now = datetime.now(timezone.utc)
        diff = now - (self.created_at if self.created_at.tzinfo else self.created_at.replace(tzinfo=timezone.utc))
        seconds = int(diff.total_seconds())
        if seconds < 60:
            return "Just now"
        minutes = seconds // 60
        if minutes < 60:
            return f"{minutes} min{'s' if minutes > 1 else ''} ago"
        hours = minutes // 60
        if hours < 24:
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        days = hours // 24
        if days < 7:
            return f"{days} day{'s' if days > 1 else ''} ago"
        return self.created_at.strftime("%d %b %Y")


class NotificationListResponse(BaseModel):
    items: List[NotificationItem]
    total: int
    unread_count: int


class UnreadCountResponse(BaseModel):
    unread_count: int


class MarkNotificationsRequest(BaseModel):
    notification_ids: Optional[List[str]] = None


class DismissNotificationsRequest(BaseModel):
    notification_ids: Optional[List[str]] = None


class NotificationActionResponse(BaseModel):
    status: str = "success"
    message: str
    updated_count: Optional[int] = None
    notification: Optional[NotificationItem] = None


class BulkNotificationDeleteRequest(BaseModel):
    notification_ids: List[Union[str, int]] = Field(..., min_length=1, description="List of notification IDs to delete")

    @field_validator("notification_ids")
    @classmethod
    def validate_ids(cls, v):
        if not v or len(v) == 0:
            raise ValueError("notification_ids must contain at least 1 ID")
        cleaned = []
        seen = set()
        for item in v:
            val = str(item).strip()
            if val and val not in seen:
                seen.add(val)
                cleaned.append(val)
        if not cleaned:
            raise ValueError("notification_ids must contain at least 1 valid ID")
        return cleaned


class NotificationDeleteResponse(BaseModel):
    message: str = "Notification deleted successfully."


class BulkNotificationDeleteResponse(BaseModel):
    message: str = "Notifications deleted successfully."
    deleted_count: int

