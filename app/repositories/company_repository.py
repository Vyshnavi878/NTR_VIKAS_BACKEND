from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timezone
from sqlalchemy import select, func, or_, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.recruiter import RecruiterProfile
from app.models.user import User
from app.models.job import Job, JobSkill
from app.models.internship import Internship


class CompanyRepository:
    """
    Database repository layer for Company information derived from RecruiterProfile,
    calculating live active jobs and internships, and managing verification governance.
    """

    @staticmethod
    async def get_verified_companies(
        db: AsyncSession,
        search: Optional[str] = None,
        industry: Optional[str] = None,
        location: Optional[str] = None,
        page: int = 1,
        page_size: int = 12,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Fetch verified companies for public and candidate directories."""
        # 1. Base conditions: strictly APPROVED or VERIFIED, and user is active
        conds = [
            RecruiterProfile.status.in_(["APPROVED", "VERIFIED"]),
            RecruiterProfile.user.has(User.is_active.is_(True)),
        ]

        # 2. Search filter: name, industry, location, description, tagline, or tech skills in jobs
        if search and search.strip():
            q = f"%{search.strip()}%"
            # Subqueries for jobs/skills matching search term
            job_match_subq = select(Job.recruiter_id).where(
                and_(
                    Job.status == "PUBLISHED",
                    Job.closed_at.is_(None),
                    or_(
                        Job.title.ilike(q),
                        Job.skills.ilike(q),
                        Job.job_skills.any(JobSkill.skill_name.ilike(q)),
                    ),
                )
            )
            job_company_match_subq = select(Job.company_id).where(
                and_(
                    Job.status == "PUBLISHED",
                    Job.closed_at.is_(None),
                    or_(
                        Job.title.ilike(q),
                        Job.skills.ilike(q),
                        Job.job_skills.any(JobSkill.skill_name.ilike(q)),
                    ),
                )
            )

            conds.append(
                or_(
                    RecruiterProfile.company_name.ilike(q),
                    RecruiterProfile.primary_industry.ilike(q),
                    RecruiterProfile.headquarters_city_state.ilike(q),
                    RecruiterProfile.company_description.ilike(q),
                    RecruiterProfile.tagline.ilike(q),
                    RecruiterProfile.id.in_(job_match_subq),
                    RecruiterProfile.id.in_(job_company_match_subq),
                )
            )

        # 3. Industry filter
        if industry and industry.strip() and industry.strip().lower() not in ("all", "all industries"):
            conds.append(RecruiterProfile.primary_industry.ilike(f"%{industry.strip()}%"))

        # 4. Location filter
        if location and location.strip() and location.strip().lower() not in ("all", "all locations"):
            conds.append(RecruiterProfile.headquarters_city_state.ilike(f"%{location.strip()}%"))

        filter_clause = and_(*conds)

        # Correlated scalar subqueries for counting active published jobs and internships
        job_cnt_subq = (
            select(func.count(Job.id))
            .where(
                and_(
                    or_(Job.recruiter_id == RecruiterProfile.id, Job.company_id == RecruiterProfile.id),
                    Job.status == "PUBLISHED",
                    Job.closed_at.is_(None),
                )
            )
            .correlate(RecruiterProfile)
            .as_scalar()
        )

        intern_cnt_subq = (
            select(func.count(Internship.id))
            .where(
                and_(
                    Internship.company_id == RecruiterProfile.id,
                    Internship.status == "PUBLISHED",
                    Internship.closed_at.is_(None),
                )
            )
            .correlate(RecruiterProfile)
            .as_scalar()
        )

        # Count total matching distinct companies
        count_stmt = select(func.count(RecruiterProfile.id)).where(filter_clause)
        total = (await db.execute(count_stmt)).scalar() or 0

        # Query company profiles with subquery counts
        stmt = (
            select(
                RecruiterProfile,
                job_cnt_subq.label("open_jobs_count"),
                intern_cnt_subq.label("open_internships_count"),
            )
            .where(filter_clause)
            .order_by(job_cnt_subq.desc(), RecruiterProfile.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await db.execute(stmt)
        rows = result.all()

        profile_ids = [r[0].id for r in rows]

        # Batch load tech stack for these companies from their published jobs
        company_skills_map: Dict[str, List[str]] = {}
        if profile_ids:
            skills_stmt = (
                select(Job.recruiter_id, Job.company_id, JobSkill.skill_name)
                .join(JobSkill, Job.id == JobSkill.job_id)
                .where(
                    and_(
                        or_(Job.recruiter_id.in_(profile_ids), Job.company_id.in_(profile_ids)),
                        Job.status == "PUBLISHED",
                        Job.closed_at.is_(None),
                    )
                )
            )
            skills_res = await db.execute(skills_stmt)
            for rec_id, comp_id, skill_name in skills_res.all():
                target_ids = set(filter(None, [rec_id, comp_id]))
                for tid in target_ids:
                    if tid in profile_ids:
                        if tid not in company_skills_map:
                            company_skills_map[tid] = []
                        if skill_name and skill_name not in company_skills_map[tid]:
                            company_skills_map[tid].append(skill_name)

        items = []
        seen_names = set()
        for p, open_jobs, open_internships in rows:
            norm_name = p.company_name.strip().lower()
            # If a duplicate registration exists for the same company, preserve the primary one
            if norm_name in seen_names:
                continue
            seen_names.add(norm_name)

            skills_list = company_skills_map.get(p.id, [])[:5]

            # Logo URL resolution helper
            logo_url = None
            if p.company_logo_path:
                logo_url = p.company_logo_path if p.company_logo_path.startswith("http") else f"/{p.company_logo_path.lstrip('/')}"

            items.append({
                "id": p.id,
                "name": p.company_name,
                "company_name": p.company_name,
                "logo": logo_url or p.company_logo_path,
                "logo_url": logo_url or p.company_logo_path,
                "company_logo_path": p.company_logo_path,
                "industry": p.primary_industry,
                "location": p.headquarters_city_state,
                "tagline": p.tagline or p.company_description[:100] if p.company_description else None,
                "description": p.company_description,
                "website": p.company_website,
                "size": p.company_size,
                "employees": p.company_size,
                "company_size": p.company_size,
                "openJobs": open_jobs or 0,
                "open_jobs": open_jobs or 0,
                "open_jobs_count": open_jobs or 0,
                "openInternships": open_internships or 0,
                "open_internships": open_internships or 0,
                "open_internships_count": open_internships or 0,
                "rating": None,  # No fake ratings; real calculated or None
                "tech_stack": skills_list if skills_list else None,
                "verified": True,
            })

        # Adjust total if duplicate names were deduplicated
        final_total = max(total - (len(rows) - len(items)), len(items))

        return items, final_total

    @staticmethod
    async def get_company_by_id(
        db: AsyncSession, company_id: str
    ) -> Optional[RecruiterProfile]:
        """Fetch RecruiterProfile by ID."""
        stmt = select(RecruiterProfile).where(RecruiterProfile.id == company_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()


    @staticmethod
    async def get_admin_companies(
        db: AsyncSession,
        status_filter: Optional[str] = "ALL",
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Fetch company verifications queue for Administrator review."""
        conds = []

        if status_filter and status_filter.upper() != "ALL":
            norm = status_filter.upper().strip()
            if norm in ("PENDING", "PENDING_APPROVAL"):
                conds.append(
                    or_(
                        RecruiterProfile.status == "PENDING_APPROVAL",
                        RecruiterProfile.status == "PENDING",
                    )
                )
            elif norm in ("VERIFIED", "APPROVED"):
                conds.append(
                    or_(
                        RecruiterProfile.status == "APPROVED",
                        RecruiterProfile.status == "VERIFIED",
                    )
                )
            elif norm == "REJECTED":
                conds.append(RecruiterProfile.status == "REJECTED")

        if search and search.strip():
            q = f"%{search.strip()}%"
            conds.append(
                or_(
                    RecruiterProfile.company_name.ilike(q),
                    RecruiterProfile.recruiter_name.ilike(q),
                    RecruiterProfile.work_email.ilike(q),
                    RecruiterProfile.primary_industry.ilike(q),
                    RecruiterProfile.headquarters_city_state.ilike(q),
                )
            )

        filter_clause = and_(*conds) if conds else None

        count_stmt = select(func.count(RecruiterProfile.id))
        if filter_clause is not None:
            count_stmt = count_stmt.where(filter_clause)
        total = (await db.execute(count_stmt)).scalar() or 0

        stmt = select(RecruiterProfile)
        if filter_clause is not None:
            stmt = stmt.where(filter_clause)
        stmt = stmt.order_by(RecruiterProfile.created_at.desc()).offset((page - 1) * page_size).limit(page_size)

        result = await db.execute(stmt)
        profiles = result.scalars().all()

        items = []
        for p in profiles:
            job_cnt_stmt = select(func.count(Job.id)).where(
                and_(
                    or_(Job.recruiter_id == p.id, Job.company_id == p.id),
                    Job.status == "PUBLISHED",
                )
            )
            open_jobs = (await db.execute(job_cnt_stmt)).scalar() or 0

            # Verification status label
            v_status = "PENDING"
            if p.status in ("APPROVED", "VERIFIED"):
                v_status = "VERIFIED"
            elif p.status == "REJECTED":
                v_status = "REJECTED"

            items.append({
                "id": p.id,
                "name": p.company_name,
                "company_name": p.company_name,
                "recruiter_name": p.recruiter_name,
                "recruiter": p.recruiter_name,
                "recruiter_email": p.work_email,
                "recruiter_phone": p.mobile_phone,
                "designation": p.designation,
                "industry": p.primary_industry,
                "company_size": p.company_size,
                "location": p.headquarters_city_state,
                "address": p.registered_office_address,
                "website": p.company_website,
                "description": p.company_description,
                "status": p.status,
                "verification_status": v_status,
                "verificationStatus": v_status,
                "rejection_reason": p.rejection_reason,
                "rejectionReason": p.rejection_reason,
                "submitted_at": p.submitted_at.strftime("%Y-%m-%d %H:%M:%S") if p.submitted_at else (p.created_at.strftime("%Y-%m-%d %H:%M:%S") if p.created_at else None),
                "reviewed_at": p.reviewed_at.strftime("%Y-%m-%d %H:%M:%S") if p.reviewed_at else None,
                "reviewed_by": p.reviewed_by,
                "incorporation_document_path": p.incorporation_document_path,
                "recruiter_authorization_document_path": p.recruiter_authorization_document_path,
                "company_logo_path": p.company_logo_path,
                "open_jobs": open_jobs,
                "openJobs": open_jobs,
            })

        return items, total
