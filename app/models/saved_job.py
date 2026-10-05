import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database.base import Base


class SavedJob(Base):
    __tablename__ = "saved_jobs"

    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    candidate_profile_id = Column(
        String(50),
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_id = Column(String(50), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    company_name = Column(String(200), nullable=False)
    company_verified = Column(Boolean, default=True, nullable=False)
    location = Column(String(200), nullable=False)
    salary = Column(String(100), nullable=True)
    experience = Column(String(100), nullable=True)
    employment_type = Column(String(100), default="Full-time", nullable=False)
    work_mode = Column(String(50), default="Hybrid", nullable=False)
    skills = Column(Text, nullable=True)
    is_applied = Column(Boolean, default=False, nullable=False)
    saved_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("candidate_profile_id", "job_id", name="uq_candidate_job_save"),
    )

    # Relationship to CandidateProfile
    candidate_profile = relationship("CandidateProfile", back_populates="saved_jobs")
