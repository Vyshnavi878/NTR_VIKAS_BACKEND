import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database.base import Base


class SupportTicket(Base):
    __tablename__ = "support_tickets"

    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    ticket_number = Column(String(50), unique=True, nullable=False, index=True)
    candidate_id = Column(
        String(50),
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    candidate_name = Column(String(150), nullable=False)
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
    candidate_profile = relationship("CandidateProfile", back_populates="support_tickets")
