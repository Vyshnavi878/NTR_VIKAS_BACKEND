import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database.base import Base


class Report(Base):
    __tablename__ = "reports"

    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    report_number = Column(String(50), unique=True, index=True, nullable=False)
    
    # Category of violation / grievance
    report_type = Column(String(100), index=True, nullable=False)
    
    # Target entity classification
    reported_user_type = Column(String(50), default="RECRUITER", nullable=False, index=True)
    reported_user_id = Column(
        String(50),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    reported_entity_type = Column(String(50), default="JOB", nullable=False, index=True)
    reported_entity_id = Column(String(100), nullable=True, index=True)
    reported_entity_name = Column(String(255), nullable=True, index=True)
    
    # Complainant / Reporter
    reporter_user_id = Column(
        String(50),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Narrative details
    subject = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    
    # Moderation status: PENDING, RESOLVED, DISMISSED
    status = Column(String(50), default="PENDING", nullable=False, index=True)
    
    # Resolution / Dismissal audit trail
    admin_notes = Column(Text, nullable=True)
    resolution_reason = Column(String(255), nullable=True)
    resolved_by_admin_id = Column(
        String(50),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    resolved_at = Column(DateTime, nullable=True)
    dismissed_by_admin_id = Column(
        String(50),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    dismissed_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    reporter_user = relationship("User", foreign_keys=[reporter_user_id])
    reported_user = relationship("User", foreign_keys=[reported_user_id])
    resolved_by_admin = relationship("User", foreign_keys=[resolved_by_admin_id])
    dismissed_by_admin = relationship("User", foreign_keys=[dismissed_by_admin_id])
