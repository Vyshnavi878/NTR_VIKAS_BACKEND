import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database.base import Base


class CandidateSkill(Base):
    __tablename__ = "candidate_skills"

    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    candidate_profile_id = Column(
        String(50),
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    skill_name = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Avoid duplicate skills for the same candidate
    __table_args__ = (
        UniqueConstraint("candidate_profile_id", "skill_name", name="uq_candidate_skill"),
    )

    candidate_profile = relationship("CandidateProfile", back_populates="skills")


class CandidateExperience(Base):
    __tablename__ = "candidate_experiences"

    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    candidate_profile_id = Column(
        String(50),
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role = Column(String(150), nullable=False)
    company = Column(String(150), nullable=False)
    location = Column(String(150), nullable=True)
    duration = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    candidate_profile = relationship("CandidateProfile", back_populates="experiences")


class CandidateEducation(Base):
    __tablename__ = "candidate_educations"

    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    candidate_profile_id = Column(
        String(50),
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    degree = Column(String(150), nullable=False)
    institution = Column(String(200), nullable=False)
    duration = Column(String(100), nullable=True)
    score = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    candidate_profile = relationship("CandidateProfile", back_populates="educations")


class CandidateCertification(Base):
    __tablename__ = "candidate_certifications"

    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    candidate_profile_id = Column(
        String(50),
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(200), nullable=False)
    issuer = Column(String(200), nullable=False)
    year = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    candidate_profile = relationship("CandidateProfile", back_populates="certifications")


class CandidateProject(Base):
    __tablename__ = "candidate_projects"

    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    candidate_profile_id = Column(
        String(50),
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title = Column(String(200), nullable=False)
    tech = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    link = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    candidate_profile = relationship("CandidateProfile", back_populates="projects")


class CandidateResume(Base):
    __tablename__ = "candidate_resumes"

    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    candidate_profile_id = Column(
        String(50),
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(String(50), nullable=True)
    file_type = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    candidate_profile = relationship("CandidateProfile", back_populates="resumes")
