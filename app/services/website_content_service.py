import os
import re
import uuid
import base64
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from fastapi import HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.website_content import (
    GalleryPhoto,
    GalleryVideo,
    PressArticle,
    WebsiteSectionHeader,
)
from app.repositories.website_content_repository import WebsiteContentRepository
from app.schemas.website_content import (
    GalleryPhotoCreate,
    GalleryPhotoUpdate,
    GalleryVideoCreate,
    GalleryVideoUpdate,
    PressArticleCreate,
    PressArticleUpdate,
    WebsiteSectionHeaderUpdate,
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
