import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database.base import Base


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    candidate_id = Column(
        String(50),
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    category = Column(String(50), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    link = Column(String(255), nullable=True)

    # Cross-reference IDs
    application_id = Column(String(50), nullable=True, index=True)
    interview_id = Column(String(50), nullable=True)
    job_id = Column(String(50), nullable=True)
    job_mela_id = Column(String(50), nullable=True)

    # State flags
    is_read = Column(Boolean, default=False, nullable=False, index=True)
    is_dismissed = Column(Boolean, default=False, nullable=False, index=True)

    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    read_at = Column(DateTime, nullable=True)
    dismissed_at = Column(DateTime, nullable=True)

    # Relationship to CandidateProfile
    candidate_profile = relationship("CandidateProfile", back_populates="notifications")
