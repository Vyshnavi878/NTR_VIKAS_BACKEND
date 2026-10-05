from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import select, func, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.recruiter import RecruiterProfile
from app.models.job import Job
from app.models.application import CandidateApplication
from app.models.interview import Interview

CANONICAL_SOURCES = [
    {"source": "NTR Vikasa Job Portal Direct", "color": "var(--color-primary-600)"},
    {"source": "NTR Vikasa Mega Job Melas", "color": "#8b5cf6"},
    {"source": "Skill Training Direct Pool", "color": "#10b981"},
    {"source": "Employee Referrals", "color": "#f59e0b"},
]


class RecruiterAnalyticsRepository:
    """
    Database repository layer for Recruiter Hiring Analytics queries using SQLAlchemy 2.0 AsyncIO.
    """

    @staticmethod
    async def get_recruiter_profile_by_user_id(
        db: AsyncSession, user_id: str
    ) -> Optional[RecruiterProfile]:
        """Fetch recruiter profile by authenticated user's ID."""
        stmt = select(RecruiterProfile).where(RecruiterProfile.user_id == user_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_recruiter_job_ids(
        db: AsyncSession, recruiter_id: str
    ) -> List[str]:
        """Fetch all internal (UUID) and external (slug) job IDs belonging to this recruiter."""
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
    def _build_app_filter(
        recruiter_id: str,
        job_ids: List[str],
        start_dt: datetime,
        end_dt: datetime,
    ):
        """Build condition matching applications for recruiter's jobs within date range."""
        ownership_cond = [CandidateApplication.recruiter_id == recruiter_id]
        if job_ids:
            ownership_cond.append(CandidateApplication.job_id.in_(job_ids))

        return and_(
            or_(*ownership_cond),
            CandidateApplication.applied_at >= start_dt,
            CandidateApplication.applied_at <= end_dt,
        )

    @staticmethod
    async def get_summary_metrics(
        db: AsyncSession,
        recruiter_id: str,
        job_ids: List[str],
        start_dt: datetime,
        end_dt: datetime,
    ) -> Dict[str, Any]:
        """
        Aggregate total applications, shortlisted, interviews, and time to hire.
        """
        app_filter = RecruiterAnalyticsRepository._build_app_filter(
            recruiter_id, job_ids, start_dt, end_dt
        )

        # Total applications
        total_stmt = select(func.count(CandidateApplication.id)).where(app_filter)
        total_apps = (await db.execute(total_stmt)).scalar() or 0

        # Shortlisted applications (SHORTLISTED, INTERVIEW, SELECTED, HIRED)
        shortlist_filter = and_(
            app_filter,
            CandidateApplication.status.in_(["SHORTLISTED", "INTERVIEW", "SELECTED", "HIRED"]),
        )
        shortlist_stmt = select(func.count(CandidateApplication.id)).where(shortlist_filter)
        shortlisted_apps = (await db.execute(shortlist_stmt)).scalar() or 0

        # Interviews conducted/scheduled in period
        int_stmt = select(func.count(Interview.id)).where(
            Interview.recruiter_id == recruiter_id,
            Interview.scheduled_at >= start_dt,
            Interview.scheduled_at <= end_dt,
        )
        interviews_count = (await db.execute(int_stmt)).scalar() or 0

        # Average time to hire calculation
        hired_stmt = select(CandidateApplication.applied_at, CandidateApplication.updated_at).where(
            and_(
                app_filter,
                CandidateApplication.status.in_(["SELECTED", "HIRED"]),
            )
        )
        hired_rows = (await db.execute(hired_stmt)).all()
        avg_days = 0
        if hired_rows:
            diffs = []
            for row in hired_rows:
                applied_at = row[0]
                updated_at = row[1]
                if applied_at and updated_at:
                    diff_days = max(1, (updated_at - applied_at).days)
                    diffs.append(diff_days)
            if diffs:
                avg_days = round(sum(diffs) / len(diffs))

        conversion_rate = 0.0
        if total_apps > 0:
            conversion_rate = round((shortlisted_apps / total_apps) * 100, 1)

        return {
            "total_applications": total_apps,
            "shortlist_conversion": conversion_rate,
            "interviews_conducted": interviews_count,
            "average_time_to_hire_days": avg_days,
            "shortlisted_count": shortlisted_apps,
        }

    @staticmethod
    async def get_recruitment_funnel(
        db: AsyncSession,
        recruiter_id: str,
        job_ids: List[str],
        start_dt: datetime,
        end_dt: datetime,
        interviews_count: int,
    ) -> Dict[str, int]:
        """Calculate stage counts for the recruitment funnel."""
        app_filter = RecruiterAnalyticsRepository._build_app_filter(
            recruiter_id, job_ids, start_dt, end_dt
        )

        total_stmt = select(func.count(CandidateApplication.id)).where(app_filter)
        total_apps = (await db.execute(total_stmt)).scalar() or 0

        shortlist_stmt = select(func.count(CandidateApplication.id)).where(
            and_(
                app_filter,
                CandidateApplication.status.in_(["SHORTLISTED", "INTERVIEW", "SELECTED", "HIRED"]),
            )
        )
        shortlisted_apps = (await db.execute(shortlist_stmt)).scalar() or 0

        # Technical interviews: either actual interview count or applications that reached interview/hire
        app_interview_stmt = select(func.count(CandidateApplication.id)).where(
            and_(
                app_filter,
                CandidateApplication.status.in_(["INTERVIEW", "SELECTED", "HIRED"]),
            )
        )
        app_interview_count = (await db.execute(app_interview_stmt)).scalar() or 0
        final_interviews = max(interviews_count, app_interview_count)

        hired_stmt = select(func.count(CandidateApplication.id)).where(
            and_(
                app_filter,
                CandidateApplication.status.in_(["SELECTED", "HIRED"]),
            )
        )
        hired_count = (await db.execute(hired_stmt)).scalar() or 0

        return {
            "applications_received": total_apps,
            "profile_shortlisted": shortlisted_apps,
            "technical_interviews": final_interviews,
            "final_offers_hires": hired_count,
        }

    @staticmethod
    async def get_job_posting_performance(
        db: AsyncSession,
        recruiter_id: str,
        start_dt: datetime,
        end_dt: datetime,
    ) -> List[Dict[str, Any]]:
        """Return performance statistics for all jobs posted by the recruiter."""
        jobs_stmt = (
            select(Job)
            .where(Job.recruiter_id == recruiter_id)
            .order_by(Job.created_at.desc())
        )
        jobs = (await db.execute(jobs_stmt)).scalars().all()

        results = []
        for job in jobs:
            job_match_ids = [job.id]
            if job.job_id:
                job_match_ids.append(job.job_id)

            app_filter = and_(
                CandidateApplication.job_id.in_(job_match_ids),
                CandidateApplication.applied_at >= start_dt,
                CandidateApplication.applied_at <= end_dt,
            )

            # Applicants count for this job
            app_stmt = select(func.count(CandidateApplication.id)).where(app_filter)
            applicants = (await db.execute(app_stmt)).scalar() or 0

            # Shortlisted count for this job
            sl_stmt = select(func.count(CandidateApplication.id)).where(
                and_(
                    app_filter,
                    CandidateApplication.status.in_(["SHORTLISTED", "INTERVIEW", "SELECTED", "HIRED"]),
                )
            )
            shortlisted = (await db.execute(sl_stmt)).scalar() or 0

            # Interviews count for this job
            int_stmt = select(func.count(Interview.id)).where(
                Interview.job_id.in_(job_match_ids),
                Interview.scheduled_at >= start_dt,
                Interview.scheduled_at <= end_dt,
            )
            interviews = (await db.execute(int_stmt)).scalar() or 0

            results.append({
                "job_id": job.job_id or job.id,
                "job_title": job.title,
                "department": job.department or "Engineering",
                "work_mode": job.work_mode or "Hybrid",
                "applicants": applicants,
                "shortlisted": shortlisted,
                "interviews": interviews,
                "status": job.status or "PUBLISHED",
            })

        return results

    @staticmethod
    async def get_candidate_sourcing_breakdown(
        db: AsyncSession,
        recruiter_id: str,
        job_ids: List[str],
        start_dt: datetime,
        end_dt: datetime,
    ) -> List[Dict[str, Any]]:
        """Return counts and percentages grouped by candidate application source."""
        app_filter = RecruiterAnalyticsRepository._build_app_filter(
            recruiter_id, job_ids, start_dt, end_dt
        )

        stmt = (
            select(CandidateApplication.source, func.count(CandidateApplication.id))
            .where(app_filter)
            .group_by(CandidateApplication.source)
        )
        rows = (await db.execute(stmt)).all()
        source_counts = {r[0]: r[1] for r in rows if r[0]}

        total = sum(source_counts.values())

        # Ensure all 4 canonical sources are represented
        results = []
        for item in CANONICAL_SOURCES:
            src_name = item["source"]
            cnt = source_counts.get(src_name, 0)
            pct = round((cnt / total) * 100, 1) if total > 0 else 0.0
            results.append({
                "source": src_name,
                "applicants": cnt,
                "percentage": pct,
                "color": item["color"],
            })

        # Add any other source dynamically
        for src_name, cnt in source_counts.items():
            if not any(r["source"] == src_name for r in results):
                pct = round((cnt / total) * 100, 1) if total > 0 else 0.0
                results.append({
                    "source": src_name,
                    "applicants": cnt,
                    "percentage": pct,
                    "color": "#64748b",
                })

        return results

    @staticmethod
    async def get_application_velocity(
        db: AsyncSession,
        recruiter_id: str,
        job_ids: List[str],
        start_dt: datetime,
        end_dt: datetime,
        range_type: str,
    ) -> List[Dict[str, Any]]:
        """
        Return period-based application volume and hires trend.
        Uses database dates to group applications by Month/Period.
        """
        app_filter = RecruiterAnalyticsRepository._build_app_filter(
            recruiter_id, job_ids, start_dt, end_dt
        )

        stmt = select(
            CandidateApplication.applied_at,
            CandidateApplication.status,
        ).where(app_filter).order_by(CandidateApplication.applied_at.asc())
        rows = (await db.execute(stmt)).all()

        # Build periods
        if range_type == "7d":
            # 7 daily buckets
            from datetime import timedelta
            periods_map = {}
            cur = start_dt
            while cur <= end_dt:
                key = cur.strftime("%d %b")
                periods_map[key] = {"total_applicants": 0, "hired_candidates": 0, "interviews": 0}
                cur += timedelta(days=1)
            for r in rows:
                if r[0]:
                    k = r[0].strftime("%d %b")
                    if k in periods_map:
                        periods_map[k]["total_applicants"] += 1
                        if r[1] in ["SELECTED", "HIRED"]:
                            periods_map[k]["hired_candidates"] += 1
            return [
                {
                    "period": k,
                    "month": k,
                    "total_applicants": v["total_applicants"],
                    "applicants": v["total_applicants"],
                    "hired_candidates": v["hired_candidates"],
                    "hired": v["hired_candidates"],
                    "interviews": v["interviews"],
                }
                for k, v in periods_map.items()
            ]
        else:
            # Monthly buckets for 30d, 90d, 1y, or custom
            # Generate relevant months in range
            periods_map = {}
            for r in rows:
                if r[0]:
                    k = r[0].strftime("%b")
                    if k not in periods_map:
                        periods_map[k] = {"total_applicants": 0, "hired_candidates": 0, "interviews": 0}
                    periods_map[k]["total_applicants"] += 1
                    if r[1] in ["SELECTED", "HIRED"]:
                        periods_map[k]["hired_candidates"] += 1

            if not periods_map:
                # Return standard monthly placeholder periods so chart renders gracefully
                cur_month = end_dt.strftime("%b")
                periods_map[cur_month] = {"total_applicants": 0, "hired_candidates": 0, "interviews": 0}

            return [
                {
                    "period": k,
                    "month": k,
                    "total_applicants": v["total_applicants"],
                    "applicants": v["total_applicants"],
                    "hired_candidates": v["hired_candidates"],
                    "hired": v["hired_candidates"],
                    "interviews": v["interviews"],
                }
                for k, v in periods_map.items()
            ]
