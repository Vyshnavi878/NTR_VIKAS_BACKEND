"""
Recruiter Dashboard Repository
Handles all async MySQL database queries for the Recruiter Dashboard.
Optimized with single aggregations and correlated subqueries.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.recruiter import RecruiterProfile
from app.models.job import Job
from app.models.application import CandidateApplication
from app.models.interview import Interview
from app.models.candidate import CandidateProfile
from app.models.internship import Internship
from app.models.job_mela import JobMelaCompanyParticipation


class RecruiterDashboardRepository:
    """Database repository for recruiter dashboard metrics and entities."""

    @staticmethod
    async def get_recruiter_profile_by_user_id(
        db: AsyncSession, user_id: str
    ) -> Optional[RecruiterProfile]:
        """Fetch recruiter profile by the authenticated user's id."""
        stmt = select(RecruiterProfile).where(RecruiterProfile.user_id == user_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_recruiter_job_ids(
        db: AsyncSession, recruiter_id: str
    ) -> List[str]:
        """Get all internal and external job IDs belonging to the recruiter."""
        stmt = select(Job.id, Job.job_id).where(Job.recruiter_id == recruiter_id)
        result = await db.execute(stmt)
        rows = result.all()
        ids = set()
        for r in rows:
            if r[0]:
                ids.add(r[0])
            if r[1]:
                ids.add(r[1])
        return list(ids)

    @staticmethod
    async def get_active_jobs_count(db: AsyncSession, recruiter_id: str) -> int:
        """Count published/active jobs belonging to the recruiter."""
        stmt = select(func.count(Job.id)).where(
            Job.recruiter_id == recruiter_id,
            Job.status.in_(["PUBLISHED", "ACTIVE"]),
        )
        res = await db.execute(stmt)
        return res.scalar() or 0

    @staticmethod
    async def get_pending_approvals_count(db: AsyncSession, recruiter_id: str) -> int:
        """Count jobs, internships, and job mela participation requests awaiting admin moderation/approval."""
        job_stmt = select(func.count(Job.id)).where(
            Job.recruiter_id == recruiter_id,
            Job.status.in_(["PENDING", "PENDING_APPROVAL"]),
        )
        job_res = await db.execute(job_stmt)
        job_count = job_res.scalar() or 0

        intern_stmt = select(func.count(Internship.id)).where(
            Internship.company_id == recruiter_id,
            Internship.status.in_(["PENDING", "PENDING_APPROVAL"]),
        )
        intern_res = await db.execute(intern_stmt)
        intern_count = intern_res.scalar() or 0

        mela_stmt = select(func.count(JobMelaCompanyParticipation.id)).where(
            JobMelaCompanyParticipation.company_id == recruiter_id,
            JobMelaCompanyParticipation.status.in_(["PENDING", "PENDING_APPROVAL"]),
        )
        mela_res = await db.execute(mela_stmt)
        mela_count = mela_res.scalar() or 0

        return job_count + intern_count + mela_count

    @staticmethod
    async def get_total_applications_count(
        db: AsyncSession, recruiter_id: str, job_ids: List[str]
    ) -> int:
        """Count all applications submitted for this recruiter's positions."""
        conditions = [CandidateApplication.recruiter_id == recruiter_id]
        if job_ids:
            conditions.append(CandidateApplication.job_id.in_(job_ids))
        stmt = select(func.count(CandidateApplication.id)).where(or_(*conditions))
        res = await db.execute(stmt)
        return res.scalar() or 0

    @staticmethod
    async def get_shortlisted_count(
        db: AsyncSession, recruiter_id: str, job_ids: List[str]
    ) -> int:
        """Count applications currently in SHORTLISTED status."""
        conditions = [CandidateApplication.recruiter_id == recruiter_id]
        if job_ids:
            conditions.append(CandidateApplication.job_id.in_(job_ids))
        stmt = select(func.count(CandidateApplication.id)).where(
            or_(*conditions),
            CandidateApplication.status == "SHORTLISTED",
        )
        res = await db.execute(stmt)
        return res.scalar() or 0

    @staticmethod
    async def get_upcoming_interviews_count(db: AsyncSession, recruiter_id: str) -> int:
        """Count future/pending scheduled interviews for this recruiter."""
        stmt = select(func.count(Interview.id)).where(
            Interview.recruiter_id == recruiter_id,
            Interview.status.in_(["SCHEDULED", "CONFIRMED", "UPCOMING"]),
        )
        res = await db.execute(stmt)
        return res.scalar() or 0

    @staticmethod
    async def get_pipeline_counts(
        db: AsyncSession, recruiter_id: str, job_ids: List[str]
    ) -> Dict[str, int]:
        """
        Calculate pipeline funnel metrics from live applications:
        - applications: total valid applications
        - under_review: APPLIED, SCREENING, UNDER_REVIEW
        - shortlisted: SHORTLISTED
        - interviews: INTERVIEW, INTERVIEW_SCHEDULED
        - selected_hired: SELECTED, HIRED
        """
        conditions = [CandidateApplication.recruiter_id == recruiter_id]
        if job_ids:
            conditions.append(CandidateApplication.job_id.in_(job_ids))

        # Query all applications for status aggregation
        stmt = select(CandidateApplication.status).where(or_(*conditions))
        res = await db.execute(stmt)
        statuses = [s.upper() for (s,) in res.all() if s]

        total_apps = len(statuses)
        under_review = sum(1 for s in statuses if s in ("UNDER_REVIEW", "APPLIED", "SCREENING"))
        shortlisted = sum(1 for s in statuses if s == "SHORTLISTED")
        interviews = sum(1 for s in statuses if "INTERVIEW" in s)
        selected_hired = sum(1 for s in statuses if s in ("SELECTED", "HIRED"))

        # If applications don't track interview stage directly, check interview table count
        if interviews == 0:
            interview_stmt = select(func.count(Interview.id)).where(
                Interview.recruiter_id == recruiter_id
            )
            interview_res = await db.execute(interview_stmt)
            interviews = interview_res.scalar() or 0

        return {
            "applications": total_apps,
            "under_review": under_review,
            "shortlisted": shortlisted,
            "interviews": interviews,
            "selected_hired": selected_hired,
        }

    @staticmethod
    async def get_recent_applications(
        db: AsyncSession, recruiter_id: str, job_ids: List[str], limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Return newest applications submitted for recruiter's positions."""
        conditions = [CandidateApplication.recruiter_id == recruiter_id]
        if job_ids:
            conditions.append(CandidateApplication.job_id.in_(job_ids))

        stmt = (
            select(CandidateApplication, CandidateProfile.name.label("candidate_full_name"))
            .outerjoin(
                CandidateProfile,
                CandidateApplication.candidate_profile_id == CandidateProfile.id,
            )
            .where(or_(*conditions))
            .order_by(CandidateApplication.applied_at.desc())
            .limit(limit)
        )
        res = await db.execute(stmt)
        rows = res.all()

        results = []
        for app, cand_name in rows:
            display_name = cand_name or "Applicant"
            applied_date_str = app.applied_date or app.applied_at.strftime("%d %b %Y")
            results.append({
                "id": app.id,
                "application_number": app.application_number,
                "candidate_id": app.candidate_profile_id,
                "candidate_name": display_name,
                "candidateName": display_name,
                "job_id": app.job_id,
                "job_title": app.job_title,
                "jobTitle": app.job_title,
                "experience": app.experience or "3+ yrs",
                "match_percentage": app.match_percentage or 85,
                "matchScore": app.match_percentage or 85,
                "applied_at": app.applied_at.isoformat(),
                "applied_date": applied_date_str,
                "appliedDate": applied_date_str,
                "status": app.status,
            })
        return results

    @staticmethod
    async def get_active_jobs(
        db: AsyncSession, recruiter_id: str, limit: int = 4
    ) -> List[Dict[str, Any]]:
        """
        Return active/published jobs for the recruiter with live application count.
        Uses a correlated subquery for optimal performance without full-group-by issues.
        """
        # Correlated subquery for counting applications
        app_count_subq = (
            select(func.count(CandidateApplication.id))
            .where(
                or_(
                    CandidateApplication.job_id == Job.job_id,
                    CandidateApplication.job_id == Job.id,
                )
            )
            .scalar_subquery()
        )

        stmt = (
            select(Job, app_count_subq.label("applicants_count"))
            .where(
                Job.recruiter_id == recruiter_id,
                Job.status.in_(["PUBLISHED", "ACTIVE"]),
            )
            .order_by(Job.created_at.desc())
            .limit(limit)
        )
        res = await db.execute(stmt)
        rows = res.all()

        results = []
        for job, app_count in rows:
            cnt = app_count or 0
            results.append({
                "id": job.id,
                "job_id": job.job_id,
                "title": job.title,
                "department": job.department or "Engineering",
                "location": job.location,
                "job_type": job.job_type,
                "type": job.job_type,
                "status": job.status,
                "applications_count": cnt,
                "applicantsCount": cnt,
            })
        return results

    @staticmethod
    async def get_upcoming_interviews(
        db: AsyncSession, recruiter_id: str, limit: int = 3
    ) -> List[Dict[str, Any]]:
        """Return upcoming scheduled interviews sorted chronologically."""
        stmt = (
            select(Interview)
            .where(
                Interview.recruiter_id == recruiter_id,
                Interview.status.in_(["SCHEDULED", "CONFIRMED", "UPCOMING"]),
            )
            .order_by(Interview.scheduled_at.asc())
            .limit(limit)
        )
        res = await db.execute(stmt)
        interviews = res.scalars().all()

        results = []
        for item in interviews:
            results.append({
                "id": item.id,
                "interview_number": item.interview_number,
                "candidate_id": item.candidate_profile_id,
                "candidate_name": item.candidate_name,
                "candidateName": item.candidate_name,
                "job_id": item.job_id,
                "job_title": item.job_title,
                "jobTitle": item.job_title,
                "round_name": item.round_name,
                "interview_type": item.interview_type,
                "type": item.interview_type,
                "date": item.date or item.scheduled_at.strftime("%Y-%m-%d"),
                "time": item.time or item.scheduled_at.strftime("%I:%M %p"),
                "scheduled_at": item.scheduled_at.isoformat(),
                "meeting_platform": item.meeting_platform,
                "meeting_link": item.meeting_link,
                "meetingLink": item.meeting_link,
                "status": item.status,
            })
        return results
