import uuid
from typing import Optional, List, Tuple, Dict, Any
from sqlalchemy import select, func, or_, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.website_content import (
    GalleryPhoto,
    GalleryVideo,
    PressArticle,
    WebsiteSectionHeader,
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
