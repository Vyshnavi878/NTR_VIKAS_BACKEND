import uuid
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.candidate import CandidateProfile
from app.models.application import CandidateApplication, ApplicationTimelineEvent
from app.repositories.candidate_application_repository import CandidateApplicationRepository
from app.repositories.candidate_dashboard_repository import CandidateDashboardRepository
from app.schemas.candidate_application import (
    CandidateBrief,
    StatusCounts,
    TimelineEventItem,
    CandidateApplicationItem,
    CandidateApplicationsListResponse,
    ApplicationTimelineResponse,
    CandidateApplicationCreate,
)


def _serialize_application(app: CandidateApplication) -> CandidateApplicationItem:
    """Helper to convert CandidateApplication ORM model to Pydantic schema."""
    applied_at_str = (
        app.applied_at.strftime("%Y-%m-%d")
        if app.applied_at
        else datetime.now(timezone.utc).strftime("%Y-%m-%d")
    )
    applied_date_str = app.applied_date or applied_at_str

    # Build timeline events list
    timeline_items = [
        TimelineEventItem(
            status=event.status,
            stage=event.stage,
            label=event.label or event.stage,
            date=event.date or applied_date_str,
            timestamp=event.created_at.isoformat() if event.created_at else None,
            completed=event.completed,
            current=event.current,
            step_order=event.step_order,
        )
        for event in sorted(app.timeline_events, key=lambda e: e.step_order)
    ]

    # If no custom events stored yet, generate standard 5-step timeline based on current status
    if not timeline_items:
        current_status = app.status.upper()
        timeline_items = [
            TimelineEventItem(
                status="APPLIED",
                stage="Applied",
                label="Application Submitted",
                date=applied_date_str,
                completed=True,
                current=current_status == "APPLIED",
                step_order=1,
            ),
            TimelineEventItem(
                status="SCREENING",
                stage="Screening",
                label="Application Under Screening",
                date="In Progress" if current_status != "APPLIED" else "Pending Review",
                completed=current_status in ("SCREENING", "SHORTLISTED", "INTERVIEW", "SELECTED"),
                current=current_status == "SCREENING",
                step_order=2,
            ),
            TimelineEventItem(
                status="SHORTLISTED",
                stage="Shortlisted",
                label="Application Shortlisted",
                date="Pending Review" if current_status not in ("SHORTLISTED", "INTERVIEW", "SELECTED") else "Shortlisted",
                completed=current_status in ("SHORTLISTED", "INTERVIEW", "SELECTED"),
                current=current_status == "SHORTLISTED",
                step_order=3,
            ),
            TimelineEventItem(
                status="INTERVIEW",
                stage="Interview",
                label="Interview Scheduled",
                date="Pending Schedule" if current_status not in ("INTERVIEW", "SELECTED") else "Scheduled",
                completed=current_status in ("INTERVIEW", "SELECTED"),
                current=current_status == "INTERVIEW",
                step_order=4,
            ),
            TimelineEventItem(
                status="SELECTED",
                stage="Selected",
                label="Offer Extended",
                date="TBD" if current_status != "SELECTED" else "Selected",
                completed=current_status == "SELECTED",
                current=current_status == "SELECTED",
                step_order=5,
            ),
        ]

    return CandidateApplicationItem(
        application_id=app.application_number,
        id=app.id,
        appNumber=app.application_number,
        job_id=app.job_id,
        jobId=app.job_id,
        job_title=app.job_title,
        title=app.job_title,
        company_name=app.company_name,
        company=app.company_name,
        location=app.location,
        salary=app.salary or "Not Disclosed",
        employment_type=app.employment_type or "Full-time",
        type=app.employment_type or "Full-time",
        work_mode=app.work_mode or "On-site",
        mode=app.work_mode or "On-site",
        applied_at=applied_at_str,
        appliedDate=applied_date_str,
        application_type=app.application_type or "Direct Job Application",
        applicationType=app.application_type or "Direct Job Application",
        job_mela_id=app.mela_id,
        melaId=app.mela_id,
        melaTitle=app.mela_title,
        status=app.status.upper(),
        resume_name=app.resume_name,
        resumeName=app.resume_name,
        cover_letter=app.cover_letter,
        coverLetter=app.cover_letter,
        additional_info=app.additional_info,
        additionalInfo=app.additional_info,
        match_percentage=app.match_percentage,
        matchScore=app.match_percentage,
        timeline=timeline_items,
    )


class CandidateApplicationService:
    @staticmethod
    async def get_candidate_profile(
        db: AsyncSession, user_id: str
    ) -> CandidateProfile:
        """Retrieve candidate profile for the given user, or raise 404."""
        profile = await CandidateDashboardRepository.get_candidate_profile(db, user_id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Candidate profile not found. Please complete your registration first.",
            )
        return profile

    @staticmethod
    async def get_applications(
        db: AsyncSession,
        current_user: User,
        status_filter: Optional[str] = None,
        search: Optional[str] = None,
    ) -> CandidateApplicationsListResponse:
        """
        Fetch applications for the authenticated candidate with status counts.
        """
        profile = await CandidateApplicationService.get_candidate_profile(db, current_user.id)

        # 1. Fetch status counts aggregated directly in database
        counts_dict = await CandidateApplicationRepository.get_status_counts(db, profile.id)
        status_counts = StatusCounts(**counts_dict)

        # 2. Fetch applications with filters
        applications_orm = await CandidateApplicationRepository.list_applications(
            db,
            candidate_profile_id=profile.id,
            status=status_filter,
            search=search,
        )

        app_items = [_serialize_application(a) for a in applications_orm]

        return CandidateApplicationsListResponse(
            candidate=CandidateBrief(
                id=profile.id,
                full_name=profile.name,
            ),
            status_counts=status_counts,
            applications=app_items,
        )

    @staticmethod
    async def get_application_details(
        db: AsyncSession,
        current_user: User,
        identifier: str,
    ) -> CandidateApplicationItem:
        """
        Fetch application details with strict ownership verification.
        Candidate A cannot view Candidate B's application.
        """
        profile = await CandidateApplicationService.get_candidate_profile(db, current_user.id)

        application = await CandidateApplicationRepository.get_by_id_and_candidate(
            db, identifier=identifier, candidate_profile_id=profile.id
        )

        if not application:
            other_app = await CandidateApplicationRepository.get_by_id(db, identifier)
            if other_app and other_app.candidate_profile_id != profile.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You are not authorized to view another candidate's application.",
                )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application not found.",
            )

        return _serialize_application(application)

    @staticmethod
    async def get_application_timeline(
        db: AsyncSession,
        current_user: User,
        identifier: str,
    ) -> ApplicationTimelineResponse:
        """
        Fetch application timeline with strict ownership verification.
        """
        profile = await CandidateApplicationService.get_candidate_profile(db, current_user.id)

        application = await CandidateApplicationRepository.get_by_id_and_candidate(
            db, identifier=identifier, candidate_profile_id=profile.id
        )

        if not application:
            other_app = await CandidateApplicationRepository.get_by_id(db, identifier)
            if other_app and other_app.candidate_profile_id != profile.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You are not authorized to view another candidate's timeline.",
                )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application not found.",
            )

        serialized = _serialize_application(application)
        return ApplicationTimelineResponse(
            application_id=application.application_number,
            timeline=serialized.timeline,
        )

    @staticmethod
    async def create_application(
        db: AsyncSession,
        current_user: User,
        data: CandidateApplicationCreate,
    ) -> CandidateApplicationItem:
        """
        Create a new job application for the authenticated candidate.
        Performs duplicate check (returns 409 Conflict if already applied).
        Generates server-side unique application number.
        Initial status is APPLIED.
        Automatically creates the first timeline event.
        """
        profile = await CandidateApplicationService.get_candidate_profile(db, current_user.id)
        job_id_str = str(data.job_id).strip()

        # Duplicate check: candidate_id + job_id
        existing = await CandidateApplicationRepository.get_by_candidate_and_job(
            db, candidate_profile_id=profile.id, job_id=job_id_str
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="You have already applied for this job.",
            )

        # Check target job if applicable (prevent applying to closed/unpublished jobs)
        from sqlalchemy import select
        from app.models.candidate_profile_details import CandidateSkill
        from app.repositories.job_repository import JobRepository

        target_job = await JobRepository.get_job_by_id(db, job_id_str)
        if target_job:
            if target_job.status == "CLOSED":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="This job posting is closed and no longer accepting applications.",
                )
            if target_job.status != "PUBLISHED":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="This job posting is not currently accepting applications.",
                )

        # Match score calculation based on candidate skills vs required job skills
        match_score = 85
        if target_job:
            cand_skills_stmt = select(CandidateSkill.skill_name).where(CandidateSkill.candidate_profile_id == profile.id)
            cand_skills_res = await db.execute(cand_skills_stmt)
            cand_skills = {row[0].lower().strip() for row in cand_skills_res.all()}

            job_skills = {s.skill_name.lower().strip() for s in target_job.job_skills}
            if not job_skills and target_job.skills:
                job_skills = {s.strip().lower() for s in target_job.skills.split(",") if s.strip()}

            if job_skills and cand_skills:
                common = cand_skills & job_skills
                match_score = max(50, min(100, int((len(common) / len(job_skills)) * 100)))

        is_mela = bool(data.mela_id or (data.application_type and "Mela" in data.application_type))
        app_number = await CandidateApplicationRepository.generate_unique_application_number(
            db, is_mela=is_mela
        )

        now = datetime.now(timezone.utc)
        today_str = now.strftime("%d %b %Y")
        app_id = str(uuid.uuid4())

        new_app = CandidateApplication(
            id=app_id,
            application_number=app_number,
            candidate_profile_id=profile.id,
            job_id=job_id_str,
            job_title=target_job.title if target_job else (data.job_title or f"Job #{job_id_str}"),
            company_name=target_job.company_name if target_job else (data.company_name or "Partner Employer"),
            location=target_job.location if target_job else (data.location or profile.location or "Visakhapatnam, Andhra Pradesh"),
            salary=target_job.salary if target_job else (data.salary or "As per industry standards"),
            employment_type=target_job.job_type if target_job else (data.employment_type or "Full-time"),
            work_mode=target_job.work_mode if target_job else (data.work_mode or "On-site"),
            application_type="Job Mela Application" if is_mela else "Direct Job Application",
            source=getattr(data, "source", None) or ("NTR Vikasa Mega Job Melas" if is_mela else "NTR Vikasa Job Portal Direct"),
            mela_id=data.mela_id,
            mela_title=data.mela_title,
            recruiter_id=target_job.recruiter_id if target_job else None,
            match_percentage=match_score,
            status="APPLIED",
            applied_date=today_str,
            applied_at=now,
            cover_letter=data.cover_letter,
            additional_info=data.additional_info,
            resume_name=data.resume_name,
        )
        created_app = await CandidateApplicationRepository.create_application(db, new_app)

        # Automatically create initial timeline entry
        initial_event = ApplicationTimelineEvent(
            id=str(uuid.uuid4()),
            application_id=created_app.id,
            stage="Applied",
            status="APPLIED",
            label="Application Submitted",
            date=today_str,
            completed=True,
            current=True,
            step_order=1,
            created_at=now,
        )
        await CandidateApplicationRepository.create_timeline_event(db, initial_event)

        # Create persistent application notification
        try:
            from app.services.notification_service import NotificationService
            await NotificationService.create_notification(
                db=db,
                candidate_id=profile.id,
                category="application",
                title=f"Application Submitted: {created_app.job_title}",
                message=f"Your application for {created_app.job_title} at {created_app.company_name} has been submitted successfully (Application No: {created_app.application_number}).",
                link="/candidate/applications",
                application_id=created_app.id,
                job_id=created_app.job_id,
                job_mela_id=created_app.mela_id if is_mela else None,
            )
        except Exception:
            pass

        # Refresh application with timeline events
        full_app = await CandidateApplicationRepository.get_by_id_and_candidate(
            db, identifier=created_app.id, candidate_profile_id=profile.id
        )
        return _serialize_application(full_app or created_app)

