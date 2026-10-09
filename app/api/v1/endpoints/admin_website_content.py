from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_database, get_current_admin
from app.models.user import User
from app.schemas.website_content import (
    GalleryPhotoCreate,
    GalleryPhotoUpdate,
    GalleryPhotoResponse,
    GalleryPhotosListResponse,
    GalleryVideoCreate,
    GalleryVideoUpdate,
    GalleryVideoResponse,
    GalleryVideosListResponse,
    PressArticleCreate,
    PressArticleUpdate,
    PressArticleResponse,
    PressArticlesListResponse,
    WebsiteSectionHeaderUpdate,
    WebsiteSectionHeaderResponse,
)
from app.services.website_content_service import WebsiteContentService

router = APIRouter(
    prefix="/admin/website-content",
    tags=["Admin Website Content Management"],
)


# ── File / Media Upload ──

@router.post(
    "/upload",
    status_code=status.HTTP_201_CREATED,
    summary="Upload image file for website gallery or press clippings",
)
async def upload_media(
    file: UploadFile = File(..., description="Image file (JPG, JPEG, PNG, WEBP max 5MB)"),
    section: str = Query("gallery", description="'gallery' or 'press'"),
    current_admin: User = Depends(get_current_admin),
) -> Dict[str, Any]:
    """Store uploaded image file on server and return its static URL."""
    return await WebsiteContentService.upload_media(upload_file=file, subfolder=section)


# ── Photo Gallery Management ──

@router.get(
    "/gallery/photos",
    response_model=List[GalleryPhotoResponse],
    summary="List all photo gallery entries for admin",
)
async def list_admin_gallery_photos(
    category: Optional[str] = Query(None, description="Filter by category"),
    search: Optional[str] = Query(None, description="Search by title or description"),
    is_published: Optional[bool] = Query(None, description="Filter by publication status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=200),
    db: AsyncSession = Depends(get_database),
    current_admin: User = Depends(get_current_admin),
):
    items, _ = await WebsiteContentService.list_photos(
        db=db,
        category=category,
        search=search,
        is_published=is_published,
        page=page,
        page_size=page_size,
    )
    return items


@router.post(
    "/gallery/photos",
    response_model=GalleryPhotoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new photo gallery entry",
)
async def create_gallery_photo(
    payload: GalleryPhotoCreate,
    db: AsyncSession = Depends(get_database),
    current_admin: User = Depends(get_current_admin),
):
    return await WebsiteContentService.create_photo(
        db=db,
        payload=payload,
        admin_id=current_admin.id,
    )


@router.get(
    "/gallery/photos/{photo_id}",
    response_model=GalleryPhotoResponse,
    summary="Get single photo gallery entry",
)
async def get_gallery_photo(
    photo_id: str,
    db: AsyncSession = Depends(get_database),
    current_admin: User = Depends(get_current_admin),
):
    return await WebsiteContentService.get_photo(db=db, photo_id=photo_id)


@router.patch(
    "/gallery/photos/{photo_id}",
    response_model=GalleryPhotoResponse,
    summary="Update photo gallery entry",
)
async def update_gallery_photo(
    photo_id: str,
    payload: GalleryPhotoUpdate,
    db: AsyncSession = Depends(get_database),
    current_admin: User = Depends(get_current_admin),
):
    return await WebsiteContentService.update_photo(
        db=db,
        photo_id=photo_id,
        payload=payload,
    )


@router.delete(
    "/gallery/photos/{photo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete photo gallery entry",
)
async def delete_gallery_photo(
    photo_id: str,
    db: AsyncSession = Depends(get_database),
    current_admin: User = Depends(get_current_admin),
):
    await WebsiteContentService.delete_photo(db=db, photo_id=photo_id)


# ── Video Gallery Management ──

@router.get(
    "/gallery/videos",
    response_model=List[GalleryVideoResponse],
    summary="List all video gallery entries for admin",
)
async def list_admin_gallery_videos(
    category: Optional[str] = Query(None, description="Filter by category"),
    search: Optional[str] = Query(None, description="Search by title or description"),
    is_published: Optional[bool] = Query(None, description="Filter by publication status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=200),
    db: AsyncSession = Depends(get_database),
    current_admin: User = Depends(get_current_admin),
):
    items, _ = await WebsiteContentService.list_videos(
        db=db,
        category=category,
        search=search,
        is_published=is_published,
        page=page,
        page_size=page_size,
    )
    return items


@router.post(
    "/gallery/videos",
    response_model=GalleryVideoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new video gallery entry",
)
async def create_gallery_video(
    payload: GalleryVideoCreate,
    db: AsyncSession = Depends(get_database),
    current_admin: User = Depends(get_current_admin),
):
    return await WebsiteContentService.create_video(
        db=db,
        payload=payload,
        admin_id=current_admin.id,
    )


@router.get(
    "/gallery/videos/{video_id}",
    response_model=GalleryVideoResponse,
    summary="Get single video gallery entry",
)
async def get_gallery_video(
    video_id: str,
    db: AsyncSession = Depends(get_database),
    current_admin: User = Depends(get_current_admin),
):
    return await WebsiteContentService.get_video(db=db, video_id=video_id)


@router.patch(
    "/gallery/videos/{video_id}",
    response_model=GalleryVideoResponse,
    summary="Update video gallery entry",
)
async def update_gallery_video(
    video_id: str,
    payload: GalleryVideoUpdate,
    db: AsyncSession = Depends(get_database),
    current_admin: User = Depends(get_current_admin),
):
    return await WebsiteContentService.update_video(
        db=db,
        video_id=video_id,
        payload=payload,
    )


@router.delete(
    "/gallery/videos/{video_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete video gallery entry",
)
async def delete_gallery_video(
    video_id: str,
    db: AsyncSession = Depends(get_database),
    current_admin: User = Depends(get_current_admin),
):
    await WebsiteContentService.delete_video(db=db, video_id=video_id)


# ── Press & News Articles Management ──

@router.get(
    "/press",
    response_model=List[PressArticleResponse],
    summary="List all press articles and newspaper clippings for admin",
)
async def list_admin_press_articles(
    category: Optional[str] = Query(None, description="Filter by category"),
    search: Optional[str] = Query(None, description="Search by title, newspaper, or summary"),
    is_published: Optional[bool] = Query(None, description="Filter by publication status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=200),
    db: AsyncSession = Depends(get_database),
    current_admin: User = Depends(get_current_admin),
):
    items, _ = await WebsiteContentService.list_press_articles(
        db=db,
        category=category,
        search=search,
        is_published=is_published,
        page=page,
        page_size=page_size,
    )
    return items


@router.post(
    "/press",
    response_model=PressArticleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new press article / newspaper clipping",
)
async def create_press_article(
    payload: PressArticleCreate,
    db: AsyncSession = Depends(get_database),
    current_admin: User = Depends(get_current_admin),
):
    return await WebsiteContentService.create_press_article(
        db=db,
        payload=payload,
        admin_id=current_admin.id,
    )


@router.get(
    "/press/{press_id}",
    response_model=PressArticleResponse,
    summary="Get single press article / newspaper clipping",
)
async def get_press_article(
    press_id: str,
    db: AsyncSession = Depends(get_database),
    current_admin: User = Depends(get_current_admin),
):
    return await WebsiteContentService.get_press_article(db=db, press_id=press_id)


@router.patch(
    "/press/{press_id}",
    response_model=PressArticleResponse,
    summary="Update press article / newspaper clipping",
)
async def update_press_article(
    press_id: str,
    payload: PressArticleUpdate,
    db: AsyncSession = Depends(get_database),
    current_admin: User = Depends(get_current_admin),
):
    return await WebsiteContentService.update_press_article(
        db=db,
        press_id=press_id,
        payload=payload,
    )


@router.delete(
    "/press/{press_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete press article / newspaper clipping",
)
async def delete_press_article(
    press_id: str,
    db: AsyncSession = Depends(get_database),
    current_admin: User = Depends(get_current_admin),
):
    await WebsiteContentService.delete_press_article(db=db, press_id=press_id)


# ── Section Headers Management ──

@router.get(
    "/sections/{section_id}",
    response_model=Optional[WebsiteSectionHeaderResponse],
    summary="Get section header settings (e.g. gallery, news)",
)
async def get_section_header(
    section_id: str,
    db: AsyncSession = Depends(get_database),
    current_admin: User = Depends(get_current_admin),
):
    return await WebsiteContentService.get_section_header(db=db, section_id=section_id)


@router.put(
    "/sections/{section_id}",
    response_model=WebsiteSectionHeaderResponse,
    summary="Save section header settings (e.g. gallery, news)",
)
async def update_section_header(
    section_id: str,
    payload: WebsiteSectionHeaderUpdate,
    db: AsyncSession = Depends(get_database),
    current_admin: User = Depends(get_current_admin),
):
    admin_name = current_admin.email if current_admin else "Admin"
    return await WebsiteContentService.save_section_header(
        db=db,
        section_id=section_id,
        payload=payload,
        admin_name=admin_name,
    )
