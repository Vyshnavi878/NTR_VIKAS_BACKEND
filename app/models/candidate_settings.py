import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database.base import Base


class CandidateSettings(Base):
    __tablename__ = "candidate_settings"

    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    candidate_id = Column(
        String(50),
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    # Notification Preferences
    email_job_application_alerts = Column(Boolean, default=True, nullable=False)
    sms_whatsapp_notifications = Column(Boolean, default=True, nullable=False)
    upcoming_interview_reminders = Column(Boolean, default=True, nullable=False)
    weekly_job_recommendation_digest = Column(Boolean, default=False, nullable=False)

    # Profile Visibility & Privacy Preferences
    visible_in_recruiter_talent_search = Column(Boolean, default=True, nullable=False)
    direct_recruiter_messages = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationship to CandidateProfile
    candidate_profile = relationship("CandidateProfile", back_populates="settings")
