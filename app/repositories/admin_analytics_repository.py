from datetime import datetime, timezone
from typing import Dict, List, Tuple, Any, Optional
from sqlalchemy import select, func, or_, and_, distinct
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.candidate import CandidateProfile
from app.models.recruiter import RecruiterProfile
from app.models.job import Job
from app.models.internship import Internship, InternshipApplication
from app.models.application import CandidateApplication
from app.models.job_mela import JobMelaRegistration
from app.schemas.admin_analytics import (
    AnalyticsKPIs,
    SectorDemandItem,
    MonthlyPlacementItem,
)


class AdminAnalyticsRepository:
    """Async database repository for Platform-Wide Analytics calculations."""

    @staticmethod
    async def get_kpis(
        db: AsyncSession,
        start_dt: Optional[datetime] = None,
        end_dt: Optional[datetime] = None,
    ) -> AnalyticsKPIs:
        """
        Calculates all 8 platform KPIs based on real MySQL records.
        """
        # 1. Total Platform Users
        user_stmt = select(func.count(User.id))
        if end_dt:
            user_stmt = user_stmt.where(User.created_at <= end_dt)
        total_users = (await db.execute(user_stmt)).scalar_one_or_none() or 0

        # 2. Active Candidates
        cand_stmt = (
            select(func.count(CandidateProfile.id))
            .join(User, CandidateProfile.user_id == User.id)
            .where(User.is_active.is_(True))
        )
        if end_dt:
            cand_stmt = cand_stmt.where(CandidateProfile.created_at <= end_dt)
        active_candidates = (await db.execute(cand_stmt)).scalar_one_or_none() or 0

        # 3. Verified Recruiters
        rec_stmt = select(func.count(RecruiterProfile.id)).where(
            RecruiterProfile.status.in_(["APPROVED", "VERIFIED", "ACTIVE"])
        )
        if end_dt:
            rec_stmt = rec_stmt.where(RecruiterProfile.created_at <= end_dt)
        verified_recruiters = (await db.execute(rec_stmt)).scalar_one_or_none() or 0

        # 4. Registered Companies
        comp_stmt = select(func.count(distinct(RecruiterProfile.company_name)))
        if end_dt:
            comp_stmt = comp_stmt.where(RecruiterProfile.created_at <= end_dt)
        registered_companies = (await db.execute(comp_stmt)).scalar_one_or_none() or 0

        # 5. Live Posted Jobs (PUBLISHED or ACTIVE)
        job_stmt = select(func.count(Job.id)).where(
            Job.status.in_(["PUBLISHED", "ACTIVE"])
        )
        if end_dt:
            job_stmt = job_stmt.where(Job.created_at <= end_dt)
        live_jobs = (await db.execute(job_stmt)).scalar_one_or_none() or 0

        # 6. Submitted Applications (Jobs + Internships)
        job_app_stmt = select(func.count(CandidateApplication.id))
        if end_dt:
            job_app_stmt = job_app_stmt.where(CandidateApplication.created_at <= end_dt)
        job_apps = (await db.execute(job_app_stmt)).scalar_one_or_none() or 0

        intern_app_stmt = select(func.count(InternshipApplication.id))
        if end_dt:
            intern_app_stmt = intern_app_stmt.where(InternshipApplication.created_at <= end_dt)
        intern_apps = (await db.execute(intern_app_stmt)).scalar_one_or_none() or 0

        submitted_apps = job_apps + intern_apps

        # 7. Active Internships (PUBLISHED or ACTIVE)
        intern_stmt = select(func.count(Internship.id)).where(
            Internship.status.in_(["PUBLISHED", "ACTIVE"])
        )
        if end_dt:
            intern_stmt = intern_stmt.where(Internship.created_at <= end_dt)
        active_internships = (await db.execute(intern_stmt)).scalar_one_or_none() or 0

        # 8. Mela Registrations
        mela_reg_stmt = select(func.count(JobMelaRegistration.id))
        if end_dt:
            mela_reg_stmt = mela_reg_stmt.where(JobMelaRegistration.created_at <= end_dt)
        mela_registrations = (await db.execute(mela_reg_stmt)).scalar_one_or_none() or 0

        return AnalyticsKPIs(
            total_platform_users=total_users,
            active_candidates=active_candidates,
            verified_recruiters=verified_recruiters,
            registered_companies=registered_companies,
            live_posted_jobs=live_jobs,
            submitted_applications=submitted_apps,
            active_internships=active_internships,
            mela_registrations=mela_registrations,
        )

    @staticmethod
    async def get_hiring_demand_by_sector(
        db: AsyncSession,
        start_dt: Optional[datetime] = None,
        end_dt: Optional[datetime] = None,
    ) -> List[SectorDemandItem]:
        """
        Calculates job count and percentage distribution grouped by industry sector.
        """
        # Fetch all live jobs with their department and recruiter industry
        stmt = (
            select(
                Job.id,
                Job.department,
                Job.title,
                RecruiterProfile.primary_industry,
            )
            .outerjoin(RecruiterProfile, Job.recruiter_id == RecruiterProfile.id)
            .where(Job.status.in_(["PUBLISHED", "ACTIVE"]))
        )
        if end_dt:
            stmt = stmt.where(Job.created_at <= end_dt)

        res = await db.execute(stmt)
        job_rows = res.all()
        total_live_jobs = len(job_rows)

        # Standard sector buckets
        categories = {
            "Information Technology & Software": {"color": "#3b82f6", "count": 0, "keywords": ["it", "tech", "software", "developer", "engineering", "data", "cloud", "ai", "web", "infra"]},
            "Banking, Financial Services & Insurance": {"color": "#10b981", "count": 0, "keywords": ["banking", "finance", "bfsi", "insurance", "fintech", "accounts", "tax"]},
            "Healthcare Diagnostics & Pharma": {"color": "#8b5cf6", "count": 0, "keywords": ["health", "pharma", "biotech", "medical", "hospital", "diagnostics", "clinic"]},
            "E-Commerce, Logistics & Retail": {"color": "#f59e0b", "count": 0, "keywords": ["logistics", "retail", "e-commerce", "ecommerce", "supply chain", "warehouse", "store"]},
            "Core Engineering & Manufacturing": {"color": "#ec4899", "count": 0, "keywords": ["manufacturing", "mechanical", "electrical", "civil", "core", "industrial", "automobile", "production"]},
        }

        # Classify each job
        for row in job_rows:
            dept = (row.department or "").lower()
            title = (row.title or "").lower()
            industry = (row.primary_industry or "").lower()
            combined = f"{dept} {title} {industry}"

            matched = False
            for cat_name, cat_info in categories.items():
                if any(kw in combined for kw in cat_info["keywords"]):
                    cat_info["count"] += 1
                    matched = True
                    break

            if not matched:
                # Default to IT & Software if tech or first category
                categories["Information Technology & Software"]["count"] += 1

        # Build response items
        items = []
        for cat_name, cat_info in categories.items():
            cnt = cat_info["count"]
            pct = round((cnt / total_live_jobs * 100), 1) if total_live_jobs > 0 else 0.0
            items.append(
                SectorDemandItem(
                    name=cat_name,
                    sector=cat_name,
                    share=f"{pct}%",
                    percentage=pct,
                    count=f"{cnt:,} Jobs",
                    job_count=cnt,
                    color=cat_info["color"],
                )
            )

        return items

    @staticmethod
    async def get_monthly_placement_trajectory(
        db: AsyncSession,
        start_dt: Optional[datetime] = None,
        end_dt: Optional[datetime] = None,
    ) -> List[MonthlyPlacementItem]:
        """
        Calculates monthly trajectory of candidates, active jobs, and placements.
        """
        end_date = end_dt or datetime.now(timezone.utc)

        # Generate month list (default 5 recent months up to end_date)
        from dateutil.relativedelta import relativedelta
        current = end_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        months_list = []
        for i in range(4, -1, -1):
            m_dt = current - relativedelta(months=i)
            months_list.append(m_dt)

        items = []
        for m_start in months_list:
            m_end = (m_start + relativedelta(months=1)) - relativedelta(microseconds=1)
            month_label = m_start.strftime("%b %Y")
            date_key = m_start.strftime("%Y-%m")

            # 1. Total Cumulative Candidates registered up to that month
            cand_res = await db.execute(
                select(func.count(CandidateProfile.id)).where(CandidateProfile.created_at <= m_end)
            )
            cand_count = cand_res.scalar_one_or_none() or 0

            # 2. Cumulative Active Jobs published up to that month
            job_res = await db.execute(
                select(func.count(Job.id)).where(
                    Job.status.in_(["PUBLISHED", "ACTIVE"]),
                    Job.created_at <= m_end,
                )
            )
            job_count = job_res.scalar_one_or_none() or 0

            # 3. Placements in that month (SELECTED, PLACED, HIRED)
            placement_res = await db.execute(
                select(func.count(CandidateApplication.id)).where(
                    CandidateApplication.status.in_(["SELECTED", "PLACED", "HIRED"]),
                    CandidateApplication.applied_at <= m_end,
                )
            )
            placement_count = placement_res.scalar_one_or_none() or 0

            items.append(
                MonthlyPlacementItem(
                    month=month_label,
                    date_key=date_key,
                    candidates=cand_count,
                    active_jobs=job_count,
                    placements=placement_count,
                )
            )

        return items
