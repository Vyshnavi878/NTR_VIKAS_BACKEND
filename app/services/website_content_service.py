import os
import re
import uuid
import base64
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from fastapi import HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

import json
from app.core.config import settings
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
from app.repositories.website_content_repository import WebsiteContentRepository
from app.repositories.audit_log_repository import AuditLogRepository
from app.schemas.website_content import (
    GalleryPhotoCreate,
    GalleryPhotoUpdate,
    GalleryVideoCreate,
    GalleryVideoUpdate,
    PressArticleCreate,
    PressArticleUpdate,
    WebsiteSectionHeaderUpdate,
    JobsHeroConfig,
    JobsHeroUpdate,
    JobsSearchConfig,
    JobsSearchUpdate,
    JobsPopularSearchesUpdate,
    JobLocationResponse,
    JobLocationUpdate,
    JobLocationsBatchUpdate,
    JobsPageFullUpdate,
    JobsPageConfigResponse,
    PublicJobLocationsResponse,
    AboutUsHeroData,
    AboutUsHeroUpdate,
    PrincipleCardItem,
    AboutUsPrinciplesData,
    AboutUsPrinciplesUpdate,
    TeamMemberItem,
    AboutUsTeamData,
    AboutUsTeamUpdate,
    LeadershipMessageItem,
    AboutUsLeadershipData,
    AboutUsLeadershipUpdate,
    PartnerItem,
    AboutUsPartnersData,
    AboutUsPartnersUpdate,
    AboutUsFullUpdate,
    AboutUsConfigResponse,
    JobMelaHeroUpdate,
    JobMelaHeroResponse,
    SkillHeroData,
    SkillHighlightsUpdate,
    SkillMissionUpdate,
    SkillPathwayUpdate,
    SkillAdvantagesUpdate,
    SkillProgramsUpdate,
    SkillSectionResponse,
    SkillDevelopmentConfigResponse,
)

# YouTube validation regex
YOUTUBE_PATTERN = re.compile(
    r"^(https?://)?(www\.|m\.)?(youtube\.com/(watch\?.*v=|embed/|v/|shorts/)|youtu\.be/)([\w-]{11})"
)
RAW_YOUTUBE_ID_PATTERN = re.compile(r"^([\w-]{11})$")


def validate_youtube_url(url: str) -> str:
    """Validate YouTube URL and return normalized watch URL."""
    if not url or not isinstance(url, str):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A valid YouTube URL is required.",
        )
    url_trimmed = url.strip()
    match = YOUTUBE_PATTERN.search(url_trimmed)
    if match:
        video_id = match.group(5)
        return f"https://www.youtube.com/watch?v={video_id}"
    id_match = RAW_YOUTUBE_ID_PATTERN.match(url_trimmed)
    if id_match:
        video_id = id_match.group(1)
        return f"https://www.youtube.com/watch?v={video_id}"

    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail="Invalid YouTube video URL format. Please provide a standard YouTube video link.",
    )


def save_data_url_image(data_url: str, subfolder: str = "gallery") -> str:
    """Decode base64 data URL and save to file storage, returning relative URL."""
    try:
        header, encoded = data_url.split(",", 1)
        mime_match = re.search(r"data:image/(\w+);base64", header)
        ext = f".{mime_match.group(1)}" if mime_match else ".png"
        if ext == ".jpeg":
            ext = ".jpg"

        file_bytes = base64.b64decode(encoded)
        filename = f"{subfolder}_{uuid.uuid4().hex[:12]}{ext}"
        target_dir = os.path.join(settings.UPLOAD_DIR, subfolder)
        os.makedirs(target_dir, exist_ok=True)
        file_path = os.path.join(target_dir, filename)

        with open(file_path, "wb") as f:
            f.write(file_bytes)

        return f"/uploads/{subfolder}/{filename}"
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to process image data: {str(e)}",
        )


class WebsiteContentService:
    """Service handling business logic, file storage, and data validation for Website Content."""

    # ── Upload Media Helper ──

    @classmethod
    async def upload_media(
        cls,
        upload_file: UploadFile,
        subfolder: str = "gallery",
    ) -> Dict[str, Any]:
        """Validate, store, and return URL for uploaded website content media."""
        if not upload_file or not upload_file.filename:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Image file is required.",
            )

        content = await upload_file.read()
        file_size = len(content)

        if file_size == 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Uploaded file is empty.",
            )

        MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB limit
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Image file exceeds maximum allowable size of 5MB.",
            )

        content_type = (upload_file.content_type or "").lower().strip()
        filename_ext = Path(upload_file.filename).suffix.lower()

        allowed_exts = {".jpg", ".jpeg", ".png", ".webp"}
        allowed_mimes = {"image/jpeg", "image/png", "image/webp"}

        if content_type not in allowed_mimes and filename_ext not in allowed_exts:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Unsupported image format. Allowed formats: JPG, JPEG, PNG, WEBP.",
            )

        safe_subfolder = "press" if subfolder.lower() == "press" else "gallery"
        ext = filename_ext if filename_ext in allowed_exts else ".jpg"
        safe_filename = f"{safe_subfolder}_{uuid.uuid4().hex[:12]}{ext}"

        target_dir = os.path.join(settings.UPLOAD_DIR, safe_subfolder)
        os.makedirs(target_dir, exist_ok=True)
        file_path = os.path.join(target_dir, safe_filename)

        with open(file_path, "wb") as f:
            f.write(content)

        relative_url = f"/uploads/{safe_subfolder}/{safe_filename}"
        return {
            "url": relative_url,
            "filename": safe_filename,
            "size": file_size,
            "message": "Image uploaded successfully.",
        }

    # ── Photo Gallery ──

    @classmethod
    async def list_photos(
        cls,
        db: AsyncSession,
        category: Optional[str] = None,
        search: Optional[str] = None,
        is_published: Optional[bool] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[List[GalleryPhoto], int]:
        skip = max(0, (page - 1) * page_size)
        return await WebsiteContentRepository.get_photos(
            db=db,
            category=category,
            search=search,
            is_published=is_published,
            skip=skip,
            limit=page_size,
        )

    @classmethod
    async def get_photo(cls, db: AsyncSession, photo_id: str) -> GalleryPhoto:
        photo = await WebsiteContentRepository.get_photo_by_id(db, photo_id)
        if not photo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Gallery photo '{photo_id}' not found.",
            )
        return photo

    @classmethod
    async def create_photo(
        cls,
        db: AsyncSession,
        payload: GalleryPhotoCreate,
        admin_id: Optional[str] = None,
    ) -> GalleryPhoto:
        data = payload.model_dump(exclude_unset=True)

        img_url = data.get("image_url", "").strip()
        if not img_url:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Image file or URL is required for gallery photo.",
            )

        # If data URL was sent from frontend reader, save to file storage
        if img_url.startswith("data:image/"):
            data["image_url"] = save_data_url_image(img_url, "gallery")

        return await WebsiteContentRepository.create_photo(db, data, admin_id=admin_id)

    @classmethod
    async def update_photo(
        cls,
        db: AsyncSession,
        photo_id: str,
        payload: GalleryPhotoUpdate,
    ) -> GalleryPhoto:
        await cls.get_photo(db, photo_id)  # verify existence
        data = payload.model_dump(exclude_unset=True)

        if "image_url" in data and data["image_url"]:
            img_url = data["image_url"].strip()
            if img_url.startswith("data:image/"):
                data["image_url"] = save_data_url_image(img_url, "gallery")

        updated = await WebsiteContentRepository.update_photo(db, photo_id, data)
        return updated

    @classmethod
    async def delete_photo(cls, db: AsyncSession, photo_id: str) -> None:
        await cls.get_photo(db, photo_id)
        await WebsiteContentRepository.delete_photo(db, photo_id)

    # ── Video Gallery ──

    @classmethod
    async def list_videos(
        cls,
        db: AsyncSession,
        category: Optional[str] = None,
        search: Optional[str] = None,
        is_published: Optional[bool] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[List[GalleryVideo], int]:
        skip = max(0, (page - 1) * page_size)
        return await WebsiteContentRepository.get_videos(
            db=db,
            category=category,
            search=search,
            is_published=is_published,
            skip=skip,
            limit=page_size,
        )

    @classmethod
    async def get_video(cls, db: AsyncSession, video_id: str) -> GalleryVideo:
        video = await WebsiteContentRepository.get_video_by_id(db, video_id)
        if not video:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Gallery video '{video_id}' not found.",
            )
        return video

    @classmethod
    async def create_video(
        cls,
        db: AsyncSession,
        payload: GalleryVideoCreate,
        admin_id: Optional[str] = None,
    ) -> GalleryVideo:
        data = payload.model_dump(exclude_unset=True)
        raw_url = data.get("youtube_url", "")
        validated_url = validate_youtube_url(raw_url)
        data["youtube_url"] = validated_url
        return await WebsiteContentRepository.create_video(db, data, admin_id=admin_id)

    @classmethod
    async def update_video(
        cls,
        db: AsyncSession,
        video_id: str,
        payload: GalleryVideoUpdate,
    ) -> GalleryVideo:
        await cls.get_video(db, video_id)
        data = payload.model_dump(exclude_unset=True)
        if "youtube_url" in data and data["youtube_url"]:
            data["youtube_url"] = validate_youtube_url(data["youtube_url"])
        updated = await WebsiteContentRepository.update_video(db, video_id, data)
        return updated

    @classmethod
    async def delete_video(cls, db: AsyncSession, video_id: str) -> None:
        await cls.get_video(db, video_id)
        await WebsiteContentRepository.delete_video(db, video_id)

    # ── Press & News Articles ──

    @classmethod
    async def list_press_articles(
        cls,
        db: AsyncSession,
        category: Optional[str] = None,
        search: Optional[str] = None,
        is_published: Optional[bool] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[List[PressArticle], int]:
        skip = max(0, (page - 1) * page_size)
        return await WebsiteContentRepository.get_press_articles(
            db=db,
            category=category,
            search=search,
            is_published=is_published,
            skip=skip,
            limit=page_size,
        )

    @classmethod
    async def get_press_article(cls, db: AsyncSession, press_id: str) -> PressArticle:
        article = await WebsiteContentRepository.get_press_article_by_id(db, press_id)
        if not article:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Press article '{press_id}' not found.",
            )
        return article

    @classmethod
    async def create_press_article(
        cls,
        db: AsyncSession,
        payload: PressArticleCreate,
        admin_id: Optional[str] = None,
    ) -> PressArticle:
        data = payload.model_dump(exclude_unset=True)
        img_url = data.get("image_url", "").strip()
        if not img_url:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Clipping image file or URL is required for news/press item.",
            )

        if img_url.startswith("data:image/"):
            data["image_url"] = save_data_url_image(img_url, "press")

        return await WebsiteContentRepository.create_press_article(db, data, admin_id=admin_id)

    @classmethod
    async def update_press_article(
        cls,
        db: AsyncSession,
        press_id: str,
        payload: PressArticleUpdate,
    ) -> PressArticle:
        await cls.get_press_article(db, press_id)
        data = payload.model_dump(exclude_unset=True)

        if "image_url" in data and data["image_url"]:
            img_url = data["image_url"].strip()
            if img_url.startswith("data:image/"):
                data["image_url"] = save_data_url_image(img_url, "press")

        updated = await WebsiteContentRepository.update_press_article(db, press_id, data)
        return updated

    @classmethod
    async def delete_press_article(cls, db: AsyncSession, press_id: str) -> None:
        await cls.get_press_article(db, press_id)
        await WebsiteContentRepository.delete_press_article(db, press_id)

    # ── Section Headers ──

    @classmethod
    async def get_section_header(
        cls,
        db: AsyncSession,
        section_id: str,
    ) -> Optional[WebsiteSectionHeader]:
        return await WebsiteContentRepository.get_section_header(db, section_id)

    @classmethod
    async def save_section_header(
        cls,
        db: AsyncSession,
        section_id: str,
        payload: WebsiteSectionHeaderUpdate,
        admin_name: Optional[str] = None,
    ) -> WebsiteSectionHeader:
        data = payload.model_dump(exclude_unset=True)
        return await WebsiteContentRepository.upsert_section_header(
            db, section_id, data, admin_name=admin_name
        )

    # ── Jobs Page Configuration ──

    @classmethod
    async def get_jobs_page_config(
        cls,
        db: AsyncSession,
        include_all_locations: bool = True,
    ) -> JobsPageConfigResponse:
        settings = await WebsiteContentRepository.get_jobs_page_settings(db)
        locations = await WebsiteContentRepository.get_all_job_locations(
            db, is_active=None if include_all_locations else True
        )
        try:
            popular = json.loads(settings.popular_searches) if settings.popular_searches else []
        except Exception:
            popular = ["Python Developer", "React JS", "Data Analyst", "Fresher Jobs", "Hybrid Work", "FastAPI"]

        loc_responses = [
            JobLocationResponse(
                id=loc.id,
                name=loc.name,
                state_ut_type=loc.state_ut_type,
                display_order=loc.display_order,
                is_active=loc.is_active,
                created_at=loc.created_at,
                updated_at=loc.updated_at,
            )
            for loc in locations
        ]

        return JobsPageConfigResponse(
            hero=JobsHeroConfig(
                badge=settings.hero_badge,
                heading=settings.hero_heading,
                subtitle=settings.hero_subtitle,
            ),
            search=JobsSearchConfig(
                searchPlaceholder=settings.search_placeholder,
                locationPlaceholder=settings.location_placeholder,
                popularSearches=popular,
            ),
            locations=loc_responses,
            updated_by=settings.updated_by,
            updated_at=settings.updated_at,
        )

    @classmethod
    async def update_jobs_hero(
        cls,
        db: AsyncSession,
        payload: JobsHeroUpdate,
        admin_name: Optional[str] = None,
    ) -> JobsPageConfigResponse:
        data = {}
        if payload.badge is not None:
            if not payload.badge.strip():
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Hero badge cannot be empty.")
            data["hero_badge"] = payload.badge.strip()
        if payload.heading is not None:
            if not payload.heading.strip():
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Hero heading cannot be empty.")
            data["hero_heading"] = payload.heading.strip()
        if payload.subtitle is not None:
            if not payload.subtitle.strip():
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Hero subtitle cannot be empty.")
            data["hero_subtitle"] = payload.subtitle.strip()

        await WebsiteContentRepository.upsert_jobs_page_settings(db, data, admin_name=admin_name)
        return await cls.get_jobs_page_config(db)

    @classmethod
    async def update_jobs_search(
        cls,
        db: AsyncSession,
        payload: JobsSearchUpdate,
        admin_name: Optional[str] = None,
    ) -> JobsPageConfigResponse:
        data = {}
        if payload.search_placeholder is not None:
            if not payload.search_placeholder.strip():
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Search placeholder cannot be empty.")
            data["search_placeholder"] = payload.search_placeholder.strip()
        if payload.location_placeholder is not None:
            if not payload.location_placeholder.strip():
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Location placeholder cannot be empty.")
            data["location_placeholder"] = payload.location_placeholder.strip()
        if payload.popular_searches is not None:
            cleaned = cls._clean_and_validate_keywords(payload.popular_searches)
            data["popular_searches"] = json.dumps(cleaned)

        await WebsiteContentRepository.upsert_jobs_page_settings(db, data, admin_name=admin_name)
        return await cls.get_jobs_page_config(db)

    @classmethod
    async def update_jobs_popular_searches(
        cls,
        db: AsyncSession,
        payload: JobsPopularSearchesUpdate,
        admin_name: Optional[str] = None,
    ) -> JobsPageConfigResponse:
        if payload.popular_searches is None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="popular_searches list is required.")
        cleaned = cls._clean_and_validate_keywords(payload.popular_searches)
        data = {"popular_searches": json.dumps(cleaned)}
        await WebsiteContentRepository.upsert_jobs_page_settings(db, data, admin_name=admin_name)
        return await cls.get_jobs_page_config(db)

    @classmethod
    async def update_jobs_page_full(
        cls,
        db: AsyncSession,
        payload: JobsPageFullUpdate,
        admin_name: Optional[str] = None,
    ) -> JobsPageConfigResponse:
        data = {}
        if payload.hero:
            if payload.hero.badge is not None:
                if not payload.hero.badge.strip():
                    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Hero badge cannot be empty.")
                data["hero_badge"] = payload.hero.badge.strip()
            if payload.hero.heading is not None:
                if not payload.hero.heading.strip():
                    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Hero heading cannot be empty.")
                data["hero_heading"] = payload.hero.heading.strip()
            if payload.hero.subtitle is not None:
                if not payload.hero.subtitle.strip():
                    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Hero subtitle cannot be empty.")
                data["hero_subtitle"] = payload.hero.subtitle.strip()

        if payload.search:
            if payload.search.search_placeholder is not None:
                if not payload.search.search_placeholder.strip():
                    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Search placeholder cannot be empty.")
                data["search_placeholder"] = payload.search.search_placeholder.strip()
            if payload.search.location_placeholder is not None:
                if not payload.search.location_placeholder.strip():
                    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Location placeholder cannot be empty.")
                data["location_placeholder"] = payload.search.location_placeholder.strip()
            if payload.search.popular_searches is not None:
                data["popular_searches"] = json.dumps(cls._clean_and_validate_keywords(payload.search.popular_searches))

        if data:
            await WebsiteContentRepository.upsert_jobs_page_settings(db, data, admin_name=admin_name)

        return await cls.get_jobs_page_config(db)

    @classmethod
    async def reset_jobs_page_config(
        cls,
        db: AsyncSession,
        admin_name: Optional[str] = None,
    ) -> JobsPageConfigResponse:
        await WebsiteContentRepository.reset_jobs_page_settings(db, admin_name=admin_name)
        return await cls.get_jobs_page_config(db)

    @classmethod
    def _clean_and_validate_keywords(cls, keywords: List[str]) -> List[str]:
        seen = set()
        cleaned = []
        for raw in keywords:
            if not isinstance(raw, str):
                continue
            kw = raw.strip()
            if not kw:
                continue
            if len(kw) > 100:
                kw = kw[:100]
            kw_lower = kw.lower()
            if kw_lower not in seen:
                seen.add(kw_lower)
                cleaned.append(kw)
        return cleaned

    # ── Job Locations Management ──

    @classmethod
    async def get_all_job_locations(
        cls,
        db: AsyncSession,
        is_active: Optional[bool] = None,
    ) -> List[JobLocationResponse]:
        locs = await WebsiteContentRepository.get_all_job_locations(db, is_active=is_active)
        return [
            JobLocationResponse(
                id=loc.id,
                name=loc.name,
                state_ut_type=loc.state_ut_type,
                display_order=loc.display_order,
                is_active=loc.is_active,
                created_at=loc.created_at,
                updated_at=loc.updated_at,
            )
            for loc in locs
        ]

    @classmethod
    async def update_job_location(
        cls,
        db: AsyncSession,
        location_id: str,
        payload: JobLocationUpdate,
    ) -> JobLocationResponse:
        loc = await WebsiteContentRepository.get_job_location_by_id(db, location_id)
        if not loc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Job location '{location_id}' not found.")

        data = payload.model_dump(exclude_unset=True)
        if "name" in data and data["name"]:
            new_name = data["name"].strip()
            if not new_name:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Region name cannot be empty.")
            existing = await WebsiteContentRepository.get_job_location_by_name(db, new_name)
            if existing and existing.id != location_id:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Region '{new_name}' already exists.")
            data["name"] = new_name

        updated = await WebsiteContentRepository.update_job_location(db, location_id, data)
        return JobLocationResponse(
            id=updated.id,
            name=updated.name,
            state_ut_type=updated.state_ut_type,
            display_order=updated.display_order,
            is_active=updated.is_active,
            created_at=updated.created_at,
            updated_at=updated.updated_at,
        )

    @classmethod
    async def batch_update_job_locations(
        cls,
        db: AsyncSession,
        payload: JobLocationsBatchUpdate,
    ) -> List[JobLocationResponse]:
        updates = [item.model_dump() for item in payload.locations]
        await WebsiteContentRepository.batch_update_job_locations(db, updates)
        return await cls.get_all_job_locations(db)

    @classmethod
    async def reset_job_locations(cls, db: AsyncSession) -> List[JobLocationResponse]:
        await WebsiteContentRepository.reset_job_locations(db)
        return await cls.get_all_job_locations(db)

    @classmethod
    async def get_public_job_locations(cls, db: AsyncSession) -> PublicJobLocationsResponse:
        active_locs = await WebsiteContentRepository.get_all_job_locations(db, is_active=True)
        states = [l.name for l in active_locs if l.state_ut_type == "state"]
        uts = [l.name for l in active_locs if l.state_ut_type == "union_territory"]
        items = [
            JobLocationResponse(
                id=loc.id,
                name=loc.name,
                state_ut_type=loc.state_ut_type,
                display_order=loc.display_order,
                is_active=loc.is_active,
                created_at=loc.created_at,
                updated_at=loc.updated_at,
            )
            for loc in active_locs
        ]
        all_names = [l.name for l in active_locs]
        return PublicJobLocationsResponse(
            states=states,
            union_territories=uts,
            items=items,
            all_locations=all_names,
        )

    # ── About Us Content Management ──

    @classmethod
    def _parse_json_safely(cls, raw: Optional[str], default_val: Any) -> Any:
        if not raw:
            return default_val
        try:
            return json.loads(raw)
        except Exception:
            return default_val

    @classmethod
    def _build_about_us_response(cls, settings: AboutUsSetting, is_public: bool = False) -> AboutUsConfigResponse:
        cards_raw = cls._parse_json_safely(settings.wwsf_cards, [])
        members_raw = cls._parse_json_safely(settings.team_members, [])
        messages_raw = cls._parse_json_safely(settings.leadership_messages, [])
        partners_raw = cls._parse_json_safely(settings.partners_list, [])
        stats_raw = cls._parse_json_safely(settings.stats_data, [])

        if is_public:
            # Filter partners so only active ones appear on the public site
            partners_raw = [p for p in partners_raw if p.get("active") is not False]

        return AboutUsConfigResponse(
            hero=AboutUsHeroData(
                badge=settings.hero_badge,
                heading=settings.hero_heading,
                description=settings.hero_description,
            ),
            stats=stats_raw,
            whatWeStandFor=AboutUsPrinciplesData(
                heading=settings.wwsf_heading,
                description=settings.wwsf_description,
                cards=[PrincipleCardItem(**c) for c in cards_raw],
            ),
            team=AboutUsTeamData(
                badge=settings.team_badge,
                heading=settings.team_heading,
                description=settings.team_description,
                members=[TeamMemberItem(**m) for m in members_raw],
            ),
            leadershipMessages=AboutUsLeadershipData(
                badge=settings.leadership_badge,
                heading=settings.leadership_heading,
                description=settings.leadership_description or "",
                messages=[LeadershipMessageItem(**msg) for msg in messages_raw],
            ),
            partners=AboutUsPartnersData(
                heading=settings.partners_heading,
                description=settings.partners_description,
                list=[PartnerItem(**p) for p in partners_raw],
            ),
            updated_by=settings.updated_by,
            updated_at=settings.updated_at,
        )

    @classmethod
    async def get_about_us_config(cls, db: AsyncSession, is_public: bool = False) -> AboutUsConfigResponse:
        settings = await WebsiteContentRepository.get_about_us_settings(db)
        return cls._build_about_us_response(settings, is_public=is_public)

    @classmethod
    async def update_about_us_hero(
        cls,
        db: AsyncSession,
        payload: AboutUsHeroUpdate,
        admin_name: Optional[str] = None,
    ) -> AboutUsConfigResponse:
        data = {
            "hero_badge": payload.badge.strip(),
            "hero_heading": payload.heading.strip(),
            "hero_description": payload.description.strip(),
        }
        updated = await WebsiteContentRepository.upsert_about_us_settings(db, data, admin_name=admin_name)
        return cls._build_about_us_response(updated, is_public=False)

    @classmethod
    async def update_about_us_principles(
        cls,
        db: AsyncSession,
        payload: AboutUsPrinciplesUpdate,
        admin_name: Optional[str] = None,
    ) -> AboutUsConfigResponse:
        cards_list = [c.model_dump() for c in payload.cards]
        data = {
            "wwsf_heading": payload.heading.strip(),
            "wwsf_description": payload.description.strip(),
            "wwsf_cards": json.dumps(cards_list),
        }
        updated = await WebsiteContentRepository.upsert_about_us_settings(db, data, admin_name=admin_name)
        return cls._build_about_us_response(updated, is_public=False)

    @classmethod
    async def update_about_us_team(
        cls,
        db: AsyncSession,
        payload: AboutUsTeamUpdate,
        admin_name: Optional[str] = None,
    ) -> AboutUsConfigResponse:
        members_list = [m.model_dump() for m in payload.members]
        data = {
            "team_badge": payload.badge.strip(),
            "team_heading": payload.heading.strip(),
            "team_description": payload.description.strip(),
            "team_members": json.dumps(members_list),
        }
        updated = await WebsiteContentRepository.upsert_about_us_settings(db, data, admin_name=admin_name)
        return cls._build_about_us_response(updated, is_public=False)

    @classmethod
    async def update_about_us_leadership(
        cls,
        db: AsyncSession,
        payload: AboutUsLeadershipUpdate,
        admin_name: Optional[str] = None,
    ) -> AboutUsConfigResponse:
        messages_list = [m.model_dump() for m in payload.messages]
        data = {
            "leadership_badge": payload.badge.strip(),
            "leadership_heading": payload.heading.strip(),
            "leadership_description": (payload.description or "").strip(),
            "leadership_messages": json.dumps(messages_list),
        }
        updated = await WebsiteContentRepository.upsert_about_us_settings(db, data, admin_name=admin_name)
        return cls._build_about_us_response(updated, is_public=False)

    @classmethod
    async def update_about_us_partners(
        cls,
        db: AsyncSession,
        payload: AboutUsPartnersUpdate,
        admin_name: Optional[str] = None,
    ) -> AboutUsConfigResponse:
        partners_list = [p.model_dump() for p in payload.list]
        data = {
            "partners_heading": payload.heading.strip(),
            "partners_description": payload.description.strip(),
            "partners_list": json.dumps(partners_list),
        }
        updated = await WebsiteContentRepository.upsert_about_us_settings(db, data, admin_name=admin_name)
        return cls._build_about_us_response(updated, is_public=False)

    @classmethod
    async def update_about_us_full(
        cls,
        db: AsyncSession,
        payload: AboutUsFullUpdate,
        admin_name: Optional[str] = None,
    ) -> AboutUsConfigResponse:
        data: Dict[str, Any] = {}
        if payload.hero:
            data["hero_badge"] = payload.hero.badge.strip()
            data["hero_heading"] = payload.hero.heading.strip()
            data["hero_description"] = payload.hero.description.strip()
        if payload.stats is not None:
            data["stats_data"] = json.dumps(payload.stats)
        if payload.whatWeStandFor:
            data["wwsf_heading"] = payload.whatWeStandFor.heading.strip()
            data["wwsf_description"] = payload.whatWeStandFor.description.strip()
            data["wwsf_cards"] = json.dumps([c.model_dump() for c in payload.whatWeStandFor.cards])
        if payload.team:
            data["team_badge"] = payload.team.badge.strip()
            data["team_heading"] = payload.team.heading.strip()
            data["team_description"] = payload.team.description.strip()
            data["team_members"] = json.dumps([m.model_dump() for m in payload.team.members])
        if payload.leadershipMessages:
            data["leadership_badge"] = payload.leadershipMessages.badge.strip()
            data["leadership_heading"] = payload.leadershipMessages.heading.strip()
            data["leadership_description"] = (payload.leadershipMessages.description or "").strip()
            data["leadership_messages"] = json.dumps([m.model_dump() for m in payload.leadershipMessages.messages])
        if payload.partners:
            data["partners_heading"] = payload.partners.heading.strip()
            data["partners_description"] = payload.partners.description.strip()
            data["partners_list"] = json.dumps([p.model_dump() for p in payload.partners.list])

        updated = await WebsiteContentRepository.upsert_about_us_settings(db, data, admin_name=admin_name)
        return cls._build_about_us_response(updated, is_public=False)

    @classmethod
    async def reset_about_us_config(
        cls,
        db: AsyncSession,
        admin_name: Optional[str] = None,
    ) -> AboutUsConfigResponse:
        settings = await WebsiteContentRepository.reset_about_us_settings(db, admin_name=admin_name)
        return cls._build_about_us_response(settings, is_public=False)

    # ── Job Melas Page Hero Service Methods ──

    @classmethod
    async def get_job_mela_hero(cls, db: AsyncSession) -> JobMelaHeroResponse:
        """Retrieve current saved Job Melas page hero content."""
        setting = await WebsiteContentRepository.get_job_mela_settings(db)
        return JobMelaHeroResponse(
            badge=setting.hero_badge,
            heading=setting.hero_heading,
            description=setting.hero_description,
            hero_badge=setting.hero_badge,
            hero_heading=setting.hero_heading,
            hero_description=setting.hero_description,
            hero={
                "badge": setting.hero_badge,
                "heading": setting.hero_heading,
                "description": setting.hero_description,
            },
            updated_by=setting.updated_by,
            updated_at=setting.updated_at,
        )

    @classmethod
    async def update_job_mela_hero(
        cls,
        db: AsyncSession,
        payload: JobMelaHeroUpdate,
        admin_name: Optional[str] = None,
    ) -> JobMelaHeroResponse:
        """Update Job Melas page hero content with validation."""
        data: Dict[str, Any] = {}
        badge = payload.badge or payload.hero_badge
        if badge is not None:
            if not badge.strip():
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Hero badge cannot be empty.",
                )
            data["badge"] = badge.strip()

        heading = payload.heading or payload.hero_heading
        if heading is not None:
            if not heading.strip():
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Main heading cannot be empty.",
                )
            data["heading"] = heading.strip()

        description = payload.description or payload.hero_description
        if description is not None:
            if not description.strip():
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Hero description cannot be empty.",
                )
            data["description"] = description.strip()

        setting = await WebsiteContentRepository.upsert_job_mela_settings(
            db=db, data=data, admin_name=admin_name
        )
        return JobMelaHeroResponse(
            badge=setting.hero_badge,
            heading=setting.hero_heading,
            description=setting.hero_description,
            hero_badge=setting.hero_badge,
            hero_heading=setting.hero_heading,
            hero_description=setting.hero_description,
            hero={
                "badge": setting.hero_badge,
                "heading": setting.hero_heading,
                "description": setting.hero_description,
            },
            updated_by=setting.updated_by,
            updated_at=setting.updated_at,
        )

    @classmethod
    async def reset_job_mela_hero(
        cls,
        db: AsyncSession,
        admin_name: Optional[str] = None,
    ) -> JobMelaHeroResponse:
        """Reset Job Melas page hero content to default values."""
        setting = await WebsiteContentRepository.reset_job_mela_settings(
            db=db, admin_name=admin_name
        )
        return JobMelaHeroResponse(
            badge=setting.hero_badge,
            heading=setting.hero_heading,
            description=setting.hero_description,
            hero_badge=setting.hero_badge,
            hero_heading=setting.hero_heading,
            hero_description=setting.hero_description,
            hero={
                "badge": setting.hero_badge,
                "heading": setting.hero_heading,
                "description": setting.hero_description,
            },
            updated_by=setting.updated_by,
            updated_at=setting.updated_at,
        )

    # ── Skill Development CMS Service Methods ──

    @classmethod
    async def get_skill_development_config(cls, db: AsyncSession) -> SkillDevelopmentConfigResponse:
        """Retrieve all six Skill Development sections in one aggregated response."""
        all_sections = await WebsiteContentRepository.get_all_skill_sections(db)

        hero_c = all_sections.get("skills_hero", {}).get("content", {})
        highlights_c = all_sections.get("skills_highlights", {}).get("content", [])
        mission_c = all_sections.get("skills_mission", {}).get("content", {})
        pathway_c = all_sections.get("skills_pathway", {}).get("content", {})
        advantages_c = all_sections.get("skills_advantages", {}).get("content", {})
        programs_c = all_sections.get("skills_programs", {}).get("content", {})

        latest_updated_at = None
        latest_updated_by = None
        for sec in all_sections.values():
            if sec.get("updated_at") and (latest_updated_at is None or sec["updated_at"] > latest_updated_at):
                latest_updated_at = sec["updated_at"]
                latest_updated_by = sec.get("updated_by")

        return SkillDevelopmentConfigResponse(
            skills_hero=hero_c,
            skills_highlights=highlights_c,
            skills_mission=mission_c,
            skills_pathway=pathway_c,
            skills_advantages=advantages_c,
            skills_programs=programs_c,
            hero=hero_c,
            highlights=highlights_c,
            empoweringSkills=mission_c,
            trainingJourney=pathway_c,
            whyChoose=advantages_c,
            programsWeOffer=programs_c,
            updated_by=latest_updated_by,
            updated_at=latest_updated_at,
        )

    @classmethod
    async def get_skill_section(cls, db: AsyncSession, section_key: str) -> SkillSectionResponse:
        """Retrieve a single Skill Development section by key."""
        norm_key = WebsiteContentRepository.normalize_skill_section_key(section_key)
        if not norm_key:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid section identifier '{section_key}'. Allowed sections: skills_hero, skills_highlights, skills_mission, skills_pathway, skills_advantages, skills_programs.",
            )

        sec = await WebsiteContentRepository.get_skill_section(db, norm_key)
        try:
            parsed = json.loads(sec.content) if isinstance(sec.content, str) else sec.content
        except Exception:
            parsed = sec.content

        return SkillSectionResponse(
            section_key=norm_key,
            title=sec.title,
            content=parsed,
            updated_by=sec.updated_by,
            updated_at=sec.updated_at,
        )

    @classmethod
    async def update_skill_section(
        cls,
        db: AsyncSession,
        section_key: str,
        payload_data: Any,
        admin_name: Optional[str] = None,
    ) -> SkillSectionResponse:
        """Validate and update a single Skill Development section."""
        norm_key = WebsiteContentRepository.normalize_skill_section_key(section_key)
        if not norm_key:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid section identifier '{section_key}'. Allowed sections: skills_hero, skills_highlights, skills_mission, skills_pathway, skills_advantages, skills_programs.",
            )

        # Validate structured payload against each section's exact rules
        validated_content: Any = None
        try:
            if norm_key == "skills_hero":
                validated = SkillHeroData.model_validate(payload_data)
                validated_content = validated.model_dump()
            elif norm_key == "skills_highlights":
                validated = SkillHighlightsUpdate.model_validate(payload_data)
                validated_content = [item.model_dump() for item in validated.highlights]
            elif norm_key == "skills_mission":
                validated = SkillMissionUpdate.model_validate(payload_data)
                validated_content = validated.model_dump()
            elif norm_key == "skills_pathway":
                validated = SkillPathwayUpdate.model_validate(payload_data)
                validated_content = validated.model_dump()
            elif norm_key == "skills_advantages":
                validated = SkillAdvantagesUpdate.model_validate(payload_data)
                validated_content = validated.model_dump()
            elif norm_key == "skills_programs":
                validated = SkillProgramsUpdate.model_validate(payload_data)
                validated_content = validated.model_dump()
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid payload for section '{section_key}': {str(exc)}",
            )

        updated_sec = await WebsiteContentRepository.upsert_skill_section(
            db=db,
            section_key=norm_key,
            content=validated_content,
            admin_name=admin_name,
        )

        # Record audit log
        try:
            await AuditLogRepository.create_log(
                db=db,
                actor=admin_name or "Administrator",
                action="Skill Development CMS Section Updated",
                entity="WEBSITE_CONTENT",
                entity_id=norm_key,
                target_name=f"Skill CMS: {norm_key}",
                result="SUCCESS",
            )
        except Exception:
            pass

        return SkillSectionResponse(
            section_key=updated_sec.section_key,
            title=updated_sec.title,
            content=validated_content,
            updated_by=updated_sec.updated_by,
            updated_at=updated_sec.updated_at,
        )

    @classmethod
    async def reset_skill_section(
        cls,
        db: AsyncSession,
        section_key: str,
        admin_name: Optional[str] = None,
    ) -> SkillSectionResponse:
        """Reset a single Skill Development section to default values."""
        norm_key = WebsiteContentRepository.normalize_skill_section_key(section_key)
        if not norm_key:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid section identifier '{section_key}'. Allowed sections: skills_hero, skills_highlights, skills_mission, skills_pathway, skills_advantages, skills_programs.",
            )

        reset_sec = await WebsiteContentRepository.reset_skill_section(
            db=db,
            section_key=norm_key,
            admin_name=admin_name,
        )

        try:
            parsed = json.loads(reset_sec.content) if isinstance(reset_sec.content, str) else reset_sec.content
        except Exception:
            parsed = reset_sec.content

        # Record audit log
        try:
            await AuditLogRepository.create_log(
                db=db,
                actor=admin_name or "Administrator",
                action="Skill Development CMS Section Reset to Defaults",
                entity="WEBSITE_CONTENT",
                entity_id=norm_key,
                target_name=f"Skill CMS: {norm_key}",
                result="SUCCESS",
            )
        except Exception:
            pass

        return SkillSectionResponse(
            section_key=reset_sec.section_key,
            title=reset_sec.title,
            content=parsed,
            updated_by=reset_sec.updated_by,
            updated_at=reset_sec.updated_at,
        )

    @classmethod
    async def reset_all_skill_sections(
        cls,
        db: AsyncSession,
        admin_name: Optional[str] = None,
    ) -> SkillDevelopmentConfigResponse:
        """Reset all Skill Development sections to defaults."""
        await WebsiteContentRepository.reset_all_skill_sections(db, admin_name)

        try:
            await AuditLogRepository.create_log(
                db=db,
                actor=admin_name or "Administrator",
                action="All Skill Development CMS Sections Reset to Defaults",
                entity="WEBSITE_CONTENT",
                entity_id="skills_all",
                target_name="Skill CMS: All Sections",
                result="SUCCESS",
            )
        except Exception:
            pass

        return await cls.get_skill_development_config(db)


