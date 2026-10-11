from typing import Any
from fastapi import APIRouter, Depends, Body, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_database, get_current_admin
from app.models.user import User
from app.schemas.website_content import (
    SkillSectionResponse,
    SkillDevelopmentConfigResponse,
)
from app.services.website_content_service import WebsiteContentService


# ══════════════════════════════════════════════════════════════════════════════
# 1. PUBLIC CMS ROUTERS (Read-Only)
# ══════════════════════════════════════════════════════════════════════════════
public_router = APIRouter(
    prefix="/cms/skills",
    tags=["Public Skill Development CMS"],
)

public_wc_router = APIRouter(
    prefix="/public/website-content/skills",
    tags=["Public Skill Development CMS"],
)


@public_router.get(
    "",
    response_model=SkillDevelopmentConfigResponse,
    status_code=status.HTTP_200_OK,
    summary="Public read-only all 6 Skill Development sections",
    description="Retrieve all six Skill Development sections in a single response for public landing page.",
)
@public_wc_router.get(
    "",
    response_model=SkillDevelopmentConfigResponse,
    status_code=status.HTTP_200_OK,
    summary="Public read-only all 6 Skill Development sections (alias)",
)
async def get_public_skill_content(
    db: AsyncSession = Depends(get_database),
) -> SkillDevelopmentConfigResponse:
    """GET /api/v1/cms/skills"""
    return await WebsiteContentService.get_skill_development_config(db=db)


@public_router.get(
    "/{section_key}",
    response_model=SkillSectionResponse,
    status_code=status.HTTP_200_OK,
    summary="Public read-only individual Skill Development section",
    description="Retrieve an individual section (e.g. skills_hero, skills_highlights, skills_mission, skills_pathway, skills_advantages, skills_programs).",
)
@public_wc_router.get(
    "/{section_key}",
    response_model=SkillSectionResponse,
    status_code=status.HTTP_200_OK,
    summary="Public read-only individual Skill Development section (alias)",
)
async def get_public_skill_section(
    section_key: str,
    db: AsyncSession = Depends(get_database),
) -> SkillSectionResponse:
    """GET /api/v1/cms/skills/{section_key}"""
    return await WebsiteContentService.get_skill_section(db=db, section_key=section_key)


# ══════════════════════════════════════════════════════════════════════════════
# 2. ADMIN CMS ROUTERS (Authenticated Administration)
# ══════════════════════════════════════════════════════════════════════════════
admin_router = APIRouter(
    prefix="/admin/cms/skills",
    tags=["Admin Skill Development CMS"],
)

admin_wc_router = APIRouter(
    prefix="/admin/website-content/skills",
    tags=["Admin Skill Development CMS"],
)


@admin_router.get(
    "",
    response_model=SkillDevelopmentConfigResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin retrieve all 6 Skill Development sections",
    description="Retrieve all six Skill Development sections with administrative metadata.",
)
@admin_wc_router.get(
    "",
    response_model=SkillDevelopmentConfigResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin retrieve all 6 Skill Development sections (alias)",
)
async def get_admin_skill_content(
    db: AsyncSession = Depends(get_database),
    current_admin: User = Depends(get_current_admin),
) -> SkillDevelopmentConfigResponse:
    """GET /api/v1/admin/cms/skills"""
    return await WebsiteContentService.get_skill_development_config(db=db)


@admin_router.get(
    "/{section_key}",
    response_model=SkillSectionResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin retrieve individual Skill Development section",
)
@admin_wc_router.get(
    "/{section_key}",
    response_model=SkillSectionResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin retrieve individual Skill Development section (alias)",
)
async def get_admin_skill_section(
    section_key: str,
    db: AsyncSession = Depends(get_database),
    current_admin: User = Depends(get_current_admin),
) -> SkillSectionResponse:
    """GET /api/v1/admin/cms/skills/{section_key}"""
    return await WebsiteContentService.get_skill_section(db=db, section_key=section_key)


@admin_router.put(
    "/{section_key}",
    response_model=SkillSectionResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin update individual Skill Development section (PUT)",
)
@admin_router.patch(
    "/{section_key}",
    response_model=SkillSectionResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin update individual Skill Development section (PATCH)",
)
@admin_wc_router.put(
    "/{section_key}",
    response_model=SkillSectionResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin update individual Skill Development section (PUT alias)",
)
@admin_wc_router.patch(
    "/{section_key}",
    response_model=SkillSectionResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin update individual Skill Development section (PATCH alias)",
)
async def update_admin_skill_section(
    section_key: str,
    payload: Any = Body(...),
    db: AsyncSession = Depends(get_database),
    current_admin: User = Depends(get_current_admin),
) -> SkillSectionResponse:
    """PUT /api/v1/admin/cms/skills/{section_key}"""
    admin_name = current_admin.name if current_admin and hasattr(current_admin, "name") and current_admin.name else (current_admin.email if current_admin else "Admin")
    return await WebsiteContentService.update_skill_section(
        db=db,
        section_key=section_key,
        payload_data=payload,
        admin_name=admin_name,
    )


@admin_router.post(
    "/{section_key}/reset",
    response_model=SkillSectionResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin reset individual Skill Development section to default values",
)
@admin_wc_router.post(
    "/{section_key}/reset",
    response_model=SkillSectionResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin reset individual Skill Development section to default values (alias)",
)
async def reset_admin_skill_section(
    section_key: str,
    db: AsyncSession = Depends(get_database),
    current_admin: User = Depends(get_current_admin),
) -> SkillSectionResponse:
    """POST /api/v1/admin/cms/skills/{section_key}/reset"""
    admin_name = current_admin.name if current_admin and hasattr(current_admin, "name") and current_admin.name else (current_admin.email if current_admin else "Admin")
    return await WebsiteContentService.reset_skill_section(
        db=db,
        section_key=section_key,
        admin_name=admin_name,
    )


@admin_router.post(
    "/reset",
    response_model=SkillDevelopmentConfigResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin reset all Skill Development sections to defaults",
)
@admin_wc_router.post(
    "/reset",
    response_model=SkillDevelopmentConfigResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin reset all Skill Development sections to defaults (alias)",
)
async def reset_admin_all_skill_sections(
    db: AsyncSession = Depends(get_database),
    current_admin: User = Depends(get_current_admin),
) -> SkillDevelopmentConfigResponse:
    """POST /api/v1/admin/cms/skills/reset"""
    admin_name = current_admin.name if current_admin and hasattr(current_admin, "name") and current_admin.name else (current_admin.email if current_admin else "Admin")
    return await WebsiteContentService.reset_all_skill_sections(
        db=db,
        admin_name=admin_name,
    )
