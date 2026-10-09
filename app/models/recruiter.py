import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database.base import Base


class RecruiterProfile(Base):
    __tablename__ = "recruiter_profiles"

    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(
        String(50),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    # Recruiter Contact
    recruiter_name = Column(String(150), nullable=False)
    designation = Column(String(150), nullable=False)
    work_email = Column(String(150), unique=True, index=True, nullable=False)
    mobile_phone = Column(String(20), unique=True, index=True, nullable=False)

    # Company Details
    company_name = Column(String(200), index=True, nullable=False)
    company_website = Column(String(255), nullable=False)
    corporate_email = Column(String(150), nullable=True)
    company_phone = Column(String(20), nullable=True)
    primary_industry = Column(String(100), nullable=False)
    company_size = Column(String(100), nullable=False)
    headquarters_city_state = Column(String(150), nullable=False)
    registered_office_address = Column(Text, nullable=False)
    company_description = Column(Text, nullable=False)
    tagline = Column(String(300), nullable=True)
    cin_number = Column(String(50), nullable=True)
    gst_number = Column(String(50), nullable=True)
    company_type = Column(String(100), nullable=True)

    # Geographic Location (NTR District Hub)
    district = Column(String(100), default="NTR District", nullable=True)
    mandal = Column(String(100), nullable=True)
    village = Column(String(100), nullable=True)

    # Verification Documents
    incorporation_document_path = Column(String(500), nullable=True, default="/uploads/documents/direct_onboarded_exemption.pdf")
    recruiter_authorization_document_path = Column(String(500), nullable=True, default="/uploads/documents/direct_onboarded_exemption.pdf")
    company_logo_path = Column(String(500), nullable=True)

    # Registration Status & Audit
    status = Column(String(50), default="PENDING_APPROVAL", nullable=False, index=True)
    rejection_reason = Column(Text, nullable=True)
    submitted_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    reviewed_at = Column(DateTime, nullable=True)
    reviewed_by = Column(String(150), nullable=True)
    onboarded_by_admin_id = Column(String(50), nullable=True)
    onboarded_by_role = Column(String(50), default="RECRUITER", nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    user = relationship("User", back_populates="recruiter_profile")
    jobs = relationship("Job", back_populates="recruiter", cascade="all, delete-orphan")
    interviews = relationship("Interview", back_populates="recruiter", cascade="all, delete-orphan")
    applications = relationship("CandidateApplication", back_populates="recruiter")
    support_requests = relationship("RecruiterSupportRequest", back_populates="recruiter", cascade="all, delete-orphan")
    company_members = relationship("CompanyMember", back_populates="company", cascade="all, delete-orphan")
    company_invitations = relationship("CompanyInvitation", back_populates="company", cascade="all, delete-orphan")

