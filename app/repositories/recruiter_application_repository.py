"""
Repository layer for Recruiter Applications.
Provides high-performance SQLAlchemy 2.0 async queries for:
- Recruiter multi-tenant ownership resolution
- Eager-loaded paginated application lists with filters, search, and sorting
- Aggregated application counts for pipeline summary cards and job postings
- Detailed single application lookups with IDOR protection
- Application status transitions and timeline history recording
"""
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple, Set
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_, desc, asc, distinct
from sqlalchemy.orm import selectinload, joinedload

from app.models.application import CandidateApplication, ApplicationTimelineEvent
from app.models.candidate import CandidateProfile
from app.models.candidate_profile_details import CandidateSkill, CandidateResume, CandidateExperience, CandidateEducation
from app.models.user import User
from app.models.job import Job
from app.models.interview import Interview


class RecruiterApplicationRepository:
    """SQLAlchemy 2.0 Async Repository for Recruiter Applications."""

    @staticmethod
    async def get_recruiter_jobs_and_identifiers(
        db: AsyncSession,
        recruiter_id: str,
        company_name: Optional[str] = None,
    ) -> Tuple[List[Job], Set[str]]:
        """Fetch all jobs belonging to the recruiter or recruiter's company."""
        conditions = [Job.recruiter_id == recruiter_id]
        if company_name and company_name.strip():
            conditions.append(Job.company_name.ilike(f"%{company_name.strip()}%"))

        stmt = select(Job).where(or_(*conditions)).order_by(Job.created_at.desc())
        result = await db.execute(stmt)
        jobs = list(result.scalars().all())

        identifiers: Set[str] = set()
        for j in jobs:
            if j.id:
                identifiers.add(str(j.id))
            if j.job_id:
                identifiers.add(str(j.job_id))
                identifiers.add(str(j.job_id).lower())
                identifiers.add(str(j.job_id).upper())
            if j.job_number:
                identifiers.add(str(j.job_number))
                identifiers.add(str(j.job_number).lower())
                identifiers.add(str(j.job_number).upper())

        return jobs, identifiers

    @classmethod
    def build_ownership_condition(
        cls,
        recruiter_id: str,
        owned_identifiers: Set[str],
        company_name: Optional[str] = None,
    ):
        """Construct SQLAlchemy expression restricting applications to the recruiter's tenant."""
        clauses = [CandidateApplication.recruiter_id == recruiter_id]
        if owned_identifiers:
            clauses.append(CandidateApplication.job_id.in_(list(owned_identifiers)))
        if company_name and company_name.strip():
            clauses.append(CandidateApplication.company_name.ilike(f"%{company_name.strip()}%"))

        return or_(*clauses)

    @classmethod
    async def get_applications_paginated(
        cls,
        db: AsyncSession,
        recruiter_id: str,
        owned_identifiers: Set[str],
        company_name: Optional[str] = None,
        page: int = 1,
        page_size: int = 9,
        search: Optional[str] = None,
        job_id: Optional[str] = None,
        status: Optional[str] = None,
        application_type: Optional[str] = None,
        sort_by: Optional[str] = None,
        sort_order: Optional[str] = None,
    ) -> Tuple[List[CandidateApplication], int]:
        """Fetch paginated, filtered, searched, and sorted applications with full relationships."""
        ownership_cond = cls.build_ownership_condition(recruiter_id, owned_identifiers, company_name)
        filter_clauses = [ownership_cond]

        # Job ID Filter
        if job_id and job_id.strip() and job_id.strip().upper() != "ALL":
            raw_jid = job_id.strip()
            # Match variants: e.g. "JOB-101", "job-101", uuid
            jid_variants = [raw_jid, raw_jid.lower(), raw_jid.upper()]
            if raw_jid.lower().startswith("job-"):
                num_part = raw_jid[4:]
                jid_variants.extend([num_part, f"JOB-{num_part.upper()}", f"job-{num_part.lower()}"])
            filter_clauses.append(CandidateApplication.job_id.in_(jid_variants))

        # Status Filter
        if status and status.strip() and status.strip().upper() != "ALL":
            norm_st = status.strip().upper()
            if norm_st in ("SCREENING", "APPLIED", "UNDER_REVIEW"):
                filter_clauses.append(CandidateApplication.status.in_(["SCREENING", "APPLIED", "UNDER_REVIEW"]))
            elif norm_st == "SHORTLISTED":
                filter_clauses.append(CandidateApplication.status == "SHORTLISTED")
            elif norm_st in ("INTERVIEW", "INTERVIEW_SCHEDULED"):
                filter_clauses.append(CandidateApplication.status.in_(["INTERVIEW", "INTERVIEW_SCHEDULED"]))
            elif norm_st in ("SELECTED", "HIRED"):
                filter_clauses.append(CandidateApplication.status.in_(["SELECTED", "HIRED"]))
            elif norm_st == "REJECTED":
                filter_clauses.append(CandidateApplication.status == "REJECTED")
            else:
                filter_clauses.append(CandidateApplication.status == norm_st)

        # Application Type Filter
        if application_type and application_type.strip():
            raw_type = application_type.strip().upper()
            if "MELA" in raw_type:
                filter_clauses.append(CandidateApplication.application_type.ilike("%Mela%"))
            elif "DIRECT" in raw_type:
                filter_clauses.append(CandidateApplication.application_type.ilike("%Direct%"))

        # Search Query
        needs_user_join = False
        needs_cand_join = False
        if search and search.strip():
            q = f"%{search.strip().lower()}%"
            needs_cand_join = True
            needs_user_join = True
            search_cond = or_(
                CandidateApplication.application_number.ilike(q),
                CandidateApplication.job_title.ilike(q),
                CandidateApplication.job_id.ilike(q),
                CandidateApplication.company_name.ilike(q),
                CandidateApplication.location.ilike(q),
                CandidateApplication.mela_title.ilike(q),
                CandidateApplication.mela_id.ilike(q),
                CandidateProfile.name.ilike(q),
                User.email.ilike(q),
            )
            filter_clauses.append(search_cond)

        combined_filter = and_(*filter_clauses)

        # 1. Total items count
        count_stmt = select(func.count(distinct(CandidateApplication.id)))
        if needs_cand_join:
            count_stmt = count_stmt.join(CandidateProfile, CandidateApplication.candidate_profile_id == CandidateProfile.id)
        if needs_user_join:
            count_stmt = count_stmt.join(User, CandidateProfile.user_id == User.id)
        count_stmt = count_stmt.where(combined_filter)
        total_items = (await db.execute(count_stmt)).scalar() or 0

        # 2. Sorting specification
        order_by_items = []
        sort_field = (sort_by or "newest").lower().strip()
        direction = (sort_order or "desc").lower().strip()

        if sort_field in ("match", "match_score"):
            order_by_items.append(CandidateApplication.match_percentage.is_(None))
            if direction == "asc":
                order_by_items.append(asc(CandidateApplication.match_percentage))
            else:
                order_by_items.append(desc(CandidateApplication.match_percentage))
        elif sort_field == "oldest":
            order_by_items.append(asc(CandidateApplication.applied_at))
        elif sort_field in ("newest", "applied_at"):
            if direction == "asc":
                order_by_items.append(asc(CandidateApplication.applied_at))
            else:
                order_by_items.append(desc(CandidateApplication.applied_at))
        else:
            order_by_items.append(desc(CandidateApplication.applied_at))

        # Stable secondary ordering
        order_by_items.append(desc(CandidateApplication.id))

        # 3. Main Data Query with eager loading
        offset = max(0, (page - 1) * page_size)
        data_stmt = (
            select(CandidateApplication)
            .options(
                selectinload(CandidateApplication.candidate_profile).selectinload(CandidateProfile.user),
                selectinload(CandidateApplication.candidate_profile).selectinload(CandidateProfile.skills),
                selectinload(CandidateApplication.candidate_profile).selectinload(CandidateProfile.resumes),
                selectinload(CandidateApplication.candidate_profile).selectinload(CandidateProfile.experiences),
                selectinload(CandidateApplication.candidate_profile).selectinload(CandidateProfile.educations),
                selectinload(CandidateApplication.interviews),
                selectinload(CandidateApplication.timeline_events),
            )
        )
        if needs_cand_join:
            data_stmt = data_stmt.join(CandidateProfile, CandidateApplication.candidate_profile_id == CandidateProfile.id)
        if needs_user_join:
            data_stmt = data_stmt.join(User, CandidateProfile.user_id == User.id)

        data_stmt = (
            data_stmt.where(combined_filter)
            .order_by(*order_by_items)
            .offset(offset)
            .limit(page_size)
        )

        result = await db.execute(data_stmt)
        items = list(result.scalars().all())

        return items, total_items

    @classmethod
    async def get_summary_counts(
        cls,
        db: AsyncSession,
        recruiter_id: str,
        owned_identifiers: Set[str],
        company_name: Optional[str] = None,
        job_id: Optional[str] = None,
    ) -> Dict[str, int]:
        """Aggregate application pipeline summary counts for summary cards and tabs."""
        ownership_cond = cls.build_ownership_condition(recruiter_id, owned_identifiers, company_name)
        filters = [ownership_cond]

        if job_id and job_id.strip() and job_id.strip().upper() != "ALL":
            raw_jid = job_id.strip()
            jid_variants = [raw_jid, raw_jid.lower(), raw_jid.upper()]
            if raw_jid.lower().startswith("job-"):
                num_part = raw_jid[4:]
                jid_variants.extend([num_part, f"JOB-{num_part.upper()}", f"job-{num_part.lower()}"])
            filters.append(CandidateApplication.job_id.in_(jid_variants))

        base_filter = and_(*filters)

        # Aggregate counts via conditional sums in a single query
        stmt = select(
            func.count(CandidateApplication.id).label("total_received"),
            func.sum(
                func.if_(
                    CandidateApplication.status.in_(["SCREENING", "APPLIED", "UNDER_REVIEW"]),
                    1,
                    0,
                )
            ).label("screening"),
            func.sum(
                func.if_(
                    CandidateApplication.status == "SHORTLISTED",
                    1,
                    0,
                )
            ).label("shortlisted"),
            func.sum(
                func.if_(
                    CandidateApplication.status.in_(["INTERVIEW", "INTERVIEW_SCHEDULED"]),
                    1,
                    0,
                )
            ).label("interviews"),
            func.sum(
                func.if_(
                    CandidateApplication.status.in_(["SELECTED", "HIRED"]),
                    1,
                    0,
                )
            ).label("selected_hired"),
            func.sum(
                func.if_(
                    CandidateApplication.status == "REJECTED",
                    1,
                    0,
                )
            ).label("rejected"),
        ).where(base_filter)

        row = (await db.execute(stmt)).one()
        return {
            "total_received": int(row.total_received or 0),
            "screening": int(row.screening or 0),
            "shortlisted": int(row.shortlisted or 0),
            "interviews": int(row.interviews or 0),
            "selected_hired": int(row.selected_hired or 0),
            "rejected": int(row.rejected or 0),
        }

    @classmethod
    async def get_job_postings_with_counts(
        cls,
        db: AsyncSession,
        jobs: List[Job],
        recruiter_id: str,
        owned_identifiers: Set[str],
        company_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Compute the application count for each recruiter job posting."""
        if not jobs:
            return []

        ownership_cond = cls.build_ownership_condition(recruiter_id, owned_identifiers, company_name)

        # Count per job_id
        stmt = (
            select(
                CandidateApplication.job_id,
                func.count(CandidateApplication.id).label("app_count"),
            )
            .where(ownership_cond)
            .group_by(CandidateApplication.job_id)
        )
        counts_res = await db.execute(stmt)
        count_map = {str(row[0]).lower(): int(row[1]) for row in counts_res.all() if row[0]}

        result = []
        for j in jobs:
            # Check all possible keys that might have matched
            keys = [
                str(j.id).lower() if j.id else "",
                str(j.job_id).lower() if j.job_id else "",
                str(j.job_number).lower() if j.job_number else "",
            ]
            total_for_job = sum(count_map.get(k, 0) for k in keys if k)

            result.append({
                "job_id": j.job_id or str(j.id),
                "title": j.title,
                "application_count": total_for_job,
            })

        return result

    @classmethod
    async def get_application_by_id(
        cls,
        db: AsyncSession,
        application_id: str,
        recruiter_id: str,
        owned_identifiers: Set[str],
        company_name: Optional[str] = None,
    ) -> Optional[CandidateApplication]:
        """Fetch single application by UUID or Application Number with tenant ownership validation."""
        ownership_cond = cls.build_ownership_condition(recruiter_id, owned_identifiers, company_name)
        id_cond = or_(
            CandidateApplication.id == application_id,
            CandidateApplication.application_number == application_id,
        )

        stmt = (
            select(CandidateApplication)
            .options(
                selectinload(CandidateApplication.candidate_profile).selectinload(CandidateProfile.user),
                selectinload(CandidateApplication.candidate_profile).selectinload(CandidateProfile.skills),
                selectinload(CandidateApplication.candidate_profile).selectinload(CandidateProfile.resumes),
                selectinload(CandidateApplication.candidate_profile).selectinload(CandidateProfile.experiences),
                selectinload(CandidateApplication.candidate_profile).selectinload(CandidateProfile.educations),
                selectinload(CandidateApplication.interviews),
                selectinload(CandidateApplication.timeline_events),
            )
            .where(and_(id_cond, ownership_cond))
        )

        result = await db.execute(stmt)
        return result.scalars().first()

    @classmethod
    async def update_application_status(
        cls,
        db: AsyncSession,
        application: CandidateApplication,
        new_status: str,
        notes: Optional[str] = None,
    ) -> CandidateApplication:
        """Update application status, create a timeline event, and commit."""
        now = datetime.now(timezone.utc)
        application.status = new_status
        application.updated_at = now

        # Add timeline event
        stage_map = {
            "APPLIED": "Application Received",
            "SCREENING": "Candidate Screening",
            "UNDER_REVIEW": "Under Review",
            "SHORTLISTED": "Candidate Shortlisted",
            "INTERVIEW": "Interview Round",
            "INTERVIEW_SCHEDULED": "Interview Scheduled",
            "SELECTED": "Offer / Selected",
            "HIRED": "Hired",
            "REJECTED": "Application Rejected",
        }
        stage_name = stage_map.get(new_status, new_status.title())

        # Determine step order
        next_step = len(application.timeline_events) + 1 if application.timeline_events else 1

        # Mark previous events as current=False
        for event in (application.timeline_events or []):
            event.current = False

        timeline_event = ApplicationTimelineEvent(
            application_id=application.id,
            stage=stage_name,
            status=new_status,
            label=f"Status updated to {stage_name} by Recruiter" + (f": {notes}" if notes else ""),
            date=now.strftime("%d %b %Y"),
            completed=new_status in ("SHORTLISTED", "SELECTED", "HIRED"),
            current=True,
            step_order=next_step,
            created_at=now,
        )
        db.add(timeline_event)
        await db.commit()
        await db.refresh(application)
        return application
