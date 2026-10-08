from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from app.database.base import Base


class PlatformSettings(Base):
    __tablename__ = "platform_settings"

    id = Column(Integer, primary_key=True, default=1)
    platform_display_name = Column(
        String(255),
        nullable=False,
        default="NTR VIKASA State Job Portal Administration",
    )
    primary_support_email = Column(
        String(255),
        nullable=False,
        default="support@ntrvikasa.com",
    )
    grievance_redressal_email = Column(
        String(255),
        nullable=False,
        default="grievance@ntrvikasa.com",
    )
    mandatory_recruiter_legal_verification = Column(
        Boolean,
        nullable=False,
        default=True,
    )
    pre_publish_job_moderation_queue = Column(
        Boolean,
        nullable=False,
        default=True,
    )
    strict_zero_fee_candidate_rule = Column(
        Boolean,
        nullable=False,
        default=True,
    )
    platform_maintenance_mode = Column(
        Boolean,
        nullable=False,
        default=False,
    )
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_by = Column(
        String(150),
        nullable=True,
    )
