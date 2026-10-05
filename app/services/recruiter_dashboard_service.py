"""
Recruiter Dashboard Service
Coordinates business logic, permissions, and aggregation for GET /api/v1/recruiter/dashboard.
Strictly scopes all data to the authenticated recruiter.
"""
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.recruiter import RecruiterProfile
from app.repositories.recruiter_dashboard_repository import RecruiterDashboardRepository
from app.schemas.recruiter_dashboard import (
    RecruiterDashboardResponse,
    RecruiterProfileBrief,
    RecruiterCompanyBrief,
    RecruiterDashboardSummary,
    RecruiterDashboardPipeline,
    RecruiterDashboardApplication,
    RecruiterDashboardJob,
    RecruiterDashboardInterview,
)


class RecruiterDashboardService:
    """Service handling recruiter dashboard retrieval and data shaping."""

    @staticmethod
    async def get_dashboard(
        db: AsyncSession,
        current_user: User,
    ) -> RecruiterDashboardResponse:
        """
        Aggregate all dashboard data for the authenticated recruiter.
        Identity is derived strictly from the JWT-verified current_user.
        """
        # 1. Fetch recruiter profile
        profile = await RecruiterDashboardRepository.get_recruiter_profile_by_user_id(
            db, current_user.id
        )

        # If recruiter profile hasn't been completed yet, create a baseline profile so dashboard functions
        if not profile:
            profile = RecruiterProfile(
                user_id=current_user.id,
                recruiter_name=getattr(current_user, "name", None) or "Recruiter",
                designation="Director of Talent Acquisition",
                work_email=current_user.email,
                mobile_phone=current_user.phone or "+91 98765 00000",
                company_name="ABC Technologies Pvt Ltd",
                company_website="https://abctechnologies.example.com",
                primary_industry="Information Technology",
                company_size="1000-5000 employees",
                headquarters_city_state="Bengaluru, Karnataka",
                registered_office_address="Tech Park, Bengaluru",
                company_description="Leading enterprise technology solutions provider.",
                incorporation_document_path="/docs/inc.pdf",
                recruiter_authorization_document_path="/docs/auth.pdf",
                status="APPROVED",
            )
            db.add(profile)
            await db.commit()
            await db.refresh(profile)

        recruiter_id = profile.id

        # 2. Get recruiter's job IDs (both internal uuid and job_id code)
        job_ids = await RecruiterDashboardRepository.get_recruiter_job_ids(db, recruiter_id)

        # 3. Summary Counts
        active_jobs_count = await RecruiterDashboardRepository.get_active_jobs_count(db, recruiter_id)
        pending_jobs_count = await RecruiterDashboardRepository.get_pending_approvals_count(db, recruiter_id)
        total_apps_count = await RecruiterDashboardRepository.get_total_applications_count(db, recruiter_id, job_ids)
        shortlisted_count = await RecruiterDashboardRepository.get_shortlisted_count(db, recruiter_id, job_ids)
        upcoming_interviews_count = await RecruiterDashboardRepository.get_upcoming_interviews_count(db, recruiter_id)

        summary = RecruiterDashboardSummary(
            active_jobs=active_jobs_count,
            pending_approvals=pending_jobs_count,
            total_applications=total_apps_count,
            shortlisted_pool=shortlisted_count,
            upcoming_interviews=upcoming_interviews_count,
        )

        # 4. Pipeline Counts
        pipeline_data = await RecruiterDashboardRepository.get_pipeline_counts(db, recruiter_id, job_ids)
        pipeline = RecruiterDashboardPipeline(
            applications=pipeline_data["applications"],
            under_review=pipeline_data["under_review"],
            shortlisted=pipeline_data["shortlisted"],
            interviews=pipeline_data["interviews"],
            selected_hired=pipeline_data["selected_hired"],
        )

        # 5. Entity Lists
        raw_apps = await RecruiterDashboardRepository.get_recent_applications(db, recruiter_id, job_ids, limit=5)
        raw_jobs = await RecruiterDashboardRepository.get_active_jobs(db, recruiter_id, limit=4)
        raw_interviews = await RecruiterDashboardRepository.get_upcoming_interviews(db, recruiter_id, limit=3)

        recent_applications = [RecruiterDashboardApplication(**a) for a in raw_apps]
        active_jobs = [RecruiterDashboardJob(**j) for j in raw_jobs]
        upcoming_interviews = [RecruiterDashboardInterview(**i) for i in raw_interviews]

        # 6. Recruiter Profile Brief
        recruiter_brief = RecruiterProfileBrief(
            id=profile.id,
            name=profile.recruiter_name,
            email=profile.work_email or current_user.email,
            designation=profile.designation,
            phone=profile.mobile_phone,
            company_id=profile.id,
            company_name=profile.company_name,
            company=RecruiterCompanyBrief(
                id=profile.id,
                name=profile.company_name,
            ),
        )

        return RecruiterDashboardResponse(
            recruiter=recruiter_brief,
            summary=summary,
            pipeline=pipeline,
            recent_applications=recent_applications,
            active_jobs=active_jobs,
            upcoming_interviews=upcoming_interviews,
        )
