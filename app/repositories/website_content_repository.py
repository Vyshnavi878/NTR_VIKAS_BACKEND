import uuid
import json
from typing import Optional, List, Tuple, Dict, Any
from sqlalchemy import select, func, or_, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.website_content import (
    GalleryPhoto,
    GalleryVideo,
    PressArticle,
    WebsiteSectionHeader,
    JobPageSetting,
    JobLocation,
    AboutUsSetting,
    JobMelaPageSetting,
    SkillCmsSection,
)


class WebsiteContentRepository:
    """Repository handling all database operations for Website Content Management."""

    # ── Gallery Photos ──

    @staticmethod
    async def get_photos(
        db: AsyncSession,
        category: Optional[str] = None,
        search: Optional[str] = None,
        is_published: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[GalleryPhoto], int]:
        stmt = select(GalleryPhoto)

        if is_published is not None:
            stmt = stmt.where(GalleryPhoto.is_published == is_published)

        if category and category.lower() != "all":
            stmt = stmt.where(GalleryPhoto.category == category)

        if search and search.strip():
            term = f"%{search.strip().lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(GalleryPhoto.title).like(term),
                    func.lower(GalleryPhoto.description).like(term),
                    func.lower(GalleryPhoto.category).like(term),
                )
            )

        # Count total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_res = await db.execute(count_stmt)
        total = total_res.scalar() or 0

        # Order by display_order asc, then created_at desc
        stmt = stmt.order_by(asc(GalleryPhoto.display_order), desc(GalleryPhoto.created_at))
        stmt = stmt.offset(skip).limit(limit)

        result = await db.execute(stmt)
        items = list(result.scalars().all())
        return items, total

    @staticmethod
    async def get_photo_by_id(db: AsyncSession, photo_id: str) -> Optional[GalleryPhoto]:
        stmt = select(GalleryPhoto).where(GalleryPhoto.id == photo_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def create_photo(
        db: AsyncSession,
        data: Dict[str, Any],
        admin_id: Optional[str] = None,
    ) -> GalleryPhoto:
        photo_id = data.get("id") or f"img-{uuid.uuid4().hex[:10]}"
        photo = GalleryPhoto(
            id=photo_id,
            title=data["title"],
            category=data.get("category", "Job Melas"),
            date=data.get("date", ""),
            image_url=data.get("image_url", ""),
            description=data.get("description"),
            display_order=data.get("display_order", 0),
            is_published=data.get("is_published", True) if data.get("is_published") is not None else True,
            created_by_admin_id=admin_id,
        )
        db.add(photo)
        await db.commit()
        await db.refresh(photo)
        return photo

    @staticmethod
    async def update_photo(
        db: AsyncSession,
        photo_id: str,
        data: Dict[str, Any],
    ) -> Optional[GalleryPhoto]:
        photo = await WebsiteContentRepository.get_photo_by_id(db, photo_id)
        if not photo:
            return None

        for field, value in data.items():
            if value is not None and hasattr(photo, field):
                setattr(photo, field, value)

        await db.commit()
        await db.refresh(photo)
        return photo

    @staticmethod
    async def delete_photo(db: AsyncSession, photo_id: str) -> bool:
        photo = await WebsiteContentRepository.get_photo_by_id(db, photo_id)
        if not photo:
            return False
        await db.delete(photo)
        await db.commit()
        return True

    # ── Gallery Videos ──

    @staticmethod
    async def get_videos(
        db: AsyncSession,
        category: Optional[str] = None,
        search: Optional[str] = None,
        is_published: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[GalleryVideo], int]:
        stmt = select(GalleryVideo)

        if is_published is not None:
            stmt = stmt.where(GalleryVideo.is_published == is_published)

        if category and category.lower() != "all":
            stmt = stmt.where(GalleryVideo.category == category)

        if search and search.strip():
            term = f"%{search.strip().lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(GalleryVideo.title).like(term),
                    func.lower(GalleryVideo.description).like(term),
                    func.lower(GalleryVideo.category).like(term),
                )
            )

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_res = await db.execute(count_stmt)
        total = total_res.scalar() or 0

        stmt = stmt.order_by(asc(GalleryVideo.display_order), desc(GalleryVideo.created_at))
        stmt = stmt.offset(skip).limit(limit)

        result = await db.execute(stmt)
        items = list(result.scalars().all())
        return items, total

    @staticmethod
    async def get_video_by_id(db: AsyncSession, video_id: str) -> Optional[GalleryVideo]:
        stmt = select(GalleryVideo).where(GalleryVideo.id == video_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def create_video(
        db: AsyncSession,
        data: Dict[str, Any],
        admin_id: Optional[str] = None,
    ) -> GalleryVideo:
        video_id = data.get("id") or f"vid-{uuid.uuid4().hex[:10]}"
        video = GalleryVideo(
            id=video_id,
            title=data["title"],
            youtube_url=data.get("youtube_url", ""),
            category=data.get("category", "Job Melas"),
            date=data.get("date"),
            description=data.get("description"),
            display_order=data.get("display_order", 0),
            is_published=data.get("is_published", True) if data.get("is_published") is not None else True,
            created_by_admin_id=admin_id,
        )
        db.add(video)
        await db.commit()
        await db.refresh(video)
        return video

    @staticmethod
    async def update_video(
        db: AsyncSession,
        video_id: str,
        data: Dict[str, Any],
    ) -> Optional[GalleryVideo]:
        video = await WebsiteContentRepository.get_video_by_id(db, video_id)
        if not video:
            return None

        for field, value in data.items():
            if value is not None and hasattr(video, field):
                setattr(video, field, value)

        await db.commit()
        await db.refresh(video)
        return video

    @staticmethod
    async def delete_video(db: AsyncSession, video_id: str) -> bool:
        video = await WebsiteContentRepository.get_video_by_id(db, video_id)
        if not video:
            return False
        await db.delete(video)
        await db.commit()
        return True

    # ── Press & News Articles ──

    @staticmethod
    async def get_press_articles(
        db: AsyncSession,
        category: Optional[str] = None,
        search: Optional[str] = None,
        is_published: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[PressArticle], int]:
        stmt = select(PressArticle)

        if is_published is not None:
            stmt = stmt.where(PressArticle.is_published == is_published)

        if category and category.lower() != "all":
            stmt = stmt.where(PressArticle.category == category)

        if search and search.strip():
            term = f"%{search.strip().lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(PressArticle.title).like(term),
                    func.lower(PressArticle.newspaper).like(term),
                    func.lower(PressArticle.summary).like(term),
                )
            )

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_res = await db.execute(count_stmt)
        total = total_res.scalar() or 0

        stmt = stmt.order_by(asc(PressArticle.display_order), desc(PressArticle.created_at))
        stmt = stmt.offset(skip).limit(limit)

        result = await db.execute(stmt)
        items = list(result.scalars().all())
        return items, total

    @staticmethod
    async def get_press_article_by_id(db: AsyncSession, press_id: str) -> Optional[PressArticle]:
        stmt = select(PressArticle).where(PressArticle.id == press_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def create_press_article(
        db: AsyncSession,
        data: Dict[str, Any],
        admin_id: Optional[str] = None,
    ) -> PressArticle:
        press_id = data.get("id") or f"news-{uuid.uuid4().hex[:10]}"
        article = PressArticle(
            id=press_id,
            title=data["title"],
            newspaper=data.get("newspaper", "Special Press Bulletin"),
            date=data.get("date", ""),
            edition=data.get("edition"),
            image_url=data.get("image_url", ""),
            source_url=data.get("source_url"),
            summary=data.get("summary"),
            category=data.get("category", "Press Coverage"),
            display_order=data.get("display_order", 0),
            is_published=data.get("is_published", True) if data.get("is_published") is not None else True,
            created_by_admin_id=admin_id,
        )
        db.add(article)
        await db.commit()
        await db.refresh(article)
        return article

    @staticmethod
    async def update_press_article(
        db: AsyncSession,
        press_id: str,
        data: Dict[str, Any],
    ) -> Optional[PressArticle]:
        article = await WebsiteContentRepository.get_press_article_by_id(db, press_id)
        if not article:
            return None

        for field, value in data.items():
            if value is not None and hasattr(article, field):
                setattr(article, field, value)

        await db.commit()
        await db.refresh(article)
        return article

    @staticmethod
    async def delete_press_article(db: AsyncSession, press_id: str) -> bool:
        article = await WebsiteContentRepository.get_press_article_by_id(db, press_id)
        if not article:
            return False
        await db.delete(article)
        await db.commit()
        return True

    # ── Section Headers ──

    @staticmethod
    async def get_section_header(db: AsyncSession, section_id: str) -> Optional[WebsiteSectionHeader]:
        stmt = select(WebsiteSectionHeader).where(WebsiteSectionHeader.id == section_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def upsert_section_header(
        db: AsyncSession,
        section_id: str,
        data: Dict[str, Any],
        admin_name: Optional[str] = None,
    ) -> WebsiteSectionHeader:
        header = await WebsiteContentRepository.get_section_header(db, section_id)
        if not header:
            header = WebsiteSectionHeader(id=section_id)
            db.add(header)

        for field, value in data.items():
            if value is not None and hasattr(header, field):
                setattr(header, field, value)

        if admin_name:
            header.updated_by = admin_name

        await db.commit()
        await db.refresh(header)
        return header

    # ── Jobs Page Settings ──

    @staticmethod
    async def get_jobs_page_settings(db: AsyncSession) -> JobPageSetting:
        stmt = select(JobPageSetting).where(JobPageSetting.id == "default")
        result = await db.execute(stmt)
        settings = result.scalar_one_or_none()
        if not settings:
            settings = JobPageSetting(
                id="default",
                hero_badge="Corporate Recruitment Portal",
                hero_heading="Find Your Dream Job in Andhra Pradesh & India",
                hero_subtitle="Explore 2,450+ verified corporate job openings with zero placement fees",
                search_placeholder="Job title, skills (Python, React...), or company...",
                location_placeholder="All Locations (All India)",
                popular_searches=json.dumps([
                    "Python Developer",
                    "React JS",
                    "Data Analyst",
                    "Fresher Jobs",
                    "Hybrid Work",
                    "FastAPI",
                ]),
                updated_by="System Default",
            )
            db.add(settings)
            await db.commit()
            await db.refresh(settings)
        return settings

    @staticmethod
    async def upsert_jobs_page_settings(
        db: AsyncSession,
        data: Dict[str, Any],
        admin_name: Optional[str] = None,
    ) -> JobPageSetting:
        settings = await WebsiteContentRepository.get_jobs_page_settings(db)
        for field, value in data.items():
            if value is not None and hasattr(settings, field):
                setattr(settings, field, value)

        if admin_name:
            settings.updated_by = admin_name

        await db.commit()
        await db.refresh(settings)
        return settings

    @staticmethod
    async def reset_jobs_page_settings(db: AsyncSession, admin_name: Optional[str] = None) -> JobPageSetting:
        defaults = {
            "hero_badge": "Corporate Recruitment Portal",
            "hero_heading": "Find Your Dream Job in Andhra Pradesh & India",
            "hero_subtitle": "Explore 2,450+ verified corporate job openings with zero placement fees",
            "search_placeholder": "Job title, skills (Python, React...), or company...",
            "location_placeholder": "All Locations (All India)",
            "popular_searches": json.dumps([
                "Python Developer",
                "React JS",
                "Data Analyst",
                "Fresher Jobs",
                "Hybrid Work",
                "FastAPI",
            ]),
        }
        return await WebsiteContentRepository.upsert_jobs_page_settings(db, defaults, admin_name=admin_name)

    # ── Job Locations ──

    @staticmethod
    async def get_all_job_locations(
        db: AsyncSession,
        is_active: Optional[bool] = None,
    ) -> List[JobLocation]:
        stmt = select(JobLocation)
        if is_active is not None:
            stmt = stmt.where(JobLocation.is_active == is_active)
        stmt = stmt.order_by(asc(JobLocation.display_order), asc(JobLocation.name))
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_job_location_by_id(db: AsyncSession, location_id: str) -> Optional[JobLocation]:
        stmt = select(JobLocation).where(JobLocation.id == location_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_job_location_by_name(db: AsyncSession, name: str) -> Optional[JobLocation]:
        stmt = select(JobLocation).where(func.lower(JobLocation.name) == name.strip().lower())
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def update_job_location(
        db: AsyncSession,
        location_id: str,
        data: Dict[str, Any],
    ) -> Optional[JobLocation]:
        loc = await WebsiteContentRepository.get_job_location_by_id(db, location_id)
        if not loc:
            return None
        for field, value in data.items():
            if value is not None and hasattr(loc, field):
                setattr(loc, field, value)
        await db.commit()
        await db.refresh(loc)
        return loc

    @staticmethod
    async def batch_update_job_locations(
        db: AsyncSession,
        updates: List[Dict[str, Any]],
    ) -> List[JobLocation]:
        for item in updates:
            loc_id = item.get("id")
            if not loc_id:
                continue
            loc = await WebsiteContentRepository.get_job_location_by_id(db, loc_id)
            if loc:
                if "is_active" in item and item["is_active"] is not None:
                    loc.is_active = item["is_active"]
                if "name" in item and item["name"]:
                    loc.name = item["name"]
        await db.commit()
        return await WebsiteContentRepository.get_all_job_locations(db)

    @staticmethod
    async def reset_job_locations(db: AsyncSession) -> List[JobLocation]:
        stmt = select(JobLocation)
        res = await db.execute(stmt)
        locs = list(res.scalars().all())
        for loc in locs:
            loc.is_active = True
        await db.commit()
        return await WebsiteContentRepository.get_all_job_locations(db)

    # ── About Us Page Settings ──

    @staticmethod
    async def get_about_us_settings(db: AsyncSession) -> AboutUsSetting:
        stmt = select(AboutUsSetting).where(AboutUsSetting.id == "default")
        result = await db.execute(stmt)
        settings = result.scalar_one_or_none()
        if not settings:
            settings = AboutUsSetting(
                id="default",
                hero_badge="Our Mission & Impact",
                hero_heading="Bridging Talent with Opportunity Across India",
                hero_description="NTR VIKASA Job Portal was founded on a simple principle: every candidate deserves fair, direct access to employment opportunities without scam fees, opaque processes, or dead ends.",
                wwsf_heading="What We Stand For",
                wwsf_description="Guiding principles that power our candidate-first architecture and employer verification policies.",
                wwsf_cards=json.dumps([
                    {
                        "id": "wwsf-1",
                        "icon": "ShieldCheck",
                        "title": "100% Verified Quality",
                        "desc": "Every single recruiter profile and job listing is reviewed to eliminate illegitimate recruiters and recruitment charges.",
                        "color": "primary",
                    },
                    {
                        "id": "wwsf-2",
                        "icon": "Target",
                        "title": "Transparent Application Lifecycle",
                        "desc": "Candidates receive live feedback across all 20 standard recruitment milestones from applied to interview to offer letters.",
                        "color": "success",
                    },
                    {
                        "id": "wwsf-3",
                        "icon": "Users",
                        "title": "Inclusive Mega Job Melas",
                        "desc": "Bringing top corporate opportunities directly to Tier-2, Tier-3 and rural graduate communities through walk-in physical fairs.",
                        "color": "warning",
                    },
                ]),
                team_badge="Our Leadership & Team",
                team_heading="Our Team",
                team_description="Experienced leaders with backgrounds across technology, public policy, and corporate recruitment.",
                team_members=json.dumps([
                    {
                        "id": "team-1",
                        "name": "Dr. Ramesh Sundaram",
                        "role": "Founder & Managing Director",
                        "organization": "NTR Vikasa",
                        "bio": "Former National Employment Council advisor with 20+ years driving talent mobility initiatives.",
                        "image": None,
                    },
                    {
                        "id": "team-2",
                        "name": "Ananya Deshmukh",
                        "role": "Chief Technology Officer",
                        "organization": "NTR Vikasa",
                        "bio": "Ex-Google & Flipkart engineering leader passionate about AI-driven career matching.",
                        "image": None,
                    },
                    {
                        "id": "team-3",
                        "name": "Siddharth Nair",
                        "role": "Head of Employer Partnerships",
                        "organization": "NTR Vikasa",
                        "bio": "Built recruitment pipelines across 500+ Indian corporate enterprises and SME networks.",
                        "image": None,
                    },
                    {
                        "id": "team-4",
                        "name": "Meera Sengupta",
                        "role": "Director of Diversity & Job Melas",
                        "organization": "NTR Vikasa",
                        "bio": "Pioneered inclusive job fairs for women, PwD, and tier-2/3 college graduates across India.",
                        "image": None,
                    },
                ]),
                leadership_badge="LEADERSHIP",
                leadership_heading="Leadership Messages",
                leadership_description="Words from our esteemed leaders who guide our mission",
                leadership_messages=json.dumps([
                    {
                        "id": "msg-1",
                        "name": "K Lacha Rao",
                        "designation": "Chairperson",
                        "role": "Chairperson",
                        "organization": "NTR Vikasa Jobs",
                        "image": None,
                        "initials": "VIKASA",
                        "headerBg": "#0f2a59",
                        "message": "Our mission is to bridge the gap between academia and industry by providing industry-aligned curriculum to ICT faculty and students, offering the finest skill, career connect, and mentorship guidance.",
                        "fullMessage": "Our mission is to bridge the gap between academia and industry by providing industry-aligned curriculum to ICT faculty and students, offering the finest skill, career connect, and mentorship guidance. Through deep collaboration with industry leaders and government stakeholders, we are dedicated to providing transformational employment avenues for all aspiring youth across the state.",
                        "hasViewAction": False,
                    },
                    {
                        "id": "msg-2",
                        "name": "K. Lacha Rao",
                        "designation": "Project Director",
                        "role": "Project Director",
                        "organization": "Vikasa Jobs",
                        "image": None,
                        "initials": "KLR",
                        "headerBg": "#047857",
                        "message": "At NTR Vikasa, our mission is to empower youth by creating meaningful employment opportunities and building a skilled workforce for the future. We believe that every individual deserves the right guidance, training, and platform to achieve their career aspirations. Through our initiatives such as Job Melas, skill development programs, and industry partnerships,...",
                        "fullMessage": "At NTR Vikasa, our mission is to empower youth by creating meaningful employment opportunities and building a skilled workforce for the future. We believe that every individual deserves the right guidance, training, and platform to achieve their career aspirations. Through our initiatives such as Job Melas, skill development programs, and industry partnerships, we strive to build sustainable bridges between talent and industry requirements across the state.",
                        "hasViewAction": True,
                    },
                ]),
                partners_heading="OUR INDUSTRY & ACADEMIC TRAINING PARTNERS",
                partners_description="Empowering future-ready talent in collaboration with leading corporate and educational organizations.",
                partners_list=json.dumps([
                    {"id": "p-1", "name": "Hyundai MOBIS", "logoText": "HYUNDAI MOBIS", "active": True, "order": 1},
                    {"id": "p-2", "name": "ISUZU", "logoText": "ISUZU", "active": True, "order": 2},
                    {"id": "p-3", "name": "MedPlus+", "logoText": "MedPlus+", "active": True, "order": 3},
                    {"id": "p-4", "name": "Apollo Pharmacy", "logoText": "Apollo Pharmacy", "active": True, "order": 4},
                    {"id": "p-5", "name": "IndiGo", "logoText": "IndiGo", "active": True, "order": 5},
                    {"id": "p-6", "name": "INZI Controls", "logoText": "INZI CONTROLS", "active": True, "order": 6},
                    {"id": "p-7", "name": "Dixon", "logoText": "Dixon", "active": True, "order": 7},
                    {"id": "p-8", "name": "COGENT", "logoText": "COGENT", "active": True, "order": 8},
                    {"id": "p-9", "name": "Indus", "logoText": "Indus", "active": True, "order": 9},
                    {"id": "p-10", "name": "NIIT", "logoText": "NIIT", "active": True, "order": 10},
                    {"id": "p-11", "name": "iSON", "logoText": "iSON", "active": True, "order": 11},
                    {"id": "p-12", "name": "Deccan", "logoText": "deccan", "active": True, "order": 12},
                    {"id": "p-13", "name": "ICICI Bank", "logoText": "ICICI Bank", "active": True, "order": 13},
                ]),
                stats_data=json.dumps([
                    {"id": "ab-stat-1", "label": "Registered Job Seekers", "value": "2,80,000+", "color": "var(--color-primary-600)"},
                    {"id": "ab-stat-2", "label": "Confirmed Placements", "value": "1,95,000+", "color": "var(--color-success-600)"},
                    {"id": "ab-stat-3", "label": "Verified Hiring Employers", "value": "14,200+", "color": "var(--color-warning-600)"},
                    {"id": "ab-stat-4", "label": "State-Wide Job Melas Held", "value": "24+", "color": "var(--color-info-600)"},
                ]),
                updated_by="System Seed",
            )
            db.add(settings)
            await db.commit()
            await db.refresh(settings)
        return settings

    @staticmethod
    async def upsert_about_us_settings(
        db: AsyncSession,
        data: Dict[str, Any],
        admin_name: Optional[str] = None,
    ) -> AboutUsSetting:
        settings = await WebsiteContentRepository.get_about_us_settings(db)
        for field, value in data.items():
            if value is not None and hasattr(settings, field):
                setattr(settings, field, value)

        if admin_name:
            settings.updated_by = admin_name

        await db.commit()
        await db.refresh(settings)
        return settings

    @staticmethod
    async def reset_about_us_settings(db: AsyncSession, admin_name: Optional[str] = None) -> AboutUsSetting:
        defaults = {
            "hero_badge": "Our Mission & Impact",
            "hero_heading": "Bridging Talent with Opportunity Across India",
            "hero_description": "NTR VIKASA Job Portal was founded on a simple principle: every candidate deserves fair, direct access to employment opportunities without scam fees, opaque processes, or dead ends.",
            "wwsf_heading": "What We Stand For",
            "wwsf_description": "Guiding principles that power our candidate-first architecture and employer verification policies.",
            "wwsf_cards": json.dumps([
                {
                    "id": "wwsf-1",
                    "icon": "ShieldCheck",
                    "title": "100% Verified Quality",
                    "desc": "Every single recruiter profile and job listing is reviewed to eliminate illegitimate recruiters and recruitment charges.",
                    "color": "primary",
                },
                {
                    "id": "wwsf-2",
                    "icon": "Target",
                    "title": "Transparent Application Lifecycle",
                    "desc": "Candidates receive live feedback across all 20 standard recruitment milestones from applied to interview to offer letters.",
                    "color": "success",
                },
                {
                    "id": "wwsf-3",
                    "icon": "Users",
                    "title": "Inclusive Mega Job Melas",
                    "desc": "Bringing top corporate opportunities directly to Tier-2, Tier-3 and rural graduate communities through walk-in physical fairs.",
                    "color": "warning",
                },
            ]),
            "team_badge": "Our Leadership & Team",
            "team_heading": "Our Team",
            "team_description": "Experienced leaders with backgrounds across technology, public policy, and corporate recruitment.",
            "team_members": json.dumps([
                {
                    "id": "team-1",
                    "name": "Dr. Ramesh Sundaram",
                    "role": "Founder & Managing Director",
                    "organization": "NTR Vikasa",
                    "bio": "Former National Employment Council advisor with 20+ years driving talent mobility initiatives.",
                    "image": None,
                },
                {
                    "id": "team-2",
                    "name": "Ananya Deshmukh",
                    "role": "Chief Technology Officer",
                    "organization": "NTR Vikasa",
                    "bio": "Ex-Google & Flipkart engineering leader passionate about AI-driven career matching.",
                    "image": None,
                },
                {
                    "id": "team-3",
                    "name": "Siddharth Nair",
                    "role": "Head of Employer Partnerships",
                    "organization": "NTR Vikasa",
                    "bio": "Built recruitment pipelines across 500+ Indian corporate enterprises and SME networks.",
                    "image": None,
                },
                {
                    "id": "team-4",
                    "name": "Meera Sengupta",
                    "role": "Director of Diversity & Job Melas",
                    "organization": "NTR Vikasa",
                    "bio": "Pioneered inclusive job fairs for women, PwD, and tier-2/3 college graduates across India.",
                    "image": None,
                },
            ]),
            "leadership_badge": "LEADERSHIP",
            "leadership_heading": "Leadership Messages",
            "leadership_description": "Words from our esteemed leaders who guide our mission",
            "leadership_messages": json.dumps([
                {
                    "id": "msg-1",
                    "name": "K Lacha Rao",
                    "designation": "Chairperson",
                    "role": "Chairperson",
                    "organization": "NTR Vikasa Jobs",
                    "image": None,
                    "initials": "VIKASA",
                    "headerBg": "#0f2a59",
                    "message": "Our mission is to bridge the gap between academia and industry by providing industry-aligned curriculum to ICT faculty and students, offering the finest skill, career connect, and mentorship guidance.",
                    "fullMessage": "Our mission is to bridge the gap between academia and industry by providing industry-aligned curriculum to ICT faculty and students, offering the finest skill, career connect, and mentorship guidance. Through deep collaboration with industry leaders and government stakeholders, we are dedicated to providing transformational employment avenues for all aspiring youth across the state.",
                    "hasViewAction": False,
                },
                {
                    "id": "msg-2",
                    "name": "K. Lacha Rao",
                    "designation": "Project Director",
                    "role": "Project Director",
                    "organization": "Vikasa Jobs",
                    "image": None,
                    "initials": "KLR",
                    "headerBg": "#047857",
                    "message": "At NTR Vikasa, our mission is to empower youth by creating meaningful employment opportunities and building a skilled workforce for the future. We believe that every individual deserves the right guidance, training, and platform to achieve their career aspirations. Through our initiatives such as Job Melas, skill development programs, and industry partnerships,...",
                    "fullMessage": "At NTR Vikasa, our mission is to empower youth by creating meaningful employment opportunities and building a skilled workforce for the future. We believe that every individual deserves the right guidance, training, and platform to achieve their career aspirations. Through our initiatives such as Job Melas, skill development programs, and industry partnerships, we strive to build sustainable bridges between talent and industry requirements across the state.",
                    "hasViewAction": True,
                },
            ]),
            "partners_heading": "OUR INDUSTRY & ACADEMIC TRAINING PARTNERS",
            "partners_description": "Empowering future-ready talent in collaboration with leading corporate and educational organizations.",
            "partners_list": json.dumps([
                {"id": "p-1", "name": "Hyundai MOBIS", "logoText": "HYUNDAI MOBIS", "active": True, "order": 1},
                {"id": "p-2", "name": "ISUZU", "logoText": "ISUZU", "active": True, "order": 2},
                {"id": "p-3", "name": "MedPlus+", "logoText": "MedPlus+", "active": True, "order": 3},
                {"id": "p-4", "name": "Apollo Pharmacy", "logoText": "Apollo Pharmacy", "active": True, "order": 4},
                {"id": "p-5", "name": "IndiGo", "logoText": "IndiGo", "active": True, "order": 5},
                {"id": "p-6", "name": "INZI Controls", "logoText": "INZI CONTROLS", "active": True, "order": 6},
                {"id": "p-7", "name": "Dixon", "logoText": "Dixon", "active": True, "order": 7},
                {"id": "p-8", "name": "COGENT", "logoText": "COGENT", "active": True, "order": 8},
                {"id": "p-9", "name": "Indus", "logoText": "Indus", "active": True, "order": 9},
                {"id": "p-10", "name": "NIIT", "logoText": "NIIT", "active": True, "order": 10},
                {"id": "p-11", "name": "iSON", "logoText": "iSON", "active": True, "order": 11},
                {"id": "p-12", "name": "Deccan", "logoText": "deccan", "active": True, "order": 12},
                {"id": "p-13", "name": "ICICI Bank", "logoText": "ICICI Bank", "active": True, "order": 13},
            ]),
            "stats_data": json.dumps([
                {"id": "ab-stat-1", "label": "Registered Job Seekers", "value": "2,80,000+", "color": "var(--color-primary-600)"},
                {"id": "ab-stat-2", "label": "Confirmed Placements", "value": "1,95,000+", "color": "var(--color-success-600)"},
                {"id": "ab-stat-3", "label": "Verified Hiring Employers", "value": "14,200+", "color": "var(--color-warning-600)"},
                {"id": "ab-stat-4", "label": "State-Wide Job Melas Held", "value": "24+", "color": "var(--color-info-600)"},
            ]),
        }
        return await WebsiteContentRepository.upsert_about_us_settings(db, defaults, admin_name=admin_name)

    # ── Job Melas Page Settings ──

    @staticmethod
    async def get_job_mela_settings(db: AsyncSession) -> JobMelaPageSetting:
        """Fetch Job Melas page settings, auto-initializing with approved defaults if not existing."""
        stmt = select(JobMelaPageSetting).where(JobMelaPageSetting.id == "default")
        result = await db.execute(stmt)
        setting = result.scalar_one_or_none()
        if not setting:
            setting = JobMelaPageSetting(
                id="default",
                hero_badge="Nationwide Recruitment Drives",
                hero_heading="Mega Job Melas & Career Fairs",
                hero_description=(
                    "Attend on-ground walk-in interview sessions with 100+ hiring companies, "
                    "receive free career guidance, and get spot job offer letters. Free registration for all job seekers."
                ),
                updated_by="System Default",
            )
            db.add(setting)
            await db.commit()
            await db.refresh(setting)
        return setting

    @staticmethod
    async def upsert_job_mela_settings(
        db: AsyncSession,
        data: Dict[str, Any],
        admin_name: Optional[str] = None,
    ) -> JobMelaPageSetting:
        """Update or insert Job Melas hero settings."""
        setting = await WebsiteContentRepository.get_job_mela_settings(db)
        if "badge" in data and data["badge"] is not None:
            setting.hero_badge = data["badge"]
        elif "hero_badge" in data and data["hero_badge"] is not None:
            setting.hero_badge = data["hero_badge"]

        if "heading" in data and data["heading"] is not None:
            setting.hero_heading = data["heading"]
        elif "hero_heading" in data and data["hero_heading"] is not None:
            setting.hero_heading = data["hero_heading"]

        if "description" in data and data["description"] is not None:
            setting.hero_description = data["description"]
        elif "hero_description" in data and data["hero_description"] is not None:
            setting.hero_description = data["hero_description"]

        if admin_name:
            setting.updated_by = admin_name

        await db.commit()
        await db.refresh(setting)
        return setting

    @staticmethod
    async def reset_job_mela_settings(
        db: AsyncSession,
        admin_name: Optional[str] = None,
    ) -> JobMelaPageSetting:
        """Reset Job Melas hero settings to approved defaults."""
        defaults = {
            "badge": "Nationwide Recruitment Drives",
            "heading": "Mega Job Melas & Career Fairs",
            "description": (
                "Attend on-ground walk-in interview sessions with 100+ hiring companies, "
                "receive free career guidance, and get spot job offer letters. Free registration for all job seekers."
            ),
        }
        return await WebsiteContentRepository.upsert_job_mela_settings(db, defaults, admin_name=admin_name)

    # ── Skill Development CMS Defaults & Operations ──

    SKILL_CMS_DEFAULTS = {
        "skills_hero": {
            "title": "Hero Section — Top Banner",
            "content": {
                "badge": "NTR VIKASA • Skill Development & Employment Generation",
                "heading": "Skill Development & Training Programs",
                "description": "Empowering job seekers with government-recognized, industry-aligned training, practical learning, and placement support.",
                "exploreBtnText": "Explore Programs",
                "viewCoursesBtnText": "View Courses",
            },
        },
        "skills_highlights": {
            "title": "Highlights — Trust Metrics",
            "content": [
                {"id": "hl-1", "icon": "Award", "title": "Government Recognized", "subtitle": "NSDC / NSQF Certified"},
                {"id": "hl-2", "icon": "TrendingUp", "title": "Placement Support", "subtitle": "Job Mela / Employment Support"},
                {"id": "hl-3", "icon": "BookOpen", "title": "Practical Curriculum", "subtitle": "Hands-on Industry Labs"},
                {"id": "hl-4", "icon": "Users", "title": "Expert Mentors", "subtitle": "Experienced Professionals"},
            ],
        },
        "skills_mission": {
            "title": "Institutional Mission — Mission & Pillars",
            "content": {
                "badge": "Institutional Mission",
                "heading": "Empowering Skills. Enabling Careers.",
                "description": "The NTR VIKASA Skill Development initiative bridges the critical divide between academic qualifications and industry hiring standards. By partnering with state government bodies, national sector skill councils, and corporate employers, we deliver employment-focused, hands-on training to youth across Andhra Pradesh.",
                "cards": [
                    {
                        "id": "es-1",
                        "icon": "Code2",
                        "title": "Industry-Relevant Learning",
                        "desc": "Curricula designed directly in consultation with tech leaders, BFSI corporations, and manufacturing employers to teach in-demand workplace tools."
                    },
                    {
                        "id": "es-2",
                        "icon": "Laptop",
                        "title": "Practical Training Labs",
                        "desc": "Over 70% of course time is dedicated to hands-on lab practicals, simulated industrial environments, and live capstone projects."
                    },
                    {
                        "id": "es-3",
                        "icon": "TrendingUp",
                        "title": "Placement Assistance",
                        "desc": "Trained candidates receive dedicated interview preparation, resume enhancement, and direct fast-track access to regional Mega Job Melas."
                    }
                ],
            },
        },
        "skills_pathway": {
            "title": "Candidate Pathway — Training Journey",
            "content": {
                "badge": "Candidate Pathway",
                "heading": "From Training to Employment",
                "description": "A structured 6-step journey designed to take you from foundational training to confirmed corporate placement.",
                "steps": [
                    {"step": "01", "title": "Choose a Program", "desc": "Browse through high-demand domains like Tech, AI, Cloud, and BFSI to select the right skill track aligned with your career goals."},
                    {"step": "02", "title": "Register & Counseling", "desc": "Submit a free online enrollment request. Our skill counselors guide you through batch schedules, prerequisite review, and center allocation."},
                    {"step": "03", "title": "Hands-on Training", "desc": "Undergo practical, lab-based learning with experienced industry mentors, real-world capstone assignments, and modern equipment."},
                    {"step": "04", "title": "Get Certified", "desc": "Earn government-recognized NSDC, NSQF, and Sector Skill Council certifications validating your industry-ready competencies."},
                    {"step": "05", "title": "Placement Preparation", "desc": "Participate in resume enhancement sessions, technical interview simulations, soft skills coaching, and mock tests."},
                    {"step": "06", "title": "Employment & Job Melas", "desc": "Receive direct interview access to 14,000+ verified corporate recruiters and fast-track entry to statewide Mega Job Melas."},
                ],
            },
        },
        "skills_advantages": {
            "title": "Why Choose NTR VIKASA — Institutional Excellence",
            "content": {
                "badge": "Institutional Excellence",
                "heading": "Why Choose NTR VIKASA",
                "description": "Outcome-focused advantages designed to give candidates a real competitive edge in modern job markets.",
                "cards": [
                    {"icon": "Award", "title": "Govt. & NSDC Recognized", "desc": "All programs follow National Skill Qualification Framework (NSQF) standards ensuring nationwide employer recognition."},
                    {"icon": "Laptop", "title": "70% Practical Lab Training", "desc": "Emphasis on experiential lab exercises, software simulations, and hardware setups rather than rote memorization."},
                    {"icon": "Users", "title": "Certified Expert Mentors", "desc": "Learn directly from seasoned industry practitioners and certified instructors with extensive domain track records."},
                    {"icon": "TrendingUp", "title": "100% Placement Support", "desc": "Direct pipeline to NTR VIKASA verified recruiters, corporate interview drives, and district-wide Mega Job Melas."},
                    {"icon": "ShieldCheck", "title": "100% Free / Subsidized", "desc": "State-sponsored skill development initiatives designed to empower aspiring job seekers across all districts of Andhra Pradesh."},
                    {"icon": "Sparkles", "title": "Future-Ready Curriculum", "desc": "Regularly updated course modules integrating modern AI tools, cloud platforms, and modern industrial requirements."},
                ],
            },
        },
        "skills_programs": {
            "title": "Programs We Offer — Programs & Sectors",
            "content": {
                "badge": "Sector Domains",
                "heading": "Programs We Offer",
                "description": "Specialized training pathways spanning modern tech, finance, core engineering, and administrative sectors.",
                "categories": [
                    {"id": "it", "name": "Information Technology", "icon": "Code2", "desc": "Web development, cloud computing, and computer fundamentals", "count": "3 Courses"},
                    {"id": "data-ai", "name": "Data & AI", "icon": "Database", "desc": "Data analytics, Power BI dashboards, and business intelligence", "count": "2 Courses"},
                    {"id": "ai-tools", "name": "AI & Productivity Tools", "icon": "Sparkles", "desc": "ChatGPT prompt engineering, Gemini AI & office automation", "count": "2 Courses"},
                    {"id": "banking", "name": "Banking & Finance", "icon": "Landmark", "desc": "BFSI operations, retail banking, credit appraisal & compliance", "count": "2 Courses"},
                    {"id": "accounting", "name": "Office & Accounting", "icon": "Calculator", "desc": "Tally Prime, GST return filing, MS Office & Advanced Excel", "count": "2 Courses"},
                    {"id": "core-eng", "name": "Core Engineering", "icon": "Cpu", "desc": "PLC automation, SCADA systems, and industrial electrical wiring", "count": "2 Courses"},
                    {"id": "healthcare", "name": "Healthcare", "icon": "Activity", "desc": "Hospital administration, patient care, EMR systems & billing", "count": "2 Courses"},
                    {"id": "marketing", "name": "Marketing & Sales", "icon": "Megaphone", "desc": "Digital marketing, SEO, social media ads & customer support", "count": "2 Courses"},
                ],
            },
        },
    }

    @staticmethod
    def normalize_skill_section_key(key: str) -> Optional[str]:
        if not key:
            return None
        mapping = {
            "skills_hero": "skills_hero",
            "hero": "skills_hero",
            "skills_highlights": "skills_highlights",
            "highlights": "skills_highlights",
            "skills_mission": "skills_mission",
            "mission": "skills_mission",
            "empowering_skills": "skills_mission",
            "empoweringSkills": "skills_mission",
            "skills_pathway": "skills_pathway",
            "pathway": "skills_pathway",
            "training_journey": "skills_pathway",
            "trainingJourney": "skills_pathway",
            "skills_advantages": "skills_advantages",
            "advantages": "skills_advantages",
            "why_choose": "skills_advantages",
            "whyChoose": "skills_advantages",
            "skills_programs": "skills_programs",
            "programs": "skills_programs",
            "programs_we_offer": "skills_programs",
            "programsWeOffer": "skills_programs",
        }
        return mapping.get(key.strip())

    @staticmethod
    async def get_skill_section(db: AsyncSession, section_key: str) -> Optional[SkillCmsSection]:
        norm_key = WebsiteContentRepository.normalize_skill_section_key(section_key) or section_key
        stmt = select(SkillCmsSection).where(SkillCmsSection.section_key == norm_key)
        res = await db.execute(stmt)
        record = res.scalar_one_or_none()
        if not record and norm_key in WebsiteContentRepository.SKILL_CMS_DEFAULTS:
            default_entry = WebsiteContentRepository.SKILL_CMS_DEFAULTS[norm_key]
            record = SkillCmsSection(
                section_key=norm_key,
                title=default_entry["title"],
                content=json.dumps(default_entry["content"]),
                updated_by="System Default",
            )
            db.add(record)
            await db.commit()
            await db.refresh(record)
        return record

    @staticmethod
    async def get_all_skill_sections(db: AsyncSession) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        for canonical_key in WebsiteContentRepository.SKILL_CMS_DEFAULTS.keys():
            sec = await WebsiteContentRepository.get_skill_section(db, canonical_key)
            if sec:
                try:
                    parsed = json.loads(sec.content)
                except Exception:
                    parsed = sec.content
                result[canonical_key] = {
                    "section_key": sec.section_key,
                    "title": sec.title,
                    "content": parsed,
                    "updated_by": sec.updated_by,
                    "updated_at": sec.updated_at,
                }
        return result

    @staticmethod
    async def upsert_skill_section(
        db: AsyncSession,
        section_key: str,
        content: Any,
        admin_name: Optional[str] = None,
    ) -> SkillCmsSection:
        norm_key = WebsiteContentRepository.normalize_skill_section_key(section_key) or section_key
        sec = await WebsiteContentRepository.get_skill_section(db, norm_key)
        content_str = json.dumps(content) if not isinstance(content, str) else content
        if sec:
            sec.content = content_str
            if admin_name:
                sec.updated_by = admin_name
        else:
            title = WebsiteContentRepository.SKILL_CMS_DEFAULTS.get(norm_key, {}).get("title", norm_key)
            sec = SkillCmsSection(
                section_key=norm_key,
                title=title,
                content=content_str,
                updated_by=admin_name or "Admin",
            )
            db.add(sec)
        await db.commit()
        await db.refresh(sec)
        return sec

    @staticmethod
    async def reset_skill_section(
        db: AsyncSession,
        section_key: str,
        admin_name: Optional[str] = None,
    ) -> SkillCmsSection:
        norm_key = WebsiteContentRepository.normalize_skill_section_key(section_key) or section_key
        default_entry = WebsiteContentRepository.SKILL_CMS_DEFAULTS.get(norm_key)
        if not default_entry:
            raise ValueError(f"No default configured for section '{section_key}'.")
        return await WebsiteContentRepository.upsert_skill_section(
            db=db,
            section_key=norm_key,
            content=default_entry["content"],
            admin_name=admin_name,
        )

    @staticmethod
    async def reset_all_skill_sections(
        db: AsyncSession,
        admin_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        for canonical_key, default_entry in WebsiteContentRepository.SKILL_CMS_DEFAULTS.items():
            await WebsiteContentRepository.upsert_skill_section(
                db=db,
                section_key=canonical_key,
                content=default_entry["content"],
                admin_name=admin_name,
            )
        return await WebsiteContentRepository.get_all_skill_sections(db)


