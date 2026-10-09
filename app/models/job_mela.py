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
    state = Column(String(100), default="Andhra Pradesh", nullable=True)
    address = Column(String(500), nullable=True)
    organizer = Column(String(255), nullable=True)
    client_name = Column(String(255), nullable=True)
    client_id = Column(String(50), nullable=True)
    client_contact_person = Column(String(150), nullable=True)
    client_contact_phone = Column(String(50), nullable=True)
    status = Column(String(50), default="PUBLISHED", nullable=False, index=True)
    origin = Column(String(50), default="ADMIN_CREATED", nullable=False, index=True)
    created_by = Column(String(50), nullable=True)
    created_by_role = Column(String(50), default="ADMIN", nullable=False)
    company_id = Column(
        String(50),
        ForeignKey("recruiter_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    request_id = Column(String(50), nullable=True)
    image_url = Column(String(500), nullable=True)
    flyer_url = Column(String(500), nullable=True)
    registration_start_date = Column(String(50), nullable=True)
    registration_deadline = Column(String(50), nullable=True)
    max_capacity = Column(Integer, nullable=True)
    eligible_mandals = Column(Text, nullable=True)
    eligible_villages = Column(Text, nullable=True)
    eligible_qualifications = Column(Text, nullable=True)
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
    job_openings = relationship(
        "JobMelaJobOpening",
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
        nullable=True,
        index=True,
    )
    custom_company_name = Column(String(255), nullable=True)
    recruiter_name = Column(String(150), nullable=True)
    position = Column(String(255), nullable=True)
    qualification = Column(String(255), nullable=True)
    experience = Column(String(255), nullable=True)
    salary = Column(String(255), nullable=True)
    vacancies = Column(Integer, default=15, nullable=False)
    location = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)
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
    openings_list = relationship(
        "JobMelaJobOpening",
        back_populates="participation",
        cascade="all, delete-orphan",
    )


class JobMelaJobOpening(Base):
    __tablename__ = "job_mela_job_openings"

    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    job_mela_id = Column(
        String(50),
        ForeignKey("job_melas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    participation_id = Column(
        String(50),
        ForeignKey("job_mela_company_participations.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    job_title = Column(String(255), nullable=False)
    vacancies = Column(Integer, default=10, nullable=False)
    qualification = Column(String(255), nullable=True)
    experience = Column(String(255), nullable=True)
    salary_range = Column(String(255), nullable=True)
    location_stall = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    job_mela = relationship("JobMela", back_populates="job_openings")
    participation = relationship("JobMelaCompanyParticipation", back_populates="openings_list")


class JobMelaRequest(Base):
    __tablename__ = "job_mela_requests"

    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    request_number = Column(String(50), unique=True, index=True, nullable=False)
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    organizer = Column(String(255), nullable=False, index=True)
    company_id = Column(
        String(50),
        ForeignKey("recruiter_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    contact_person = Column(String(150), nullable=True)
    contact_email = Column(String(150), nullable=True)
    contact_phone = Column(String(50), nullable=True)
    proposed_date = Column(String(50), nullable=False, index=True)
    start_time = Column(String(50), default="09:00 AM", nullable=True)
    end_time = Column(String(50), default="05:00 PM", nullable=True)
    venue = Column(String(255), nullable=False)
    city = Column(String(100), nullable=False, index=True)
    district = Column(String(100), nullable=True)
    state = Column(String(100), default="Andhra Pradesh", nullable=True)
    location = Column(String(255), nullable=True)
    address = Column(String(500), nullable=True)
    expected_capacity = Column(Integer, default=2000, nullable=True)
    vacancies_count = Column(Integer, default=500, nullable=True)
    status = Column(String(50), default="PENDING", nullable=False, index=True)  # PENDING, APPROVED, REJECTED
    admin_reviewer_id = Column(
        String(50),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewer_name = Column(String(150), nullable=True)
    rejection_reason = Column(Text, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    linked_job_mela_id = Column(
        String(50),
        ForeignKey("job_melas.id", ondelete="SET NULL"),
        nullable=True,
    )
    participating_companies_data = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    company = relationship("RecruiterProfile", foreign_keys=[company_id])
    linked_job_mela = relationship("JobMela", foreign_keys=[linked_job_mela_id])


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
