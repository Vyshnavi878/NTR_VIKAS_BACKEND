import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database.base import Base


class AdminProfile(Base):
    __tablename__ = "admin_profiles"

    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(
        String(50),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    full_name = Column(String(150), nullable=False, default="Admin User")
    designation = Column(String(150), nullable=True, default="State Operations Lead")
    contact_phone = Column(String(20), nullable=True, default="+91 98765 43210")
    department = Column(
        String(255),
        nullable=True,
        default="State Employment & Skill Development Authority",
    )
    profile_image_url = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationship to User
    user = relationship("User", back_populates="admin_profile")
