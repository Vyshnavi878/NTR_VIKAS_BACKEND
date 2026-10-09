from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, Field, model_validator


# ── Gallery Photos ──

class GalleryPhotoCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    category: str = Field(default="Job Melas", max_length=100)
    date: Optional[str] = None
    image_url: Optional[str] = None
    imageUrl: Optional[str] = None
    description: Optional[str] = None
    display_order: Optional[int] = 0
    is_published: Optional[bool] = True

    @model_validator(mode="before")
    @classmethod
    def reconcile_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "imageUrl" in data and not data.get("image_url"):
                data["image_url"] = data["imageUrl"]
        return data


class GalleryPhotoUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    category: Optional[str] = Field(None, max_length=100)
    date: Optional[str] = None
    image_url: Optional[str] = None
    imageUrl: Optional[str] = None
    description: Optional[str] = None
    display_order: Optional[int] = None
    is_published: Optional[bool] = None

    @model_validator(mode="before")
    @classmethod
    def reconcile_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "imageUrl" in data and not data.get("image_url"):
                data["image_url"] = data["imageUrl"]
        return data


class GalleryPhotoResponse(BaseModel):
    id: str
    title: str
    category: str
    date: str
    image_url: str
    imageUrl: Optional[str] = None
    description: Optional[str] = None
    display_order: int = 0
    is_published: bool = True
    created_by_admin_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @model_validator(mode="before")
    @classmethod
    def populate_aliases(cls, data: Any) -> Any:
        if hasattr(data, "__dict__"):
            img_url = getattr(data, "image_url", "")
            return {
                "id": getattr(data, "id", ""),
                "title": getattr(data, "title", ""),
                "category": getattr(data, "category", "Job Melas"),
                "date": getattr(data, "date", ""),
                "image_url": img_url,
                "imageUrl": img_url,
                "description": getattr(data, "description", None),
                "display_order": getattr(data, "display_order", 0),
                "is_published": getattr(data, "is_published", True),
                "created_by_admin_id": getattr(data, "created_by_admin_id", None),
                "created_at": getattr(data, "created_at", None),
                "updated_at": getattr(data, "updated_at", None),
            }
        elif isinstance(data, dict):
            url = data.get("image_url") or data.get("imageUrl") or ""
            data["image_url"] = url
            data["imageUrl"] = url
        return data

    model_config = {"from_attributes": True}


class GalleryPhotosListResponse(BaseModel):
    items: List[GalleryPhotoResponse]
    total: int


# ── Gallery Videos ──

class GalleryVideoCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    youtube_url: Optional[str] = None
    youtubeUrl: Optional[str] = None
    video_url: Optional[str] = None
    category: str = Field(default="Job Melas", max_length=100)
    date: Optional[str] = None
    description: Optional[str] = None
    display_order: Optional[int] = 0
    is_published: Optional[bool] = True

    @model_validator(mode="before")
    @classmethod
    def reconcile_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            url = data.get("youtube_url") or data.get("youtubeUrl") or data.get("video_url")
            data["youtube_url"] = url
        return data


class GalleryVideoUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    youtube_url: Optional[str] = None
    youtubeUrl: Optional[str] = None
    video_url: Optional[str] = None
    category: Optional[str] = Field(None, max_length=100)
    date: Optional[str] = None
    description: Optional[str] = None
    display_order: Optional[int] = None
    is_published: Optional[bool] = None

    @model_validator(mode="before")
    @classmethod
    def reconcile_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            url = data.get("youtube_url") or data.get("youtubeUrl") or data.get("video_url")
            if url:
                data["youtube_url"] = url
        return data


class GalleryVideoResponse(BaseModel):
    id: str
    title: str
    youtube_url: str
    youtubeUrl: Optional[str] = None
    video_url: Optional[str] = None
    category: str
    date: Optional[str] = None
    description: Optional[str] = None
    display_order: int = 0
    is_published: bool = True
    created_by_admin_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @model_validator(mode="before")
    @classmethod
    def populate_aliases(cls, data: Any) -> Any:
        if hasattr(data, "__dict__"):
            yt = getattr(data, "youtube_url", "")
            return {
                "id": getattr(data, "id", ""),
                "title": getattr(data, "title", ""),
                "youtube_url": yt,
                "youtubeUrl": yt,
                "video_url": yt,
                "category": getattr(data, "category", "Job Melas"),
                "date": getattr(data, "date", None),
                "description": getattr(data, "description", None),
                "display_order": getattr(data, "display_order", 0),
                "is_published": getattr(data, "is_published", True),
                "created_by_admin_id": getattr(data, "created_by_admin_id", None),
                "created_at": getattr(data, "created_at", None),
                "updated_at": getattr(data, "updated_at", None),
            }
        elif isinstance(data, dict):
            yt = data.get("youtube_url") or data.get("youtubeUrl") or data.get("video_url") or ""
            data["youtube_url"] = yt
            data["youtubeUrl"] = yt
            data["video_url"] = yt
        return data

    model_config = {"from_attributes": True}


class GalleryVideosListResponse(BaseModel):
    items: List[GalleryVideoResponse]
    total: int


# ── Press & News Articles ──

class PressArticleCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    newspaper: Optional[str] = None
    publication_name: Optional[str] = None
    date: Optional[str] = None
    publication_date: Optional[str] = None
    edition: Optional[str] = None
    image_url: Optional[str] = None
    imageUrl: Optional[str] = None
    source_url: Optional[str] = None
    sourceUrl: Optional[str] = None
    article_url: Optional[str] = None
    summary: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = "Press Coverage"
    display_order: Optional[int] = 0
    is_published: Optional[bool] = True

    @model_validator(mode="before")
    @classmethod
    def reconcile_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            paper = data.get("newspaper") or data.get("publication_name") or "Special Press Bulletin"
            data["newspaper"] = paper
            dt = data.get("date") or data.get("publication_date")
            data["date"] = dt
            img = data.get("image_url") or data.get("imageUrl")
            data["image_url"] = img
            src = data.get("source_url") or data.get("sourceUrl") or data.get("article_url")
            data["source_url"] = src
            sm = data.get("summary") or data.get("description")
            data["summary"] = sm
        return data


class PressArticleUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    newspaper: Optional[str] = None
    publication_name: Optional[str] = None
    date: Optional[str] = None
    publication_date: Optional[str] = None
    edition: Optional[str] = None
    image_url: Optional[str] = None
    imageUrl: Optional[str] = None
    source_url: Optional[str] = None
    sourceUrl: Optional[str] = None
    article_url: Optional[str] = None
    summary: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    display_order: Optional[int] = None
    is_published: Optional[bool] = None

    @model_validator(mode="before")
    @classmethod
    def reconcile_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "publication_name" in data and not data.get("newspaper"):
                data["newspaper"] = data["publication_name"]
            if "publication_date" in data and not data.get("date"):
                data["date"] = data["publication_date"]
            if "imageUrl" in data and not data.get("image_url"):
                data["image_url"] = data["imageUrl"]
            if "sourceUrl" in data and not data.get("source_url"):
                data["source_url"] = data["sourceUrl"]
            elif "article_url" in data and not data.get("source_url"):
                data["source_url"] = data["article_url"]
            if "description" in data and not data.get("summary"):
                data["summary"] = data["description"]
        return data


class PressArticleResponse(BaseModel):
    id: str
    title: str
    newspaper: str
    publication_name: Optional[str] = None
    date: str
    publication_date: Optional[str] = None
    edition: Optional[str] = None
    image_url: str
    imageUrl: Optional[str] = None
    source_url: Optional[str] = None
    sourceUrl: Optional[str] = None
    article_url: Optional[str] = None
    summary: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = "Press Coverage"
    display_order: int = 0
    is_published: bool = True
    created_by_admin_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @model_validator(mode="before")
    @classmethod
    def populate_aliases(cls, data: Any) -> Any:
        if hasattr(data, "__dict__"):
            img = getattr(data, "image_url", "")
            paper = getattr(data, "newspaper", "")
            dt = getattr(data, "date", "")
            src = getattr(data, "source_url", None)
            sm = getattr(data, "summary", None)
            return {
                "id": getattr(data, "id", ""),
                "title": getattr(data, "title", ""),
                "newspaper": paper,
                "publication_name": paper,
                "date": dt,
                "publication_date": dt,
                "edition": getattr(data, "edition", None),
                "image_url": img,
                "imageUrl": img,
                "source_url": src,
                "sourceUrl": src,
                "article_url": src,
                "summary": sm,
                "description": sm,
                "category": getattr(data, "category", "Press Coverage"),
                "display_order": getattr(data, "display_order", 0),
                "is_published": getattr(data, "is_published", True),
                "created_by_admin_id": getattr(data, "created_by_admin_id", None),
                "created_at": getattr(data, "created_at", None),
                "updated_at": getattr(data, "updated_at", None),
            }
        elif isinstance(data, dict):
            img = data.get("image_url") or data.get("imageUrl") or ""
            paper = data.get("newspaper") or data.get("publication_name") or ""
            dt = data.get("date") or data.get("publication_date") or ""
            src = data.get("source_url") or data.get("sourceUrl") or data.get("article_url")
            sm = data.get("summary") or data.get("description")
            data["image_url"] = img
            data["imageUrl"] = img
            data["newspaper"] = paper
            data["publication_name"] = paper
            data["date"] = dt
            data["publication_date"] = dt
            data["source_url"] = src
            data["sourceUrl"] = src
            data["article_url"] = src
            data["summary"] = sm
            data["description"] = sm
        return data

    model_config = {"from_attributes": True}


class PressArticlesListResponse(BaseModel):
    items: List[PressArticleResponse]
    total: int


# ── Section Headers ──

class WebsiteSectionHeaderUpdate(BaseModel):
    badge: Optional[str] = None
    heading1: Optional[str] = None
    heading2: Optional[str] = None
    subtitle: Optional[str] = None


class WebsiteSectionHeaderResponse(BaseModel):
    id: str
    badge: Optional[str] = None
    heading1: Optional[str] = None
    heading2: Optional[str] = None
    subtitle: Optional[str] = None
    updated_by: Optional[str] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
