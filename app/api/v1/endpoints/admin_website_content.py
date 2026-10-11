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
    JobsHeroUpdate,
    JobsSearchUpdate,
    JobsPopularSearchesUpdate,
    JobsPageFullUpdate,
    JobsPageConfigResponse,
    JobLocationResponse,
    JobLocationUpdate,
    JobLocationsBatchUpdate,
    AboutUsHeroUpdate,
    AboutUsPrinciplesUpdate,
    AboutUsTeamUpdate,
    AboutUsLeadershipUpdate,
    AboutUsPartnersUpdate,
    AboutUsFullUpdate,
    AboutUsConfigResponse,
    AboutUsTeamData,
    AboutUsLeadershipData,
    AboutUsPartnersData,
    JobMelaHeroUpdate,
    JobMelaHeroResponse,
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
@router.get(
    "/news-press",
    response_model=List[PressArticleResponse],
    summary="List all press articles and newspaper clippings for admin (alias)",
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
@router.post(
    "/news-press",
    response_model=PressArticleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new press article / newspaper clipping (alias)",
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


# ── Section Headers Management (Static routes before parameterized routes) ──

@router.get(
    "/news-press/settings",
    response_model=Optional[WebsiteSectionHeaderResponse],
    summary="Get News & Press section header settings",
)
async def get_news_press_settings(
    db: AsyncSession = Depends(get_database),
    current_admin: User = Depends(get_current_admin),
):
    return await WebsiteContentService.get_section_header(db=db, section_id="news")


@router.patch(
    "/news-press/settings",
    response_model=WebsiteSectionHeaderResponse,
    summary="Update News & Press section header settings (PATCH)",
)
@router.put(
    "/news-press/settings",
    response_model=WebsiteSectionHeaderResponse,
    summary="Update News & Press section header settings (PUT)",
)
async def update_news_press_settings(
    payload: WebsiteSectionHeaderUpdate,
    db: AsyncSession = Depends(get_database),
    current_admin: User = Depends(get_current_admin),
):
    admin_name = current_admin.email if current_admin else "Admin"
    return await WebsiteContentService.save_section_header(
        db=db,
        section_id="news",
        payload=payload,
        admin_name=admin_name,
    )


@router.get(
    "/press/{press_id}",
    response_model=PressArticleResponse,
    summary="Get single press article / newspaper clipping",
)
@router.get(
    "/news-press/{press_id}",
    response_model=PressArticleResponse,
    summary="Get single press article / newspaper clipping (alias)",
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
@router.patch(
    "/news-press/{press_id}",
    response_model=PressArticleResponse,
    summary="Update press article / newspaper clipping (alias)",
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
@router.delete(
    "/news-press/{press_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete press article / newspaper clipping (alias)",
)
async def delete_press_article(
    press_id: str,
    db: AsyncSession = Depends(get_database),
    current_admin: User = Depends(get_current_admin),
):
    await WebsiteContentService.delete_press_article(db=db, press_id=press_id)



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
@router.patch(
    "/sections/{section_id}",
    response_model=WebsiteSectionHeaderResponse,
    summary="Update section header settings (e.g. gallery, news)",
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


# ── Jobs Page Content Management ──

@router.get(
    "/jobs-page",
    response_model=JobsPageConfigResponse,
    summary="Get complete Jobs page configuration for admin",
)
async def get_jobs_page_config(
    db: AsyncSession = Depends(get_database),
    current_admin: User = Depends(get_current_admin),
):
    return await WebsiteContentService.get_jobs_page_config(db, include_all_locations=True)


@router.patch(
    "/jobs-page",
    response_model=JobsPageConfigResponse,
    summary="Update complete or partial Jobs page configuration",
)
@router.put(
    "/jobs-page",
    response_model=JobsPageConfigResponse,
    summary="Update complete or partial Jobs page configuration (PUT)",
)
async def update_jobs_page_config(
    payload: JobsPageFullUpdate,
    db: AsyncSession = Depends(get_database),
    current_admin: User = Depends(get_current_admin),
):
    admin_name = current_admin.email if current_admin else "Admin"
    return await WebsiteContentService.update_jobs_page_full(
        db=db, payload=payload, admin_name=admin_name
    )


@router.patch(
    "/jobs-page/hero",
    response_model=JobsPageConfigResponse,
    summary="Update Jobs page hero section content",
)
@router.put(
    "/jobs-page/hero",
    response_model=JobsPageConfigResponse,
    summary="Update Jobs page hero section content (PUT)",
)
async def update_jobs_hero(
    payload: JobsHeroUpdate,
    db: AsyncSession = Depends(get_database),
    current_admin: User = Depends(get_current_admin),
):
    admin_name = current_admin.email if current_admin else "Admin"
    return await WebsiteContentService.update_jobs_hero(
        db=db, payload=payload, admin_name=admin_name
    )


@router.patch(
    "/jobs-page/search",
    response_model=JobsPageConfigResponse,
    summary="Update Jobs page search placeholders and popular keywords",
)
@router.put(
    "/jobs-page/search",
    response_model=JobsPageConfigResponse,
    summary="Update Jobs page search placeholders and popular keywords (PUT)",
)
async def update_jobs_search(
    payload: JobsSearchUpdate,
    db: AsyncSession = Depends(get_database),
    current_admin: User = Depends(get_current_admin),
):
    admin_name = current_admin.email if current_admin else "Admin"
    return await WebsiteContentService.update_jobs_search(
        db=db, payload=payload, admin_name=admin_name
    )


@router.patch(
    "/jobs-page/popular-searches",
    response_model=JobsPageConfigResponse,
    summary="Update Jobs page popular search keyword chips",
)
@router.put(
    "/jobs-page/popular-searches",
    response_model=JobsPageConfigResponse,
    summary="Update Jobs page popular search keyword chips (PUT)",
)
async def update_jobs_popular_searches(
    payload: JobsPopularSearchesUpdate,
    db: AsyncSession = Depends(get_database),
    current_admin: User = Depends(get_current_admin),
):
    admin_name = current_admin.email if current_admin else "Admin"
    return await WebsiteContentService.update_jobs_popular_searches(
        db=db, payload=payload, admin_name=admin_name
    )


@router.post(
    "/jobs-page/reset",
    response_model=JobsPageConfigResponse,
    summary="Reset Jobs page configuration to system defaults",
)
async def reset_jobs_page_config(
    db: AsyncSession = Depends(get_database),
    current_admin: User = Depends(get_current_admin),
):
    admin_name = current_admin.email if current_admin else "Admin"
    return await WebsiteContentService.reset_jobs_page_config(db=db, admin_name=admin_name)


# ── Job Locations Management ──

@router.get(
    "/jobs-page/locations",
    response_model=List[JobLocationResponse],
    summary="Get all supported Indian states & UTs for location filter",
)
@router.get(
    "/job-locations",
    response_model=List[JobLocationResponse],
    summary="Get all supported Indian states & UTs (alias)",
)
async def get_admin_job_locations(
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: AsyncSession = Depends(get_database),
    current_admin: User = Depends(get_current_admin),
):
    return await WebsiteContentService.get_all_job_locations(db=db, is_active=is_active)


@router.patch(
    "/jobs-page/locations/{location_id}",
    response_model=JobLocationResponse,
    summary="Update single job location state/active status",
)
@router.put(
    "/jobs-page/locations/{location_id}",
    response_model=JobLocationResponse,
    summary="Update single job location state/active status (PUT)",
)
async def update_admin_job_location(
    location_id: str,
    payload: JobLocationUpdate,
    db: AsyncSession = Depends(get_database),
    current_admin: User = Depends(get_current_admin),
):
    return await WebsiteContentService.update_job_location(
        db=db, location_id=location_id, payload=payload
    )


@router.put(
    "/jobs-page/locations",
    response_model=List[JobLocationResponse],
    summary="Batch update active status of job locations",
)
@router.patch(
    "/jobs-page/locations",
    response_model=List[JobLocationResponse],
    summary="Batch update active status of job locations (PATCH)",
)
async def batch_update_admin_job_locations(
    payload: JobLocationsBatchUpdate,
    db: AsyncSession = Depends(get_database),
    current_admin: User = Depends(get_current_admin),
):
    return await WebsiteContentService.batch_update_job_locations(db=db, payload=payload)


@router.post(
    "/jobs-page/locations/reset",
    response_model=List[JobLocationResponse],
    summary="Reset all job locations to active default state",
)
async def reset_admin_job_locations(
    db: AsyncSession = Depends(get_database),
    current_admin: User = Depends(get_current_admin),
):
    return await WebsiteContentService.reset_job_locations(db=db)


# ── About Us Content Management Endpoints ──

@router.get(
    "/about-us",
    response_model=AboutUsConfigResponse,
    summary="Retrieve all About Us content for the admin editor",
)
async def get_admin_about_us(
    db: AsyncSession = Depends(get_database),
    current_admin: User = Depends(get_current_admin),
):
    return await WebsiteContentService.get_about_us_config(db=db, is_public=False)


@router.patch(
    "/about-us",
    response_model=AboutUsConfigResponse,
    summary="Update full or partial About Us content",
)
@router.put(
    "/about-us",
    response_model=AboutUsConfigResponse,
    summary="Update full or partial About Us content (PUT)",
)
async def update_admin_about_us_full(
    payload: AboutUsFullUpdate,
    db: AsyncSession = Depends(get_database),
    current_admin: User = Depends(get_current_admin),
):
    admin_name = current_admin.name if current_admin and hasattr(current_admin, "name") and current_admin.name else (current_admin.email if current_admin else "Admin")
    return await WebsiteContentService.update_about_us_full(
        db=db, payload=payload, admin_name=admin_name
    )


@router.patch(
    "/about-us/hero",
    response_model=AboutUsConfigResponse,
    summary="Update hero and mission content",
)
@router.put(
    "/about-us/hero",
    response_model=AboutUsConfigResponse,
    summary="Update hero and mission content (PUT)",
)
async def update_admin_about_us_hero(
    payload: AboutUsHeroUpdate,
    db: AsyncSession = Depends(get_database),
    current_admin: User = Depends(get_current_admin),
):
    admin_name = current_admin.name if current_admin and hasattr(current_admin, "name") and current_admin.name else (current_admin.email if current_admin else "Admin")
    return await WebsiteContentService.update_about_us_hero(
        db=db, payload=payload, admin_name=admin_name
    )


@router.patch(
    "/about-us/principles",
    response_model=AboutUsConfigResponse,
    summary="Update What We Stand For (3 Core Principles)",
)
@router.put(
    "/about-us/principles",
    response_model=AboutUsConfigResponse,
    summary="Update What We Stand For (3 Core Principles) (PUT)",
)
@router.patch(
    "/about-us/what-we-stand-for",
    response_model=AboutUsConfigResponse,
    summary="Update What We Stand For (alias)",
)
@router.put(
    "/about-us/what-we-stand-for",
    response_model=AboutUsConfigResponse,
    summary="Update What We Stand For (alias PUT)",
)
async def update_admin_about_us_principles(
    payload: AboutUsPrinciplesUpdate,
    db: AsyncSession = Depends(get_database),
    current_admin: User = Depends(get_current_admin),
):
    admin_name = current_admin.name if current_admin and hasattr(current_admin, "name") and current_admin.name else (current_admin.email if current_admin else "Admin")
    return await WebsiteContentService.update_about_us_principles(
        db=db, payload=payload, admin_name=admin_name
    )


@router.get(
    "/about-us/team",
    response_model=AboutUsTeamData,
    summary="Retrieve team members section and member records",
)
async def get_admin_about_us_team(
    db: AsyncSession = Depends(get_database),
    current_admin: User = Depends(get_current_admin),
):
    config = await WebsiteContentService.get_about_us_config(db=db, is_public=False)
    return config.team


@router.put(
    "/about-us/team",
    response_model=AboutUsConfigResponse,
    summary="Save team section and its ordered member list",
)
@router.patch(
    "/about-us/team",
    response_model=AboutUsConfigResponse,
    summary="Save team section and its ordered member list (PATCH)",
)
async def update_admin_about_us_team(
    payload: AboutUsTeamUpdate,
    db: AsyncSession = Depends(get_database),
    current_admin: User = Depends(get_current_admin),
):
    admin_name = current_admin.name if current_admin and hasattr(current_admin, "name") and current_admin.name else (current_admin.email if current_admin else "Admin")
    return await WebsiteContentService.update_about_us_team(
        db=db, payload=payload, admin_name=admin_name
    )


@router.get(
    "/about-us/leadership",
    response_model=AboutUsLeadershipData,
    summary="Retrieve leadership messages section and statements",
)
async def get_admin_about_us_leadership(
    db: AsyncSession = Depends(get_database),
    current_admin: User = Depends(get_current_admin),
):
    config = await WebsiteContentService.get_about_us_config(db=db, is_public=False)
    return config.leadershipMessages


@router.put(
    "/about-us/leadership",
    response_model=AboutUsConfigResponse,
    summary="Save leadership statements and messages",
)
@router.patch(
    "/about-us/leadership",
    response_model=AboutUsConfigResponse,
    summary="Save leadership statements and messages (PATCH)",
)
async def update_admin_about_us_leadership(
    payload: AboutUsLeadershipUpdate,
    db: AsyncSession = Depends(get_database),
    current_admin: User = Depends(get_current_admin),
):
    admin_name = current_admin.name if current_admin and hasattr(current_admin, "name") and current_admin.name else (current_admin.email if current_admin else "Admin")
    return await WebsiteContentService.update_about_us_leadership(
        db=db, payload=payload, admin_name=admin_name
    )


@router.get(
    "/about-us/partners",
    response_model=AboutUsPartnersData,
    summary="Retrieve training partners list and visibility settings",
)
async def get_admin_about_us_partners(
    db: AsyncSession = Depends(get_database),
    current_admin: User = Depends(get_current_admin),
):
    config = await WebsiteContentService.get_about_us_config(db=db, is_public=False)
    return config.partners


@router.put(
    "/about-us/partners",
    response_model=AboutUsConfigResponse,
    summary="Save partner records and visibility settings",
)
@router.patch(
    "/about-us/partners",
    response_model=AboutUsConfigResponse,
    summary="Save partner records and visibility settings (PATCH)",
)
async def update_admin_about_us_partners(
    payload: AboutUsPartnersUpdate,
    db: AsyncSession = Depends(get_database),
    current_admin: User = Depends(get_current_admin),
):
    admin_name = current_admin.name if current_admin and hasattr(current_admin, "name") and current_admin.name else (current_admin.email if current_admin else "Admin")
    return await WebsiteContentService.update_about_us_partners(
        db=db, payload=payload, admin_name=admin_name
    )


@router.post(
    "/about-us/reset-defaults",
    response_model=AboutUsConfigResponse,
    summary="Reset About Us content to approved defaults",
)
@router.post(
    "/about-us/reset",
    response_model=AboutUsConfigResponse,
    summary="Reset About Us content to approved defaults (alias)",
)
async def reset_admin_about_us_config(
    db: AsyncSession = Depends(get_database),
    current_admin: User = Depends(get_current_admin),
):
    admin_name = current_admin.name if current_admin and hasattr(current_admin, "name") and current_admin.name else (current_admin.email if current_admin else "Admin")
    return await WebsiteContentService.reset_about_us_config(db=db, admin_name=admin_name)


# ── Job Melas Website Content Management ──

@router.get(
    "/job-melas/hero",
    response_model=JobMelaHeroResponse,
    summary="Retrieve current Job Melas public page hero content for admin",
)
@router.get(
    "/job-melas",
    response_model=JobMelaHeroResponse,
    summary="Retrieve current Job Melas public page hero content for admin (alias)",
)
async def get_admin_job_mela_hero(
    db: AsyncSession = Depends(get_database),
    current_admin: User = Depends(get_current_admin),
):
    """Fetch current saved hero configuration for Job Melas page."""
    return await WebsiteContentService.get_job_mela_hero(db=db)


@router.patch(
    "/job-melas/hero",
    response_model=JobMelaHeroResponse,
    summary="Update Job Melas public page hero content (PATCH)",
)
@router.put(
    "/job-melas/hero",
    response_model=JobMelaHeroResponse,
    summary="Update Job Melas public page hero content (PUT)",
)
@router.patch(
    "/job-melas",
    response_model=JobMelaHeroResponse,
    summary="Update Job Melas public page hero content (alias)",
)
async def update_admin_job_mela_hero(
    payload: JobMelaHeroUpdate,
    db: AsyncSession = Depends(get_database),
    current_admin: User = Depends(get_current_admin),
):
    """Save changes to Job Melas hero badge, heading, and description."""
    admin_name = current_admin.name if current_admin and hasattr(current_admin, "name") and current_admin.name else (current_admin.email if current_admin else "Admin")
    return await WebsiteContentService.update_job_mela_hero(
        db=db, payload=payload, admin_name=admin_name
    )


@router.post(
    "/job-melas/hero/reset-defaults",
    response_model=JobMelaHeroResponse,
    summary="Reset Job Melas hero content to approved defaults",
)
@router.post(
    "/job-melas/reset",
    response_model=JobMelaHeroResponse,
    summary="Reset Job Melas hero content to approved defaults (alias)",
)
async def reset_admin_job_mela_hero(
    db: AsyncSession = Depends(get_database),
    current_admin: User = Depends(get_current_admin),
):
    """Reset Job Melas public hero fields to default values."""
    admin_name = current_admin.name if current_admin and hasattr(current_admin, "name") and current_admin.name else (current_admin.email if current_admin else "Admin")
    return await WebsiteContentService.reset_job_mela_hero(
        db=db, admin_name=admin_name
    )

