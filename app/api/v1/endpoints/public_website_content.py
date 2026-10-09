from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_database
from app.schemas.website_content import (
    GalleryPhotoResponse,
    GalleryVideoResponse,
    PressArticleResponse,
    WebsiteSectionHeaderResponse,
)
from app.services.website_content_service import WebsiteContentService

router = APIRouter(
    prefix="/public/website-content",
    tags=["Public Website Content"],
)


@router.get(
    "/gallery/photos",
    response_model=List[GalleryPhotoResponse],
    summary="Public read-only published gallery photos",
)
async def get_public_gallery_photos(
    category: Optional[str] = Query(None, description="Filter by category"),
    search: Optional[str] = Query(None, description="Search by title or description"),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=200),
    db: AsyncSession = Depends(get_database),
):
    """Retrieve published photos for public Home and Gallery pages."""
    items, _ = await WebsiteContentService.list_photos(
        db=db,
        category=category,
        search=search,
        is_published=True,  # strictly published records only
        page=page,
        page_size=page_size,
    )
    return items


@router.get(
    "/gallery/videos",
    response_model=List[GalleryVideoResponse],
    summary="Public read-only published gallery videos",
)
async def get_public_gallery_videos(
    category: Optional[str] = Query(None, description="Filter by category"),
    search: Optional[str] = Query(None, description="Search by title or description"),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=200),
    db: AsyncSession = Depends(get_database),
):
    """Retrieve published videos for public Home and Gallery pages."""
    items, _ = await WebsiteContentService.list_videos(
        db=db,
        category=category,
        search=search,
        is_published=True,  # strictly published records only
        page=page,
        page_size=page_size,
    )
    return items


@router.get(
    "/press",
    response_model=List[PressArticleResponse],
    summary="Public read-only published press clippings & news articles",
)
async def get_public_press_articles(
    category: Optional[str] = Query(None, description="Filter by category"),
    search: Optional[str] = Query(None, description="Search by title or summary"),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=200),
    db: AsyncSession = Depends(get_database),
):
    """Retrieve published newspaper articles for public Home and News sections."""
    items, _ = await WebsiteContentService.list_press_articles(
        db=db,
        category=category,
        search=search,
        is_published=True,  # strictly published records only
        page=page,
        page_size=page_size,
    )
    return items


@router.get(
    "/sections/{section_id}",
    response_model=Optional[WebsiteSectionHeaderResponse],
    summary="Public read-only section header configuration",
)
async def get_public_section_header(
    section_id: str,
    db: AsyncSession = Depends(get_database),
):
    return await WebsiteContentService.get_section_header(db=db, section_id=section_id)
