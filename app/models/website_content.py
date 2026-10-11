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


class JobPageSetting(Base):
    """Database model for persistent Jobs Page configuration (Hero, Search Placeholders, Popular Keywords)."""
    __tablename__ = "job_page_settings"

    id = Column(String(50), primary_key=True, default="default")
    hero_badge = Column(String(255), nullable=False, default="Corporate Recruitment Portal")
    hero_heading = Column(String(255), nullable=False, default="Find Your Dream Job in Andhra Pradesh & India")
    hero_subtitle = Column(Text, nullable=False, default="Explore 2,450+ verified corporate job openings with zero placement fees")
    search_placeholder = Column(String(255), nullable=False, default="Job title, skills (Python, React...), or company...")
    location_placeholder = Column(String(255), nullable=False, default="All Locations (All India)")
    popular_searches = Column(Text, nullable=False, default='["Python Developer", "React JS", "Data Analyst", "Fresher Jobs", "Hybrid Work", "FastAPI"]')
    updated_by = Column(String(150), nullable=True)
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


class JobLocation(Base):
    """Database model for supported Indian States and Union Territories for job filtering."""
    __tablename__ = "job_locations"

    id = Column(String(50), primary_key=True)
    name = Column(String(150), unique=True, nullable=False, index=True)
    state_ut_type = Column(String(50), nullable=False, default="state", index=True)  # "state" or "union_territory"
    display_order = Column(Integer, nullable=False, default=0, index=True)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
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


class AboutUsSetting(Base):
    """Database model for persistent About Us Page configuration (Hero, 3 Principles, Team, Leadership, Partners)."""
    __tablename__ = "about_us_settings"

    id = Column(String(50), primary_key=True, default="default")
    hero_badge = Column(String(255), nullable=False, default="Our Mission & Impact")
    hero_heading = Column(String(255), nullable=False, default="Bridging Talent with Opportunity Across India")
    hero_description = Column(Text, nullable=False)

    wwsf_heading = Column(String(255), nullable=False, default="What We Stand For")
    wwsf_description = Column(Text, nullable=False)
    wwsf_cards = Column(Text, nullable=False)  # JSON serialized list of 3 principle cards

    team_badge = Column(String(255), nullable=False, default="Our Leadership & Team")
    team_heading = Column(String(255), nullable=False, default="Our Team")
    team_description = Column(Text, nullable=False)
    team_members = Column(Text, nullable=False)  # JSON serialized list of team members

    leadership_badge = Column(String(255), nullable=False, default="LEADERSHIP")
    leadership_heading = Column(String(255), nullable=False, default="Leadership Messages")
    leadership_description = Column(Text, nullable=False, default="Words from our esteemed leaders who guide our mission")
    leadership_messages = Column(Text, nullable=False)  # JSON serialized list of leadership statements

    partners_heading = Column(String(255), nullable=False, default="OUR INDUSTRY & ACADEMIC TRAINING PARTNERS")
    partners_description = Column(Text, nullable=False)
    partners_list = Column(Text, nullable=False)  # JSON serialized list of partners with active & order

    stats_data = Column(Text, nullable=True)  # JSON serialized list of 4 platform stats
    updated_by = Column(String(150), nullable=True)
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


class JobMelaPageSetting(Base):
    """Database model for persistent Job Melas Page configuration (Hero badge, heading, description)."""
    __tablename__ = "job_mela_page_settings"

    id = Column(String(50), primary_key=True, default="default")
    hero_badge = Column(String(255), nullable=False, default="Nationwide Recruitment Drives")
    hero_heading = Column(String(255), nullable=False, default="Mega Job Melas & Career Fairs")
    hero_description = Column(
        Text,
        nullable=False,
        default=(
            "Attend on-ground walk-in interview sessions with 100+ hiring companies, "
            "receive free career guidance, and get spot job offer letters. Free registration for all job seekers."
        ),
    )
    updated_by = Column(String(150), nullable=True)
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


class SkillCmsSection(Base):
    """Database model for persistent Skill Development CMS sections."""
    __tablename__ = "skill_cms_sections"

    section_key = Column(String(50), primary_key=True)  # "skills_hero", "skills_highlights", "skills_mission", "skills_pathway", "skills_advantages", "skills_programs"
    title = Column(String(255), nullable=True)
    content = Column(Text, nullable=False)  # JSON-encoded structured content
    updated_by = Column(String(150), nullable=True)
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


