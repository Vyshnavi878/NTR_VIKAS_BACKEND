import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, Integer
from app.database.base import Base


class GalleryPhoto(Base):
    """Database model for Photo Gallery entries displayed across Admin and Public portals."""
    __tablename__ = "gallery_photos"

    id = Column(String(50), primary_key=True, default=lambda: f"img-{uuid.uuid4().hex[:10]}", index=True)
    title = Column(String(255), nullable=False, index=True)
    category = Column(String(100), nullable=False, default="Job Melas", index=True)
    date = Column(String(100), nullable=False)
    image_url = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    display_order = Column(Integer, default=0, nullable=False, index=True)
    is_published = Column(Boolean, default=True, nullable=False, index=True)
    created_by_admin_id = Column(
        String(50),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class GalleryVideo(Base):
    """Database model for Video Gallery entries displayed across Admin and Public portals."""
    __tablename__ = "gallery_videos"

    id = Column(String(50), primary_key=True, default=lambda: f"vid-{uuid.uuid4().hex[:10]}", index=True)
    title = Column(String(255), nullable=False, index=True)
    youtube_url = Column(String(500), nullable=False)
    category = Column(String(100), nullable=False, default="Job Melas", index=True)
    date = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    display_order = Column(Integer, default=0, nullable=False, index=True)
    is_published = Column(Boolean, default=True, nullable=False, index=True)
    created_by_admin_id = Column(
        String(50),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class PressArticle(Base):
    """Database model for Newspaper Articles and Press Highlights."""
    __tablename__ = "press_articles"

    id = Column(String(50), primary_key=True, default=lambda: f"news-{uuid.uuid4().hex[:10]}", index=True)
    title = Column(String(255), nullable=False, index=True)
    newspaper = Column(String(200), nullable=False, index=True)
    date = Column(String(100), nullable=False)
    edition = Column(String(200), nullable=True)
    image_url = Column(String(500), nullable=False)
    source_url = Column(String(500), nullable=True)
    summary = Column(Text, nullable=True)
    category = Column(String(100), nullable=True, default="Press Coverage", index=True)
    display_order = Column(Integer, default=0, nullable=False, index=True)
    is_published = Column(Boolean, default=True, nullable=False, index=True)
    created_by_admin_id = Column(
        String(50),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class WebsiteSectionHeader(Base):
    """Database model for customizable website section headers (gallery, news, etc.)."""
    __tablename__ = "website_section_headers"

    id = Column(String(50), primary_key=True)  # e.g. "gallery", "news"
    badge = Column(String(255), nullable=True)
    heading1 = Column(String(255), nullable=True)
    heading2 = Column(String(255), nullable=True)
    subtitle = Column(Text, nullable=True)
    updated_by = Column(String(150), nullable=True)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
