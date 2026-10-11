from datetime import datetime
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field, model_validator, field_validator


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


# ── Jobs Page & Locations Schemas ──

class JobsHeroConfig(BaseModel):
    badge: str = "Corporate Recruitment Portal"
    heading: str = "Find Your Dream Job in Andhra Pradesh & India"
    subtitle: str = "Explore 2,450+ verified corporate job openings with zero placement fees"


class JobsHeroUpdate(BaseModel):
    badge: Optional[str] = None
    heading: Optional[str] = None
    subtitle: Optional[str] = None


class JobsSearchConfig(BaseModel):
    searchPlaceholder: str = "Job title, skills (Python, React...), or company..."
    locationPlaceholder: str = "All Locations (All India)"
    popularSearches: List[str] = Field(default_factory=list)


class JobsSearchUpdate(BaseModel):
    search_placeholder: Optional[str] = None
    location_placeholder: Optional[str] = None
    searchPlaceholder: Optional[str] = None
    locationPlaceholder: Optional[str] = None
    popular_searches: Optional[List[str]] = None
    popularSearches: Optional[List[str]] = None

    @model_validator(mode="before")
    @classmethod
    def reconcile_search_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "searchPlaceholder" in data and not data.get("search_placeholder"):
                data["search_placeholder"] = data["searchPlaceholder"]
            if "locationPlaceholder" in data and not data.get("location_placeholder"):
                data["location_placeholder"] = data["locationPlaceholder"]
            if "popularSearches" in data and data.get("popular_searches") is None:
                data["popular_searches"] = data["popularSearches"]
        return data


class JobsPopularSearchesUpdate(BaseModel):
    popular_searches: Optional[List[str]] = None
    popularSearches: Optional[List[str]] = None

    @model_validator(mode="before")
    @classmethod
    def reconcile_popular_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "popularSearches" in data and data.get("popular_searches") is None:
                data["popular_searches"] = data["popularSearches"]
        return data


class JobLocationResponse(BaseModel):
    id: str
    name: str
    state_ut_type: str = "state"
    display_order: int = 0
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class JobLocationUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None
    display_order: Optional[int] = None
    state_ut_type: Optional[str] = None


class JobLocationItemUpdate(BaseModel):
    id: str
    is_active: bool
    name: Optional[str] = None


class JobLocationsBatchUpdate(BaseModel):
    locations: List[JobLocationItemUpdate]


class JobsPageFullUpdate(BaseModel):
    hero: Optional[JobsHeroUpdate] = None
    search: Optional[JobsSearchUpdate] = None


class JobsPageConfigResponse(BaseModel):
    hero: JobsHeroConfig
    search: JobsSearchConfig
    locations: Optional[List[JobLocationResponse]] = None
    updated_by: Optional[str] = None
    updated_at: Optional[datetime] = None


class PublicJobLocationsResponse(BaseModel):
    states: List[str]
    union_territories: List[str]
    items: List[JobLocationResponse]
    all_locations: List[str]


# ── About Us CMS Content Schemas ──

class AboutUsHeroData(BaseModel):
    badge: str
    heading: str
    description: str


class AboutUsHeroUpdate(BaseModel):
    badge: str = Field(..., min_length=1, max_length=255)
    heading: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)


class PrincipleCardItem(BaseModel):
    id: Optional[str] = None
    icon: Optional[str] = "ShieldCheck"
    title: str = Field(..., min_length=1, max_length=255)
    desc: str = Field(..., min_length=1)
    color: Optional[str] = "primary"


class AboutUsPrinciplesData(BaseModel):
    heading: str
    description: str
    cards: List[PrincipleCardItem] = Field(default_factory=list)


class AboutUsPrinciplesUpdate(BaseModel):
    heading: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)
    cards: List[PrincipleCardItem] = Field(..., min_length=1)


class TeamMemberItem(BaseModel):
    id: Optional[str] = None
    name: str = Field(..., min_length=1, max_length=255)
    role: str = Field(..., min_length=1, max_length=255)
    organization: str = Field(..., min_length=1, max_length=255)
    bio: str = Field(..., min_length=1)
    image: Optional[str] = None


class AboutUsTeamData(BaseModel):
    badge: str
    heading: str
    description: str
    members: List[TeamMemberItem] = Field(default_factory=list)


class AboutUsTeamUpdate(BaseModel):
    badge: str = Field(..., min_length=1, max_length=255)
    heading: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)
    members: List[TeamMemberItem] = Field(default_factory=list)


class LeadershipMessageItem(BaseModel):
    id: Optional[str] = None
    name: str = Field(..., min_length=1, max_length=255)
    designation: Optional[str] = None
    role: Optional[str] = None
    organization: str = Field(..., min_length=1, max_length=255)
    image: Optional[str] = None
    initials: Optional[str] = None
    headerBg: Optional[str] = None
    message: str = Field(..., min_length=1)
    fullMessage: Optional[str] = None
    hasViewAction: Optional[bool] = False

    @model_validator(mode="before")
    @classmethod
    def sync_role_designation(cls, data: Any) -> Any:
        if isinstance(data, dict):
            desig = data.get("designation") or data.get("role") or ""
            data["designation"] = desig
            data["role"] = desig
        return data


class AboutUsLeadershipData(BaseModel):
    badge: str
    heading: str
    description: Optional[str] = ""
    messages: List[LeadershipMessageItem] = Field(default_factory=list)


class AboutUsLeadershipUpdate(BaseModel):
    badge: str = Field(..., min_length=1, max_length=255)
    heading: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = ""
    messages: List[LeadershipMessageItem] = Field(default_factory=list)


class PartnerItem(BaseModel):
    id: Optional[str] = None
    name: str = Field(..., min_length=1, max_length=255)
    logoText: Optional[str] = None
    logo: Optional[str] = None
    active: bool = True
    order: Optional[int] = 1

    @model_validator(mode="before")
    @classmethod
    def sync_logo_text(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if not data.get("logoText"):
                data["logoText"] = data.get("name", "")
        return data


class AboutUsPartnersData(BaseModel):
    heading: str
    description: str
    list: List[PartnerItem] = Field(default_factory=list)


class AboutUsPartnersUpdate(BaseModel):
    heading: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)
    list: List[PartnerItem] = Field(default_factory=list)


class AboutUsFullUpdate(BaseModel):
    hero: Optional[AboutUsHeroUpdate] = None
    stats: Optional[List[Dict[str, Any]]] = None
    whatWeStandFor: Optional[AboutUsPrinciplesUpdate] = None
    team: Optional[AboutUsTeamUpdate] = None
    leadershipMessages: Optional[AboutUsLeadershipUpdate] = None
    partners: Optional[AboutUsPartnersUpdate] = None


class AboutUsConfigResponse(BaseModel):
    hero: AboutUsHeroData
    stats: List[Dict[str, Any]] = Field(default_factory=list)
    whatWeStandFor: AboutUsPrinciplesData
    team: AboutUsTeamData
    leadershipMessages: AboutUsLeadershipData
    partners: AboutUsPartnersData
    updated_by: Optional[str] = None
    updated_at: Optional[datetime] = None


# ── Job Melas Page Schemas ──

class JobMelaHeroUpdate(BaseModel):
    badge: Optional[str] = Field(None, max_length=255)
    heading: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    hero_badge: Optional[str] = Field(None, max_length=255)
    hero_heading: Optional[str] = Field(None, max_length=255)
    hero_description: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def reconcile_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # If payload has nested "hero": { badge, heading, description }
            if "hero" in data and isinstance(data["hero"], dict):
                nested = data["hero"]
                for k in ["badge", "heading", "description", "hero_badge", "hero_heading", "hero_description"]:
                    if k in nested and k not in data:
                        data[k] = nested[k]
            if "hero_badge" in data and not data.get("badge"):
                data["badge"] = data["hero_badge"]
            if "badge" in data and not data.get("hero_badge"):
                data["hero_badge"] = data["badge"]
            if "hero_heading" in data and not data.get("heading"):
                data["heading"] = data["hero_heading"]
            if "heading" in data and not data.get("hero_heading"):
                data["hero_heading"] = data["heading"]
            if "hero_description" in data and not data.get("description"):
                data["description"] = data["hero_description"]
            if "description" in data and not data.get("hero_description"):
                data["hero_description"] = data["description"]
        return data


class JobMelaHeroResponse(BaseModel):
    badge: str
    heading: str
    description: str
    hero_badge: Optional[str] = None
    hero_heading: Optional[str] = None
    hero_description: Optional[str] = None
    hero: Optional[Dict[str, str]] = None
    updated_by: Optional[str] = None
    updated_at: Optional[datetime] = None

    @model_validator(mode="before")
    @classmethod
    def populate_helpers(cls, data: Any) -> Any:
        if isinstance(data, dict):
            badge = data.get("badge") or data.get("hero_badge") or "Nationwide Recruitment Drives"
            heading = data.get("heading") or data.get("hero_heading") or "Mega Job Melas & Career Fairs"
            desc = data.get("description") or data.get("hero_description") or ""
            data["badge"] = badge
            data["heading"] = heading
            data["description"] = desc
            data["hero_badge"] = badge
            data["hero_heading"] = heading
            data["hero_description"] = desc
            data["hero"] = {
                "badge": badge,
                "heading": heading,
                "description": desc,
            }
        return data


# ── Skill Development CMS Schemas ──

class SkillHeroData(BaseModel):
    badge: str = Field(..., min_length=1, max_length=255)
    heading: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)
    exploreBtnText: Optional[str] = "Explore Programs"
    viewCoursesBtnText: Optional[str] = "View Courses"


class SkillHighlightItem(BaseModel):
    id: Optional[str] = None
    icon: Optional[str] = "Award"
    title: str = Field(..., min_length=1, max_length=255)
    subtitle: str = Field(..., min_length=1, max_length=255)


class SkillHighlightsUpdate(BaseModel):
    highlights: List[SkillHighlightItem] = Field(...)

    @model_validator(mode="before")
    @classmethod
    def wrap_raw_list(cls, data: Any) -> Any:
        if isinstance(data, list):
            return {"highlights": data}
        return data

    @field_validator("highlights")
    @classmethod
    def validate_four_highlights(cls, v: List[SkillHighlightItem]) -> List[SkillHighlightItem]:
        if len(v) != 4:
            raise ValueError(f"Highlights must contain exactly 4 items, but got {len(v)}.")
        return v


class SkillPillarItem(BaseModel):
    id: Optional[str] = None
    icon: Optional[str] = "Code2"
    title: str = Field(..., min_length=1, max_length=255)
    desc: str = Field(..., min_length=1)


class SkillMissionUpdate(BaseModel):
    badge: str = Field(..., min_length=1, max_length=255)
    heading: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)
    cards: List[SkillPillarItem] = Field(...)

    @field_validator("cards")
    @classmethod
    def validate_three_pillars(cls, v: List[SkillPillarItem]) -> List[SkillPillarItem]:
        if len(v) != 3:
            raise ValueError(f"Institutional Mission must contain exactly 3 pillars, but got {len(v)}.")
        return v


class SkillPathwayStepItem(BaseModel):
    step: str = Field(..., min_length=1, max_length=20)
    title: str = Field(..., min_length=1, max_length=255)
    desc: str = Field(..., min_length=1)


class SkillPathwayUpdate(BaseModel):
    badge: str = Field(..., min_length=1, max_length=255)
    heading: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)
    steps: List[SkillPathwayStepItem] = Field(...)

    @field_validator("steps")
    @classmethod
    def validate_six_steps(cls, v: List[SkillPathwayStepItem]) -> List[SkillPathwayStepItem]:
        if len(v) != 6:
            raise ValueError(f"Candidate Pathway must contain exactly 6 journey steps, but got {len(v)}.")
        return v


class SkillAdvantageItem(BaseModel):
    icon: Optional[str] = "Award"
    title: str = Field(..., min_length=1, max_length=255)
    desc: str = Field(..., min_length=1)


class SkillAdvantagesUpdate(BaseModel):
    badge: str = Field(..., min_length=1, max_length=255)
    heading: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)
    cards: List[SkillAdvantageItem] = Field(...)

    @field_validator("cards")
    @classmethod
    def validate_six_advantages(cls, v: List[SkillAdvantageItem]) -> List[SkillAdvantageItem]:
        if len(v) != 6:
            raise ValueError(f"Why Choose NTR VIKASA must contain exactly 6 institutional advantage cards, but got {len(v)}.")
        return v


class SkillDomainCategoryItem(BaseModel):
    id: Optional[str] = None
    name: str = Field(..., min_length=1, max_length=255)
    icon: Optional[str] = "Code2"
    desc: str = Field(..., min_length=1)
    count: Optional[str] = "2 Courses"


class SkillProgramsUpdate(BaseModel):
    badge: str = Field(..., min_length=1, max_length=255)
    heading: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)
    categories: List[SkillDomainCategoryItem] = Field(...)

    @field_validator("categories")
    @classmethod
    def validate_eight_programs(cls, v: List[SkillDomainCategoryItem]) -> List[SkillDomainCategoryItem]:
        if len(v) != 8:
            raise ValueError(f"Programs We Offer must contain exactly 8 domain categories, but got {len(v)}.")
        return v


class SkillSectionResponse(BaseModel):
    section_key: str
    title: Optional[str] = None
    content: Any
    updated_by: Optional[str] = None
    updated_at: Optional[datetime] = None


class SkillDevelopmentConfigResponse(BaseModel):
    skills_hero: Dict[str, Any]
    skills_highlights: List[Dict[str, Any]]
    skills_mission: Dict[str, Any]
    skills_pathway: Dict[str, Any]
    skills_advantages: Dict[str, Any]
    skills_programs: Dict[str, Any]
    # Aliases matching frontend structure
    hero: Dict[str, Any]
    highlights: List[Dict[str, Any]]
    empoweringSkills: Dict[str, Any]
    trainingJourney: Dict[str, Any]
    whyChoose: Dict[str, Any]
    programsWeOffer: Dict[str, Any]
    updated_by: Optional[str] = None
    updated_at: Optional[datetime] = None


