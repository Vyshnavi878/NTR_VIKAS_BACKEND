from fastapi import APIRouter
from app.api.v1.endpoints import (
    auth,
    candidate_dashboard,
    candidate_profile,
    saved_jobs,
    candidate_applications,
    candidate_support,
    candidate_settings,
    notifications,
    candidate_job_melas,
    candidate_interviews,
    recruiter_dashboard,
    recruiter_support,
    recruiter_analytics,
    recruiter_job_melas,
    admin_job_melas,
    job_melas,
    recruiter_internships,
    admin_internships,
    internships,
    recruiter_jobs,
    admin_jobs,
    jobs,
    recruiter_interviews,
    recruiter_applications,
    recruiter_company,
    recruiter_settings,
    companies,
    admin_companies,
    admin_recruiters,
    admin_candidates,
    admin_profile,
    admin_settings,
    admin_audit_logs,
    admin_analytics,
    reports,
    admin_reports,
    admin_dashboard,
    admin_website_content,
    public_website_content,
    skills_cms,
)


api_router = APIRouter()


# Authentication & Registration
api_router.include_router(auth.router)

# Candidate Dashboard
api_router.include_router(candidate_dashboard.router)

# Candidate Profile
api_router.include_router(candidate_profile.router)

# Candidate Saved Jobs
api_router.include_router(saved_jobs.router)

# Candidate Applications
api_router.include_router(candidate_applications.router)

# Candidate Help & Support Tickets
api_router.include_router(candidate_support.router)

# Candidate Settings & Privacy
api_router.include_router(candidate_settings.router)

# Candidate Notifications
api_router.include_router(notifications.router)

# Candidate Job Melas & Registrations
api_router.include_router(candidate_job_melas.router)

# Candidate Interviews & Schedule
api_router.include_router(candidate_interviews.router)

# Recruiter Dashboard
api_router.include_router(recruiter_dashboard.router)

# Recruiter Help & Support
api_router.include_router(recruiter_support.router)

# Recruiter Hiring Analytics
api_router.include_router(recruiter_analytics.router)

# Recruiter Job Melas Participation
api_router.include_router(recruiter_job_melas.router)

# Admin Job Melas Participation Reviews
api_router.include_router(admin_job_melas.router)
api_router.include_router(admin_job_melas.admin_mela_approvals_router)
api_router.include_router(admin_job_melas.admin_mela_requests_router)

# Public & Candidate Job Melas
api_router.include_router(job_melas.router)
api_router.include_router(job_melas.router, prefix="/public")

# Recruiter Internships (/recruiters/internships and /recruiter/internships)
api_router.include_router(recruiter_internships.router)
api_router.include_router(recruiter_internships.recruiter_singular_router)

# Admin Internships Governance
api_router.include_router(admin_internships.router)
api_router.include_router(admin_internships.admin_internship_approvals_router)

# Public & Candidate Internships
api_router.include_router(internships.router)
api_router.include_router(internships.router, prefix="/public")

# Recruiter Jobs (/recruiters/jobs and /recruiter/jobs)
api_router.include_router(recruiter_jobs.router)
api_router.include_router(recruiter_jobs.recruiter_singular_router)

# Admin Jobs Governance
api_router.include_router(admin_jobs.router)
api_router.include_router(admin_jobs.admin_job_approvals_router)

# Public & Candidate Jobs
api_router.include_router(jobs.router)
api_router.include_router(jobs.router, prefix="/public")

# Public & Candidate Companies
api_router.include_router(companies.router)
api_router.include_router(companies.public_alias_router)

# Admin Companies Governance & Verification
api_router.include_router(admin_companies.router)
api_router.include_router(admin_companies.verification_alias_router)
api_router.include_router(admin_companies.singular_verification_alias_router)

# Admin Recruiters Governance & Management
api_router.include_router(admin_recruiters.router)
api_router.include_router(admin_recruiters.alias_router)

# Admin Candidates Governance & Management
api_router.include_router(admin_candidates.router)

# Recruiter Interviews (/recruiter/interviews and /recruiters/interviews)
api_router.include_router(recruiter_interviews.router)
api_router.include_router(recruiter_interviews.recruiters_plural_router)

# Recruiter Applications (/recruiter/applications and /recruiters/applications)
api_router.include_router(recruiter_applications.router)
api_router.include_router(recruiter_applications.recruiters_plural_router)

# Recruiter Company Profile
api_router.include_router(recruiter_company.router)

# Recruiter Settings & Preferences (/recruiter/settings)
api_router.include_router(recruiter_settings.router)

# Admin Profile & Identity (/admin/profile)
api_router.include_router(admin_profile.router)

# Admin Platform Settings (/admin/settings)
api_router.include_router(admin_settings.router)

# Admin Audit Logs (/admin/audit-logs)
api_router.include_router(admin_audit_logs.router)

# Admin Platform Analytics (/admin/analytics)
api_router.include_router(admin_analytics.router)

# User Grievance & Reports Submission (/reports)
api_router.include_router(reports.router)

# Admin Reports & Complaints Moderation (/admin/reports)
api_router.include_router(admin_reports.router)

# Admin Command Center Dashboard (/admin/dashboard)
api_router.include_router(admin_dashboard.router)

# Admin Website Content Management (/admin/website-content)
api_router.include_router(admin_website_content.router)

# Public Website Content (/public/website-content)
api_router.include_router(public_website_content.router)

# Skill Development Website Content Management (/cms/skills and /admin/cms/skills)
api_router.include_router(skills_cms.public_router)
api_router.include_router(skills_cms.public_wc_router)
api_router.include_router(skills_cms.admin_router)
api_router.include_router(skills_cms.admin_wc_router)

# Direct alias for /public/news-press as specified in system integration requirements
from typing import Optional, List
from fastapi import Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_database
from app.schemas.website_content import (
    PressArticleResponse,
    JobsPageConfigResponse,
    PublicJobLocationsResponse,
    AboutUsConfigResponse,
    JobMelaHeroResponse,
)
from app.services.website_content_service import WebsiteContentService

@api_router.get(
    "/public/news-press",
    response_model=List[PressArticleResponse],
    tags=["Public Website Content"],
    summary="Direct public press clippings endpoint",
)
async def get_direct_public_news_press(
    category: Optional[str] = Query(None, description="Filter by category"),
    search: Optional[str] = Query(None, description="Search by title or summary"),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=200),
    db: AsyncSession = Depends(get_database),
):
    items, _ = await WebsiteContentService.list_press_articles(
        db=db,
        category=category,
        search=search,
        is_published=True,
        page=page,
        page_size=page_size,
    )
    return items


@api_router.get(
    "/public/job-locations",
    response_model=PublicJobLocationsResponse,
    tags=["Public Website Content"],
    summary="Direct public active job filter locations endpoint",
)
async def get_direct_public_job_locations(
    db: AsyncSession = Depends(get_database),
):
    return await WebsiteContentService.get_public_job_locations(db)


@api_router.get(
    "/public/jobs-page",
    response_model=JobsPageConfigResponse,
    tags=["Public Website Content"],
    summary="Direct public Jobs page configuration endpoint",
)
async def get_direct_public_jobs_page(
    db: AsyncSession = Depends(get_database),
):
    return await WebsiteContentService.get_jobs_page_config(db, include_all_locations=False)


@api_router.get(
    "/public/about-us",
    response_model=AboutUsConfigResponse,
    tags=["Public Website Content"],
    summary="Direct public About Us configuration endpoint",
)
async def get_direct_public_about_us(
    db: AsyncSession = Depends(get_database),
):
    return await WebsiteContentService.get_about_us_config(db=db, is_public=True)


@api_router.get(
    "/public/job-melas/hero",
    response_model=JobMelaHeroResponse,
    tags=["Public Website Content"],
    summary="Direct public Job Melas hero configuration endpoint",
)
async def get_direct_public_job_melas_hero(
    db: AsyncSession = Depends(get_database),
):
    return await WebsiteContentService.get_job_mela_hero(db=db)








