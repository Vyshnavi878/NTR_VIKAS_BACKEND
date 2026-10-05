import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database.base import Base


class Internship(Base):
    __tablename__ = "internships"

    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    internship_number = Column(String(50), unique=True, index=True, nullable=False)
    company_id = Column(
        String(50),
        ForeignKey("recruiter_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_by = Column(
        String(50),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    title = Column(String(255), nullable=False, index=True)
    stipend_monthly = Column(Integer, nullable=False, default=15000)
    stipend = Column(String(100), nullable=True)
    duration = Column(String(100), nullable=False, default="6 Months")
    work_mode = Column(String(50), nullable=False, default="Hybrid")
    location = Column(String(255), nullable=True, default="Bengaluru, Karnataka")
    number_of_interns = Column(Integer, nullable=False, default=1)
    description = Column(Text, nullable=True)
    status = Column(String(50), default="PENDING", nullable=False, index=True)

    # Review & Lifecycle audit fields
    rejection_reason = Column(Text, nullable=True)
    rejected_by = Column(String(150), nullable=True)
    rejected_at = Column(DateTime, nullable=True)
    approved_by = Column(String(150), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    published_at = Column(DateTime, nullable=True)
    closed_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    company = relationship("RecruiterProfile", backref="internships")
    creator = relationship("User")
    applications = relationship(
        "InternshipApplication",
        back_populates="internship",
        cascade="all, delete-orphan",
    )


class InternshipApplication(Base):
    __tablename__ = "internship_applications"

    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    internship_id = Column(
        String(50),
        ForeignKey("internships.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    candidate_id = Column(
        String(50),
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status = Column(String(50), default="APPLIED", nullable=False, index=True)
    cover_letter = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    internship = relationship("Internship", back_populates="applications")
    candidate = relationship("CandidateProfile")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    actor = Column(String(150), nullable=False, index=True)
    action = Column(String(100), nullable=False, index=True)
    entity = Column(String(50), nullable=False, index=True)
    entity_id = Column(String(50), nullable=False, index=True)
    metadata_json = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
