import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database.base import Base


class Job(Base):
    __tablename__ = "jobs"

    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    job_id = Column(String(50), index=True, nullable=False)
    job_number = Column(String(50), index=True, nullable=True)
    recruiter_id = Column(
        String(50),
        ForeignKey("recruiter_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    company_id = Column(String(50), index=True, nullable=True)
    created_by = Column(String(150), nullable=True)
    company_name = Column(String(200), index=True, nullable=False)
    title = Column(String(200), nullable=False)
    department = Column(String(100), default="Engineering", nullable=True)
    job_type = Column(String(100), default="Full-time", nullable=False)
    work_mode = Column(String(50), default="Hybrid", nullable=False)
    location = Column(String(200), default="Bengaluru, Karnataka", nullable=False)
    experience = Column(String(100), default="3-5 years", nullable=True)
    salary = Column(String(100), nullable=True)
    salary_min = Column(Integer, nullable=True)
    salary_max = Column(Integer, nullable=True)
    salary_currency = Column(String(10), default="INR", nullable=True)
    openings = Column(Integer, default=1, nullable=False)
    status = Column(String(50), default="PUBLISHED", index=True, nullable=False)
    description = Column(Text, nullable=True)
    responsibilities = Column(Text, nullable=True)
    requirements = Column(Text, nullable=True)
    qualifications = Column(Text, nullable=True)
    skills = Column(Text, nullable=True)
    deadline = Column(String(100), nullable=True)
    posted_at = Column(DateTime, nullable=True)
    closed_at = Column(DateTime, nullable=True)
    approved_by = Column(String(150), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    recruiter = relationship("RecruiterProfile", back_populates="jobs")
    job_skills = relationship("JobSkill", back_populates="job", cascade="all, delete-orphan")


class JobSkill(Base):
    __tablename__ = "job_skills"

    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    job_id = Column(
        String(50),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    skill_name = Column(String(100), nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationship
    job = relationship("Job", back_populates="job_skills")
