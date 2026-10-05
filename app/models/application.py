import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, Integer
from sqlalchemy.orm import relationship
from app.database.base import Base


class CandidateApplication(Base):
    __tablename__ = "candidate_applications"

    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    application_number = Column(String(50), unique=True, index=True, nullable=False)
    candidate_profile_id = Column(
        String(50),
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_id = Column(String(50), nullable=False, index=True)
    job_title = Column(String(200), nullable=False)
    company_name = Column(String(200), nullable=False)
    location = Column(String(200), nullable=False)
    salary = Column(String(100), nullable=True)
    employment_type = Column(String(100), default="Full-time", nullable=False)
    work_mode = Column(String(50), default="On-site", nullable=False)
    application_type = Column(String(100), default="Direct Job Application", nullable=False)
    
    # Optional Job Mela fields
    mela_id = Column(String(50), nullable=True)
    mela_title = Column(String(255), nullable=True)
    event_number = Column(String(50), nullable=True)
    company_sequence = Column(String(50), nullable=True)
    application_sequence = Column(String(50), nullable=True)
    
    # Status
    status = Column(String(50), default="APPLIED", nullable=False, index=True)
    applied_date = Column(String(50), nullable=True)
    applied_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Candidate submission details
    cover_letter = Column(Text, nullable=True)
    additional_info = Column(Text, nullable=True)
    resume_name = Column(String(255), nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    candidate_profile = relationship("CandidateProfile", back_populates="applications")
    timeline_events = relationship(
        "ApplicationTimelineEvent",
        back_populates="application",
        cascade="all, delete-orphan",
        order_by="ApplicationTimelineEvent.step_order",
    )


class ApplicationTimelineEvent(Base):
    __tablename__ = "application_timeline_events"

    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    application_id = Column(
        String(50),
        ForeignKey("candidate_applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    stage = Column(String(100), nullable=False)
    status = Column(String(50), nullable=False)
    label = Column(String(255), nullable=True)
    date = Column(String(100), nullable=True)
    completed = Column(Boolean, default=False, nullable=False)
    current = Column(Boolean, default=False, nullable=False)
    step_order = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationship
    application = relationship("CandidateApplication", back_populates="timeline_events")
