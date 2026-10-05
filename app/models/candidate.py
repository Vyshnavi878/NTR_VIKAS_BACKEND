import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database.base import Base


class CandidateProfile(Base):
    __tablename__ = "candidate_profiles"

    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(
        String(50),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    name = Column(String(150), nullable=False)
    phone = Column(String(20), index=True, nullable=True)
    aadhaar_number = Column(String(20), unique=True, index=True, nullable=False)
    district = Column(String(100), default="NTR District")
    mandal = Column(String(100), default="Vijayawada Urban")
    village = Column(String(100), nullable=True)
    qualification_level = Column(String(50), default="10TH")
    reference_admin = Column(String(150), nullable=True)
    headline = Column(String(255), nullable=True)
    bio = Column(Text, nullable=True)
    profile_completion = Column(Integer, default=35)
    verified = Column(Boolean, default=True)

    # Personal / Social URLs & Location
    location = Column(String(200), nullable=True)
    linkedin_url = Column(String(255), nullable=True)
    github_url = Column(String(255), nullable=True)
    portfolio_url = Column(String(255), nullable=True)
    avatar = Column(Text, nullable=True)

    # Career Preferences
    total_experience = Column(String(100), nullable=True)
    current_salary = Column(String(100), nullable=True)
    expected_salary_min = Column(String(100), nullable=True)
    expected_salary_max = Column(String(100), nullable=True)
    expected_salary = Column(String(150), nullable=True)
    work_mode = Column(String(50), nullable=True)
    employment_type = Column(String(50), nullable=True)
    preferred_job_roles = Column(Text, nullable=True)
    preferred_locations = Column(Text, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    user = relationship("User", back_populates="candidate_profile")
    saved_jobs = relationship(
        "SavedJob",
        back_populates="candidate_profile",
        cascade="all, delete-orphan",
    )
    applications = relationship(
        "CandidateApplication",
        back_populates="candidate_profile",
        cascade="all, delete-orphan",
    )
    support_tickets = relationship(
        "SupportTicket",
        back_populates="candidate_profile",
        cascade="all, delete-orphan",
    )
    skills = relationship(
        "CandidateSkill",
        back_populates="candidate_profile",
        cascade="all, delete-orphan",
    )
    experiences = relationship(
        "CandidateExperience",
        back_populates="candidate_profile",
        cascade="all, delete-orphan",
        order_by="CandidateExperience.created_at.desc()",
    )
    educations = relationship(
        "CandidateEducation",
        back_populates="candidate_profile",
        cascade="all, delete-orphan",
        order_by="CandidateEducation.created_at.desc()",
    )
    certifications = relationship(
        "CandidateCertification",
        back_populates="candidate_profile",
        cascade="all, delete-orphan",
        order_by="CandidateCertification.created_at.desc()",
    )
    projects = relationship(
        "CandidateProject",
        back_populates="candidate_profile",
        cascade="all, delete-orphan",
        order_by="CandidateProject.created_at.desc()",
    )
    resumes = relationship(
        "CandidateResume",
        back_populates="candidate_profile",
        cascade="all, delete-orphan",
        order_by="CandidateResume.created_at.desc()",
    )
    settings = relationship(
        "CandidateSettings",
        back_populates="candidate_profile",
        uselist=False,
        cascade="all, delete-orphan",
    )
    notifications = relationship(
        "Notification",
        back_populates="candidate_profile",
        cascade="all, delete-orphan",
        order_by="Notification.created_at.desc()",
    )
    interviews = relationship(
        "Interview",
        back_populates="candidate",
        cascade="all, delete-orphan",
        order_by="Interview.scheduled_at.desc()",
    )
