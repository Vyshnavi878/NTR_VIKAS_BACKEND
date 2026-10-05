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

    # Verification Documents
    incorporation_document_path = Column(String(500), nullable=False)
    recruiter_authorization_document_path = Column(String(500), nullable=False)
    company_logo_path = Column(String(500), nullable=True)

    # Registration Status & Audit
    status = Column(String(50), default="PENDING_APPROVAL", nullable=False, index=True)
    rejection_reason = Column(Text, nullable=True)
    submitted_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    reviewed_at = Column(DateTime, nullable=True)
    reviewed_by = Column(String(150), nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationship to User
    user = relationship("User", back_populates="recruiter_profile")
