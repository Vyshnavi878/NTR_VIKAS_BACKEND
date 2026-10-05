import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database.base import Base


class RecruiterSupportRequest(Base):
    __tablename__ = "recruiter_support_requests"

    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    ticket_number = Column(String(50), unique=True, nullable=False, index=True)
    recruiter_id = Column(
        String(50),
        ForeignKey("recruiter_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    company_name = Column(String(200), nullable=False)
    recruiter_name = Column(String(150), nullable=False)
    registered_email = Column(String(150), nullable=False)
    issue_category = Column(String(100), nullable=False, index=True)
    subject = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(String(50), default="OPEN", nullable=False, index=True)
    priority = Column(String(50), default="NORMAL", nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    resolved_at = Column(DateTime, nullable=True)
    closed_at = Column(DateTime, nullable=True)

    # Relationships
    recruiter = relationship("RecruiterProfile", back_populates="support_requests")
