import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database.base import Base


class CompanyMember(Base):
    __tablename__ = "company_members"
    __table_args__ = (
        UniqueConstraint("company_id", "user_id", name="uq_company_user"),
    )

    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    company_id = Column(
        String(50),
        ForeignKey("recruiter_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        String(50),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role = Column(String(50), default="TECHNICAL_RECRUITER", nullable=False)
    status = Column(String(50), default="ACTIVE", nullable=False, index=True)
    invited_by = Column(String(50), nullable=True)
    joined_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    company = relationship("RecruiterProfile", back_populates="company_members")
    user = relationship("User", back_populates="company_memberships")


class CompanyInvitation(Base):
    __tablename__ = "company_invitations"

    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    company_id = Column(
        String(50),
        ForeignKey("recruiter_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    email = Column(String(150), nullable=False, index=True)
    full_name = Column(String(150), nullable=False)
    role = Column(String(50), default="TECHNICAL_RECRUITER", nullable=False)
    token_hash = Column(String(255), nullable=False, index=True)
    invited_by = Column(String(50), nullable=True)
    expires_at = Column(DateTime, nullable=False)
    accepted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    company = relationship("RecruiterProfile", back_populates="company_invitations")


class RecruiterNotificationPreference(Base):
    __tablename__ = "recruiter_notification_preferences"

    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(
        String(50),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    instant_new_applicant_alerts = Column(Boolean, default=True, nullable=False)
    interview_confirmation_reminders = Column(Boolean, default=True, nullable=False)
    weekly_hiring_digest = Column(Boolean, default=True, nullable=False)
    job_mela_alerts = Column(Boolean, default=True, nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    user = relationship("User", back_populates="recruiter_notification_preferences")
