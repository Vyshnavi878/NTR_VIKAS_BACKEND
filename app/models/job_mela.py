import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database.base import Base


class JobMela(Base):
    __tablename__ = "job_melas"

    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    mela_number = Column(String(50), unique=True, index=True, nullable=False)
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    event_date = Column(String(50), nullable=False, index=True)
    start_time = Column(String(50), nullable=True, default="09:00 AM")
    end_time = Column(String(50), nullable=True, default="05:30 PM")
    venue = Column(String(255), nullable=False)
    city = Column(String(100), nullable=False, index=True)
    district = Column(String(100), nullable=True, index=True)
    status = Column(String(50), default="PUBLISHED", nullable=False, index=True)
    created_by = Column(String(50), nullable=True)
    created_by_role = Column(String(50), default="ADMIN", nullable=False)
    company_id = Column(
        String(50),
        ForeignKey("recruiter_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    image_url = Column(String(500), nullable=True)
    flyer_url = Column(String(500), nullable=True)
    registration_deadline = Column(String(50), nullable=True)
    max_capacity = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    participations = relationship(
        "JobMelaCompanyParticipation",
        back_populates="job_mela",
        cascade="all, delete-orphan",
    )
    registrations = relationship(
        "JobMelaRegistration",
        back_populates="job_mela",
        cascade="all, delete-orphan",
    )
    company = relationship("RecruiterProfile", foreign_keys=[company_id])


class JobMelaCompanyParticipation(Base):
    __tablename__ = "job_mela_company_participations"

    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    job_mela_id = Column(
        String(50),
        ForeignKey("job_melas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    company_id = Column(
        String(50),
        ForeignKey("recruiter_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    openings = Column(Text, nullable=True)
    target_hires = Column(Integer, default=1, nullable=False)
    status = Column(String(50), default="PENDING", nullable=False, index=True)
    booth_number = Column(String(100), nullable=True)
    booth_location = Column(String(255), nullable=True)
    registered_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    approved_at = Column(DateTime, nullable=True)
    approved_by = Column(String(150), nullable=True)
    rejected_at = Column(DateTime, nullable=True)
    rejected_by = Column(String(150), nullable=True)
    rejection_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    job_mela = relationship("JobMela", back_populates="participations")
    company = relationship("RecruiterProfile", backref="mela_participations", foreign_keys=[company_id])

    __table_args__ = (
        UniqueConstraint("job_mela_id", "company_id", name="uq_mela_company_participation"),
    )


class JobMelaRegistration(Base):
    __tablename__ = "job_mela_registrations"

    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    job_mela_id = Column(
        String(50),
        ForeignKey("job_melas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    candidate_profile_id = Column(
        String(50),
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    pass_id = Column(String(100), unique=True, index=True, nullable=False)
    status = Column(String(50), default="CONFIRMED", nullable=False, index=True)
    gate_number = Column(String(100), default="Gate 2 (General Fast-Track)", nullable=False)
    time_slot = Column(String(100), default="Morning Session (09:00 AM - 01:00 PM)", nullable=False)
    qr_data = Column(String(255), nullable=True)
    application_id = Column(String(50), nullable=True, index=True)
    registered_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    job_mela = relationship("JobMela", back_populates="registrations")
    candidate_profile = relationship("CandidateProfile", backref="mela_registrations")

    __table_args__ = (
        UniqueConstraint("job_mela_id", "candidate_profile_id", name="uq_mela_candidate_registration"),
    )

