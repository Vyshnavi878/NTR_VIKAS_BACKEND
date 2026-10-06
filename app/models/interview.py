import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database.base import Base


class Interview(Base):
    __tablename__ = "interviews"

    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    interview_number = Column(String(50), index=True, nullable=True)
    recruiter_id = Column(
        String(50),
        ForeignKey("recruiter_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    candidate_profile_id = Column(
        String(50),
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    application_id = Column(
        String(50),
        ForeignKey("candidate_applications.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    job_id = Column(String(50), nullable=True, index=True)
    candidate_name = Column(String(150), nullable=False)
    candidate_email = Column(String(150), nullable=True)
    job_title = Column(String(200), nullable=False)
    round_name = Column(String(100), default="Technical Round 1", nullable=False)
    interview_type = Column(String(100), default="Online (Google Meet)", nullable=False)
    date = Column(String(100), nullable=True)
    time = Column(String(100), nullable=True)
    scheduled_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    meeting_platform = Column(String(100), default="Google Meet", nullable=False)
    meeting_link = Column(String(255), nullable=True)
    interviewer = Column(String(150), nullable=True)
    status = Column(String(50), default="SCHEDULED", index=True, nullable=False)
    notes = Column(Text, nullable=True)
    # Extended scheduling fields
    scheduled_date = Column(String(50), nullable=True, index=True)
    start_time = Column(String(50), nullable=True)
    end_time = Column(String(50), nullable=True)
    timezone = Column(String(50), default="Asia/Kolkata", nullable=False)
    format = Column(String(50), default="ONLINE", nullable=False)
    venue = Column(String(255), nullable=True)
    interviewer_panel = Column(Text, nullable=True)
    agenda_notes = Column(Text, nullable=True)
    company_name = Column(String(200), nullable=True)
    result = Column(String(50), nullable=True)

    # Status lifecycle and audit timestamps
    completed_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    rescheduled_from_id = Column(String(50), nullable=True, index=True)
    cancellation_reason = Column(Text, nullable=True)
    created_by = Column(String(150), nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    recruiter = relationship("RecruiterProfile", back_populates="interviews")
    candidate = relationship("CandidateProfile", back_populates="interviews")
    application = relationship("CandidateApplication", back_populates="interviews")

    @property
    def candidate_id(self) -> str:
        return self.candidate_profile_id

    @candidate_id.setter
    def candidate_id(self, val: str) -> None:
        self.candidate_profile_id = val

