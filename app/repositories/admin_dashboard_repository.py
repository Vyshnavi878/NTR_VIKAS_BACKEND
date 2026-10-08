from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy import select, func, or_, case, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.user import User
from app.models.candidate import CandidateProfile
from app.models.recruiter import RecruiterProfile
from app.models.job import Job
from app.models.internship import Internship, InternshipApplication, AuditLog
from app.models.job_mela import JobMela, JobMelaCompanyParticipation
from app.models.application import CandidateApplication
from app.models.report import Report


class AdminDashboardRepository:
    """Repository executing aggregated database queries for the Admin Dashboard Command Center."""

    @classmethod
    async def get_moderation_queue_counts(cls, db: AsyncSession) -> Dict[str, int]:
        """Aggregate pending action counts across recruiters, companies, jobs, internships, melas, and reports."""
        # 1. Pending Recruiters & Companies
        rec_stmt = select(
            func.count(RecruiterProfile.id)
        ).where(
            RecruiterProfile.status.in_(["PENDING_APPROVAL", "PENDING", "PENDING_VERIFICATION"])
        )
        rec_pending = (await db.execute(rec_stmt)).scalar() or 0

        # 2. Pending Jobs
        job_stmt = select(
            func.count(Job.id)
        ).where(
            Job.status.in_(["PENDING", "PENDING_APPROVAL", "UNDER_REVIEW"])
        )
        job_pending = (await db.execute(job_stmt)).scalar() or 0

        # 3. Pending Internships
        intern_stmt = select(
            func.count(Internship.id)
        ).where(
            Internship.status.in_(["PENDING", "PENDING_APPROVAL", "UNDER_REVIEW"])
        )
        intern_pending = (await db.execute(intern_stmt)).scalar() or 0

        # 4. Pending Job Melas
        mela_stmt = select(
            func.count(JobMela.id)
        ).where(
            JobMela.status.in_(["PENDING", "PENDING_APPROVAL", "DRAFT"])
        )
        mela_pending = (await db.execute(mela_stmt)).scalar() or 0

        # 5. Open Reports & Complaints
        report_stmt = select(
            func.count(Report.id)
        ).where(
            Report.status.in_(["PENDING", "OPEN"])
        )
        report_pending = (await db.execute(report_stmt)).scalar() or 0

        total_pending = rec_pending + rec_pending + job_pending + intern_pending + mela_pending + report_pending

        return {
            "pending_recruiter_verifications": rec_pending,
            "pending_company_verifications": rec_pending,
            "pending_job_approvals": job_pending,
            "pending_internship_approvals": intern_pending,
            "pending_job_mela_approvals": mela_pending,
            "open_moderation_reports": report_pending,
            "total_pending": total_pending,
        }

    @classmethod
    async def get_platform_overview_counts(cls, db: AsyncSession) -> Dict[str, int]:
        """Aggregate total platform counts for candidates, recruiters, verified companies, jobs, applications, and melas."""
        # 1. Total Candidates
        cand_stmt = select(func.count(User.id)).where(User.role == "CANDIDATE", User.is_active == True)
        total_candidates = (await db.execute(cand_stmt)).scalar() or 0

        # 2. Total Recruiters
        rec_stmt = select(func.count(User.id)).where(User.role == "RECRUITER", User.is_active == True)
        total_recruiters = (await db.execute(rec_stmt)).scalar() or 0

        # 3. Verified Companies
        comp_stmt = select(func.count(RecruiterProfile.id)).where(
            RecruiterProfile.status.in_(["VERIFIED", "APPROVED"])
        )
        verified_companies = (await db.execute(comp_stmt)).scalar() or 0

        # 4. Active Posted Jobs
        job_stmt = select(func.count(Job.id)).where(
            Job.status.in_(["PUBLISHED", "ACTIVE"])
        )
        active_jobs = (await db.execute(job_stmt)).scalar() or 0

        # 5. Submitted Applications (Job applications + Internship applications)
        job_apps_stmt = select(func.count(CandidateApplication.id)).where(
            CandidateApplication.status != "DRAFT"
        )
        job_apps = (await db.execute(job_apps_stmt)).scalar() or 0

        intern_apps_stmt = select(func.count(InternshipApplication.id))
        intern_apps = (await db.execute(intern_apps_stmt)).scalar() or 0

        submitted_applications = job_apps + intern_apps

        # 6. Job Mela Registrations
        # Try count on job_mela_registrations table or registrations table
        try:
            from app.models.job_mela import JobMelaRegistration
            mela_reg_stmt = select(func.count(JobMelaRegistration.id))
            job_mela_registrations = (await db.execute(mela_reg_stmt)).scalar() or 0
        except Exception:
            # Fallback if registration table model uses different class name
            from sqlalchemy import text
            res = await db.execute(text("SELECT count(*) FROM job_mela_registrations;"))
            job_mela_registrations = res.scalar() or 0

        return {
            "total_candidates": total_candidates,
            "total_recruiters": total_recruiters,
            "verified_companies": verified_companies,
            "active_jobs": active_jobs,
            "submitted_applications": submitted_applications,
            "job_mela_registrations": job_mela_registrations,
        }

    @classmethod
    async def get_pending_moderation_stream(cls, db: AsyncSession, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieve recent pending moderation queue items sorted by submission date."""
        items: List[Dict[str, Any]] = []

        # 1. Pending Recruiters & Companies
        rec_stmt = (
            select(RecruiterProfile)
            .where(RecruiterProfile.status.in_(["PENDING_APPROVAL", "PENDING", "PENDING_VERIFICATION"]))
            .order_by(RecruiterProfile.created_at.desc())
            .limit(5)
        )
        rec_results = (await db.execute(rec_stmt)).scalars().all()
        for r in rec_results:
            d_str = r.created_at.strftime("%Y-%m-%d") if r.created_at else "Recent"
            items.append({
                "id": f"rec-{r.id}",
                "type": "Recruiter Verification",
                "name": r.recruiter_name,
                "entity": f"{r.company_name} • {d_str}",
                "time": d_str,
                "created_at": r.created_at or datetime.now(timezone.utc),
                "link": "/admin/recruiter-verification",
            })
            items.append({
                "id": f"comp-{r.id}",
                "type": "Company Verification",
                "name": r.company_name,
                "entity": f"{r.primary_industry} • {r.recruiter_name} • {d_str}",
                "time": d_str,
                "created_at": r.created_at or datetime.now(timezone.utc),
                "link": "/admin/company-verification",
            })

        # 2. Pending Jobs
        job_stmt = (
            select(Job)
            .where(Job.status.in_(["PENDING", "PENDING_APPROVAL", "UNDER_REVIEW"]))
            .order_by(Job.created_at.desc())
            .limit(5)
        )
        job_results = (await db.execute(job_stmt)).scalars().all()
        for j in job_results:
            d_str = j.created_at.strftime("%Y-%m-%d") if j.created_at else "Recent"
            items.append({
                "id": f"job-{j.id}",
                "type": "Job Approval",
                "name": j.title,
                "entity": f"{j.company_name} • {j.department or 'Engineering'} • {d_str}",
                "time": d_str,
                "created_at": j.created_at or datetime.now(timezone.utc),
                "link": "/admin/job-approvals",
            })

        # 3. Pending Internships
        intern_stmt = (
            select(Internship)
            .options(selectinload(Internship.company))
            .where(Internship.status.in_(["PENDING", "PENDING_APPROVAL", "UNDER_REVIEW"]))
            .order_by(Internship.created_at.desc())
            .limit(5)
        )
        intern_results = (await db.execute(intern_stmt)).scalars().all()
        for i in intern_results:
            d_str = i.created_at.strftime("%Y-%m-%d") if i.created_at else "Recent"
            comp_name = i.company.company_name if i.company else "Company"
            items.append({
                "id": f"intern-{i.id}",
                "type": "Internship Approval",
                "name": i.title,
                "entity": f"{comp_name} • {i.duration} • {d_str}",
                "time": d_str,
                "created_at": i.created_at or datetime.now(timezone.utc),
                "link": "/admin/internship-approvals",
            })

        # 4. Pending Job Melas
        mela_stmt = (
            select(JobMela)
            .where(JobMela.status.in_(["PENDING", "PENDING_APPROVAL", "DRAFT"]))
            .order_by(JobMela.created_at.desc())
            .limit(5)
        )
        mela_results = (await db.execute(mela_stmt)).scalars().all()
        for m in mela_results:
            d_str = m.created_at.strftime("%Y-%m-%d") if m.created_at else "Recent"
            items.append({
                "id": f"mela-{m.id}",
                "type": "Job Mela Approval",
                "name": m.title,
                "entity": f"{m.district} • {m.venue_name} • {d_str}",
                "time": d_str,
                "created_at": m.created_at or datetime.now(timezone.utc),
                "link": "/admin/job-melas",
            })

        # Sort combined items by created_at descending
        items.sort(key=lambda x: x["created_at"], reverse=True)
        return items[:limit]

    @classmethod
    async def get_recent_audit_logs(cls, db: AsyncSession, limit: int = 5) -> List[Dict[str, Any]]:
        """Retrieve latest system and administrative audit log records."""
        stmt = (
            select(AuditLog)
            .order_by(AuditLog.timestamp.desc())
            .limit(limit)
        )
        results = (await db.execute(stmt)).scalars().all()

        formatted = []
        for log in results:
            admin_user = log.actor
            if "@" in log.actor:
                admin_user = log.actor.split("@")[0].replace(".", " ").title()

            action_label = log.action.replace("_", " ").title()
            if "Login" in action_label or "Session" in action_label:
                action_label = "Admin System Login"
            elif "Logout" in action_label:
                action_label = "Admin Logout"

            formatted.append({
                "id": log.id,
                "action": action_label,
                "target": log.target_name or log.entity or "Admin Control Panel",
                "actor": log.actor,
                "adminUser": admin_user,
                "result": log.result or "SUCCESS",
                "time": log.timestamp.strftime("%I:%M %p") if log.timestamp else "Just now",
                "date": log.timestamp.strftime("%Y-%m-%d") if log.timestamp else "Today",
                "created_at": log.timestamp,
            })

        return formatted
