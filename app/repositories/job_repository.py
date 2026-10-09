import uuid
import re
import json
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy import select, func, or_, and_, desc
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job, JobSkill
from app.models.application import CandidateApplication
from app.models.interview import Interview
from app.models.recruiter import RecruiterProfile
from app.models.internship import AuditLog
from app.models.user import User


class JobRepository:
    """
    Database repository layer for Job requisitions, normalized job skills,
    pipeline count aggregations, and multi-tenant isolation.
    """

    @staticmethod
    async def get_recruiter_profile_by_user_id(
        db: AsyncSession, user_id: str
    ) -> Optional[RecruiterProfile]:
        """Fetch recruiter profile from user ID."""
        stmt = select(RecruiterProfile).where(RecruiterProfile.user_id == user_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def generate_next_job_number(db: AsyncSession) -> Tuple[str, str]:
        """
        Generate sequential unique job IDs and requisition numbers.
        Returns (job_id, job_number), e.g. ('job-106', 'JOB-106').
        """
        stmt = select(Job.job_number, Job.job_id)
        result = await db.execute(stmt)
        rows = result.all()

        max_num = 100
        for jnum, jid in rows:
            for val in (jnum, jid):
                if val:
                    match = re.search(r'(?:job|JOB)-(\d+)', str(val))
                    if match:
                        num = int(match.group(1))
                        if num > max_num:
                            max_num = num

        next_seq = max_num + 1
        return f"job-{next_seq}", f"JOB-{next_seq}"

    @staticmethod
    async def get_pipeline_counts(
        db: AsyncSession, job_id: str, job_number: Optional[str] = None, primary_id: Optional[str] = None
    ) -> Tuple[int, int, int]:
        """
        Query real database counts: (applicants_count, shortlisted_count, interviews_count).
        """
        ids = {job_id, job_id.lower(), job_id.upper()}
        if job_number:
            ids.update([job_number, job_number.lower(), job_number.upper()])
        if primary_id:
            ids.add(primary_id)

        # 1. Total applicants
        apps_stmt = select(func.count(CandidateApplication.id)).where(
            CandidateApplication.job_id.in_(list(ids))
        )
        applicants_count = (await db.execute(apps_stmt)).scalar() or 0

        # 2. Shortlisted applicants
        short_stmt = select(func.count(CandidateApplication.id)).where(
            and_(
                CandidateApplication.job_id.in_(list(ids)),
                CandidateApplication.status == "SHORTLISTED",
            )
        )
        shortlisted_count = (await db.execute(short_stmt)).scalar() or 0

        # 3. Interviews
        int_stmt = select(func.count(Interview.id)).where(
            Interview.job_id.in_(list(ids))
        )
        interviews_count = (await db.execute(int_stmt)).scalar() or 0

        return applicants_count, shortlisted_count, interviews_count

    @staticmethod
    async def get_job_skills(db: AsyncSession, job_id: str) -> List[str]:
        """Fetch list of normalized skills for a job."""
        stmt = (
            select(JobSkill.skill_name)
            .where(JobSkill.job_id == job_id)
            .order_by(JobSkill.created_at.asc())
        )
        res = await db.execute(stmt)
        return [row[0] for row in res.all()]

    @staticmethod
    async def save_job_skills(db: AsyncSession, job_id: str, skills: List[str]):
        """Persist normalized skill records for a job."""
        now = datetime.now(timezone.utc)
        for s in skills:
            clean = s.strip()
            if clean:
                skill_rec = JobSkill(
                    id=f"skill-{uuid.uuid4().hex[:10]}",
                    job_id=job_id,
                    skill_name=clean,
                    created_at=now,
                )
                db.add(skill_rec)

    @staticmethod
    async def get_recruiter_jobs(
        db: AsyncSession,
        recruiter_id: str,
        company_id: Optional[str] = None,
        status_filter: Optional[str] = "ALL",
        department: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Fetch paginated jobs belonging to authenticated recruiter/company.
        """
        owner_clauses = [Job.recruiter_id == recruiter_id]
        if company_id:
            owner_clauses.append(Job.company_id == company_id)
        base_conds = [or_(*owner_clauses)]

        # Status filter
        if status_filter:
            norm_status = status_filter.upper().strip()
            if norm_status in ("ACTIVE", "PUBLISHED"):
                base_conds.append(Job.status == "PUBLISHED")
            elif norm_status == "PENDING":
                base_conds.append(Job.status == "PENDING")
            elif norm_status == "DRAFT":
                base_conds.append(Job.status == "DRAFT")
            elif norm_status == "CLOSED":
                base_conds.append(Job.status == "CLOSED")
            elif norm_status == "REJECTED":
                base_conds.append(Job.status == "REJECTED")

        # Department filter
        if department and department.strip() and department.upper() != "ALL":
            base_conds.append(Job.department == department.strip())

        # Search filter
        if search and search.strip():
            q = f"%{search.strip()}%"
            base_conds.append(
                or_(
                    Job.title.ilike(q),
                    Job.job_number.ilike(q),
                    Job.job_id.ilike(q),
                    Job.department.ilike(q),
                    Job.location.ilike(q),
                    Job.skills.ilike(q),
                )
            )

        filter_clause = and_(*base_conds)

        # Count total
        count_stmt = select(func.count(Job.id)).where(filter_clause)
        total = (await db.execute(count_stmt)).scalar() or 0

        # Query items
        stmt = (
            select(Job)
            .options(selectinload(Job.job_skills), selectinload(Job.recruiter))
            .where(filter_clause)
            .order_by(Job.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await db.execute(stmt)
        jobs = result.scalars().all()

        items = []
        for j in jobs:
            app_cnt, short_cnt, int_cnt = await JobRepository.get_pipeline_counts(
                db, j.job_id, j.job_number, j.id
            )
            # Retrieve skills
            skills_list = [s.skill_name for s in j.job_skills]
            if not skills_list and j.skills:
                skills_list = [s.strip() for s in j.skills.split(",") if s.strip()]

            items.append({
                "id": j.id,
                "job_id": j.job_id,
                "job_number": j.job_number or j.job_id.upper(),
                "company_name": j.company_name,
                "company_id": j.company_id or j.recruiter_id,
                "title": j.title,
                "department": j.department or "Core Engineering",
                "job_type": j.job_type,
                "employment_type": j.job_type,
                "work_mode": j.work_mode,
                "workMode": j.work_mode,
                "location": j.location,
                "experience": j.experience or "3-5 years",
                "experience_level": j.experience or "3-5 years",
                "salary": j.salary,
                "salary_min": j.salary_min,
                "salary_max": j.salary_max,
                "salary_currency": j.salary_currency or "INR",
                "openings": j.openings,
                "number_of_openings": j.openings,
                "status": j.status,
                "description": j.description,
                "job_summary": j.description,
                "responsibilities": j.responsibilities,
                "key_responsibilities": j.responsibilities,
                "requirements": j.requirements,
                "technical_requirements": j.requirements,
                "qualifications": j.qualifications,
                "educational_qualifications": j.qualifications,
                "skills": skills_list,
                "deadline": j.deadline,
                "application_deadline": j.deadline,
                "posted_at": j.posted_at.strftime("%Y-%m-%d %H:%M:%S") if j.posted_at else None,
                "createdAt": j.posted_at.strftime("%Y-%m-%d") if j.posted_at else (j.created_at.strftime("%Y-%m-%d") if j.created_at else None),
                "closed_at": j.closed_at.strftime("%Y-%m-%d %H:%M:%S") if j.closed_at else None,
                "created_at": j.created_at.strftime("%Y-%m-%d %H:%M:%S") if j.created_at else None,
                "updated_at": j.updated_at.strftime("%Y-%m-%d %H:%M:%S") if j.updated_at else None,
                "rejection_reason": j.rejection_reason,
                "approved_by": j.approved_by,
                "approved_at": j.approved_at.strftime("%Y-%m-%d %H:%M:%S") if j.approved_at else None,
                "applicantsCount": app_cnt,
                "applicant_count": app_cnt,
                "shortlistedCount": short_cnt,
                "shortlisted_count": short_cnt,
                "interviewsCount": int_cnt,
                "interview_count": int_cnt,
            })

        return items, total

    @staticmethod
    async def get_admin_jobs(
        db: AsyncSession,
        status_filter: Optional[str] = "ALL",
        department: Optional[str] = None,
        search: Optional[str] = None,
        company: Optional[str] = None,
        company_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Cross-company governance listing for administrators.
        """
        conds = []
        if status_filter and status_filter.upper() != "ALL":
            conds.append(Job.status == status_filter.upper())

        if department and department.strip() and department.upper() != "ALL":
            conds.append(Job.department == department.strip())

        if company and company.strip() and company.strip().upper() != "ALL":
            clean_comp = company.strip()
            conds.append(
                or_(
                    Job.company_name.ilike(f"%{clean_comp}%"),
                    RecruiterProfile.company_name.ilike(f"%{clean_comp}%"),
                )
            )

        if company_id and company_id.strip() and company_id.strip().upper() != "ALL":
            clean_id = company_id.strip()
            conds.append(
                or_(
                    Job.company_id == clean_id,
                    Job.recruiter_id == clean_id,
                )
            )

        if search and search.strip():
            q = f"%{search.strip()}%"
            conds.append(
                or_(
                    Job.title.ilike(q),
                    Job.job_number.ilike(q),
                    Job.job_id.ilike(q),
                    Job.department.ilike(q),
                    Job.location.ilike(q),
                    Job.company_name.ilike(q),
                    Job.skills.ilike(q),
                )
            )

        filter_clause = and_(*conds) if conds else True

        count_stmt = (
            select(func.count(Job.id))
            .join(RecruiterProfile, Job.recruiter_id == RecruiterProfile.id, isouter=True)
            .where(filter_clause)
        )
        total = (await db.execute(count_stmt)).scalar() or 0

        stmt = (
            select(Job, RecruiterProfile)
            .join(RecruiterProfile, Job.recruiter_id == RecruiterProfile.id, isouter=True)
            .options(selectinload(Job.job_skills))
            .where(filter_clause)
            .order_by(Job.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await db.execute(stmt)
        rows = result.all()

        items = []
        for job, rec in rows:
            app_cnt, short_cnt, int_cnt = await JobRepository.get_pipeline_counts(
                db, job.job_id, job.job_number, job.id
            )
            skills_list = [s.skill_name for s in job.job_skills]
            if not skills_list and job.skills:
                skills_list = [s.strip() for s in job.skills.split(",") if s.strip()]

            company_obj = {
                "id": rec.id if rec else job.recruiter_id,
                "name": job.company_name,
                "verified": True,
                "logo_url": rec.company_logo_path if rec else None,
            }
            items.append({
                "id": job.id,
                "job_id": job.job_id,
                "job_number": job.job_number or job.job_id.upper(),
                "title": job.title,
                "company_id": rec.id if rec else job.recruiter_id,
                "company_name": job.company_name,
                "company": company_obj,
                "company_verified": True,
                "company_logo": rec.company_logo_path if rec else None,
                "company_logo_path": rec.company_logo_path if rec else None,
                "recruiter_name": rec.recruiter_name if rec else None,
                "recruiter": rec.recruiter_name if rec else None,
                "recruiter_email": rec.work_email if rec else None,
                "recruiter_phone": rec.mobile_phone if rec else None,

                "department": job.department or "Core Engineering",
                "job_type": job.job_type,
                "employment_type": job.job_type,
                "work_mode": job.work_mode,
                "workMode": job.work_mode,
                "location": job.location,
                "experience": job.experience or "3-5 years",
                "experience_level": job.experience or "3-5 years",
                "salary": job.salary,
                "salary_min": job.salary_min,
                "salary_max": job.salary_max,
                "salary_currency": job.salary_currency or "INR",
                "openings": job.openings,
                "number_of_openings": job.openings,
                "status": job.status,
                "description": job.description,
                "job_summary": job.description,
                "responsibilities": job.responsibilities,
                "key_responsibilities": job.responsibilities,
                "requirements": job.requirements,
                "technical_requirements": job.requirements,
                "qualifications": job.qualifications,
                "educational_qualifications": job.qualifications,
                "skills": skills_list,
                "deadline": job.deadline,
                "application_deadline": job.deadline,
                "posted_at": job.posted_at.strftime("%Y-%m-%d %H:%M:%S") if job.posted_at else None,
                "createdAt": job.posted_at.strftime("%Y-%m-%d") if job.posted_at else (job.created_at.strftime("%Y-%m-%d") if job.created_at else None),
                "closed_at": job.closed_at.strftime("%Y-%m-%d %H:%M:%S") if job.closed_at else None,
                "created_at": job.created_at.strftime("%Y-%m-%d %H:%M:%S") if job.created_at else None,
                "updated_at": job.updated_at.strftime("%Y-%m-%d %H:%M:%S") if job.updated_at else None,
                "rejection_reason": job.rejection_reason,
                "approved_by": job.approved_by,
                "approved_at": job.approved_at.strftime("%Y-%m-%d %H:%M:%S") if job.approved_at else None,
                "applicantsCount": app_cnt,
                "applicant_count": app_cnt,
                "shortlistedCount": short_cnt,
                "shortlisted_count": short_cnt,
                "interviewsCount": int_cnt,
                "interview_count": int_cnt,
            })

        return items, total

    @staticmethod
    async def get_published_jobs(
        db: AsyncSession,
        search: Optional[str] = None,
        department: Optional[str] = None,
        location: Optional[str] = None,
        experience_level: Optional[str] = None,
        salary_min: Optional[int] = None,
        salary_max: Optional[int] = None,
        salary_range: Optional[str] = None,
        work_mode: Optional[str] = None,
        employment_type: Optional[str] = None,
        required_skill: Optional[str] = None,
        industry_sector: Optional[str] = None,
        sort: Optional[str] = "relevance",
        page: int = 1,
        page_size: int = 12,
        current_user: Optional[User] = None,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Public & candidate facing jobs listing.
        Strictly returns only PUBLISHED jobs from verified/approved companies.
        Performs database-side filtering, sorting, and pagination.
        """
        conds = [
            Job.status == "PUBLISHED",
            Job.closed_at.is_(None),
            Job.recruiter.has(RecruiterProfile.status.in_(["APPROVED", "VERIFIED"]))
        ]


        # 1. Location filter
        if location and location.strip() and location.strip().lower() not in ("all locations", "all"):
            conds.append(Job.location.ilike(f"%{location.strip()}%"))

        # 2. Experience level filter
        if experience_level and experience_level.strip() and experience_level.strip().lower() not in ("all experience", "all"):
            exp_lower = experience_level.strip().lower()
            if "fresher" in exp_lower or "0-1" in exp_lower:
                conds.append(or_(Job.experience.ilike("%0%"), Job.experience.ilike("%1%"), Job.experience.ilike("%fresher%")))
            elif "1-3" in exp_lower:
                conds.append(or_(Job.experience.ilike("%1%"), Job.experience.ilike("%2%"), Job.experience.ilike("%3%")))
            elif "3-5" in exp_lower:
                conds.append(or_(Job.experience.ilike("%3%"), Job.experience.ilike("%4%"), Job.experience.ilike("%5%")))
            elif "5-8" in exp_lower:
                conds.append(or_(Job.experience.ilike("%5%"), Job.experience.ilike("%6%"), Job.experience.ilike("%7%"), Job.experience.ilike("%8%")))
            elif "8" in exp_lower or "+" in exp_lower:
                conds.append(or_(Job.experience.ilike("%8%"), Job.experience.ilike("%9%"), Job.experience.ilike("%10%"), Job.experience.ilike("%+%")))
            else:
                conds.append(Job.experience.ilike(f"%{exp_lower}%"))

        # 3. Salary filter (numeric or parsed range string)
        min_ctc = None
        max_ctc = None
        if salary_min is not None:
            min_ctc = salary_min * 100000 if salary_min < 1000 else salary_min
        if salary_max is not None:
            max_ctc = salary_max * 100000 if salary_max < 1000 else salary_max

        if salary_range and salary_range.strip() and salary_range.strip().lower() not in ("all salaries", "all"):
            nums = [int(n) for n in re.findall(r'\d+', salary_range)]
            if len(nums) >= 2:
                min_ctc = nums[0] * 100000
                max_ctc = nums[1] * 100000
            elif len(nums) == 1:
                min_ctc = nums[0] * 100000

        if min_ctc is not None:
            conds.append(
                or_(
                    Job.salary_max >= min_ctc,
                    Job.salary_min >= min_ctc,
                    and_(Job.salary_min == None, Job.salary_max == None)
                )
            )
        if max_ctc is not None:
            conds.append(
                or_(
                    Job.salary_min <= max_ctc,
                    Job.salary_max <= max_ctc,
                    and_(Job.salary_min == None, Job.salary_max == None)
                )
            )

        # 4. Work mode filter
        if work_mode and work_mode.strip() and work_mode.strip().lower() not in ("all modes", "all"):
            conds.append(Job.work_mode.ilike(f"%{work_mode.strip()}%"))

        # 5. Employment type filter
        if employment_type and employment_type.strip() and employment_type.strip().lower() not in ("all types", "all"):
            conds.append(Job.job_type.ilike(f"%{employment_type.strip()}%"))

        # 6. Skill filter
        if required_skill and required_skill.strip() and required_skill.strip().lower() not in ("all skills", "all"):
            s_term = required_skill.strip()
            conds.append(
                or_(
                    Job.skills.ilike(f"%{s_term}%"),
                    Job.job_skills.any(JobSkill.skill_name.ilike(f"%{s_term}%"))
                )
            )

        # 7. Industry / Department filter
        effective_industry = industry_sector or department
        if effective_industry and effective_industry.strip() and effective_industry.strip().lower() not in ("all industries", "all"):
            ind_term = effective_industry.strip()
            conds.append(
                or_(
                    Job.department.ilike(f"%{ind_term}%"),
                    Job.recruiter.has(RecruiterProfile.primary_industry.ilike(f"%{ind_term}%"))
                )
            )

        # 8. Search query across title, description, skills, company name, department, industry
        if search and search.strip():
            q = f"%{search.strip()}%"
            conds.append(
                or_(
                    Job.title.ilike(q),
                    Job.description.ilike(q),
                    Job.location.ilike(q),
                    Job.company_name.ilike(q),
                    Job.skills.ilike(q),
                    Job.department.ilike(q),
                    Job.recruiter.has(RecruiterProfile.primary_industry.ilike(q)),
                    Job.job_skills.any(JobSkill.skill_name.ilike(q)),
                )
            )

        filter_clause = and_(*conds)

        count_stmt = select(func.count(Job.id)).where(filter_clause)
        total = (await db.execute(count_stmt)).scalar() or 0

        # Sorting
        sort_val = (sort or "relevance").lower()
        if sort_val in ("salaryhigh", "salary_high"):
            order_clause = [Job.salary_max.desc(), Job.salary_min.desc(), Job.posted_at.desc(), Job.created_at.desc()]
        elif sort_val in ("salarylow", "salary_low"):
            order_clause = [Job.salary_min.asc(), Job.salary_max.asc(), Job.posted_at.desc(), Job.created_at.desc()]
        elif sort_val in ("oldest",):
            order_clause = [Job.created_at.asc()]
        elif sort_val in ("newest", "latest"):
            order_clause = [Job.posted_at.desc(), Job.created_at.desc()]
        else:
            order_clause = [Job.posted_at.desc(), Job.created_at.desc()]

        stmt = (
            select(Job)
            .options(selectinload(Job.job_skills), selectinload(Job.recruiter))
            .where(filter_clause)
            .order_by(*order_clause)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await db.execute(stmt)
        jobs = result.scalars().all()

        # Candidate personalization
        saved_job_ids = set()
        applied_job_ids = set()
        cand_skills = []
        if current_user and current_user.role == "CANDIDATE":
            from app.models.candidate import CandidateProfile
            from app.models.saved_job import SavedJob
            from app.models.application import CandidateApplication
            from app.models.candidate_profile_details import CandidateSkill

            cand_res = await db.execute(
                select(CandidateProfile).where(CandidateProfile.user_id == current_user.id)
            )
            profile = cand_res.scalar_one_or_none()
            if profile:
                s_res = await db.execute(
                    select(SavedJob.job_id).where(SavedJob.candidate_profile_id == profile.id)
                )
                saved_job_ids = {str(r[0]) for r in s_res.fetchall()}

                a_res = await db.execute(
                    select(CandidateApplication.job_id).where(CandidateApplication.candidate_profile_id == profile.id)
                )
                applied_job_ids = {str(r[0]) for r in a_res.fetchall()}

                sk_res = await db.execute(
                    select(CandidateSkill.skill_name).where(CandidateSkill.candidate_profile_id == profile.id)
                )
                cand_skills = [r[0].lower().strip() for r in sk_res.fetchall() if r[0]]

        items = []
        for j in jobs:
            app_cnt, short_cnt, int_cnt = await JobRepository.get_pipeline_counts(
                db, j.job_id, j.job_number, j.id
            )
            skills_list = [s.skill_name for s in j.job_skills]
            if not skills_list and j.skills:
                skills_list = [s.strip() for s in j.skills.split(",") if s.strip()]

            is_saved = bool({str(j.id), str(j.job_id), str(j.job_number or "")} & saved_job_ids)
            has_applied = bool({str(j.id), str(j.job_id), str(j.job_number or "")} & applied_job_ids)

            match_score = None
            if current_user and current_user.role == "CANDIDATE":
                if cand_skills and skills_list:
                    job_skills_lower = [s.lower().strip() for s in skills_list]
                    matches = [s for s in job_skills_lower if any(cs in s or s in cs for cs in cand_skills)]
                    if len(matches) >= 3:
                        match_score = 96
                    elif len(matches) == 2:
                        match_score = 92
                    elif len(matches) == 1:
                        match_score = 88
                    else:
                        match_score = 80
                else:
                    match_score = 85

            company_obj = {
                "id": j.company_id or j.recruiter_id,
                "name": j.company_name,
                "logo_url": j.recruiter.company_logo_path if j.recruiter else None,
                "verified": True,
            }
            industry_val = (
                j.recruiter.primary_industry
                if (j.recruiter and j.recruiter.primary_industry)
                else (j.department or "Information Technology")
            )

            items.append({
                "id": j.id,
                "job_id": j.job_id,
                "job_number": j.job_number or j.job_id.upper(),
                "company_name": j.company_name,
                "company_id": j.company_id or j.recruiter_id,
                "company": company_obj,
                "company_verified": True,
                "company_logo": j.recruiter.company_logo_path if j.recruiter else None,
                "company_logo_path": j.recruiter.company_logo_path if j.recruiter else None,
                "title": j.title,
                "department": j.department or "Core Engineering",
                "industry": industry_val,
                "job_type": j.job_type,
                "employment_type": j.job_type,
                "work_mode": j.work_mode,
                "workMode": j.work_mode,
                "location": j.location,
                "experience": j.experience or "3-5 years",
                "experience_level": j.experience or "3-5 years",
                "salary": j.salary,
                "salary_min": j.salary_min,
                "salary_max": j.salary_max,
                "salary_currency": j.salary_currency or "INR",
                "openings": j.openings,
                "number_of_openings": j.openings,
                "status": j.status,
                "description": j.description,
                "job_summary": j.description,
                "responsibilities": j.responsibilities,
                "key_responsibilities": j.responsibilities,
                "requirements": j.requirements,
                "technical_requirements": j.requirements,
                "qualifications": j.qualifications,
                "educational_qualifications": j.qualifications,
                "skills": skills_list,
                "tags": skills_list,
                "deadline": j.deadline,
                "application_deadline": j.deadline,
                "posted_at": j.posted_at.strftime("%Y-%m-%d %H:%M:%S") if j.posted_at else None,
                "createdAt": j.posted_at.strftime("%Y-%m-%d") if j.posted_at else (j.created_at.strftime("%Y-%m-%d") if j.created_at else None),
                "closed_at": j.closed_at.strftime("%Y-%m-%d %H:%M:%S") if j.closed_at else None,
                "created_at": j.created_at.strftime("%Y-%m-%d %H:%M:%S") if j.created_at else None,
                "updated_at": j.updated_at.strftime("%Y-%m-%d %H:%M:%S") if j.updated_at else None,
                "applicantsCount": app_cnt,
                "applicant_count": app_cnt,
                "shortlistedCount": short_cnt,
                "shortlisted_count": short_cnt,
                "interviewsCount": int_cnt,
                "interview_count": int_cnt,
                "is_saved": is_saved,
                "has_applied": has_applied,
                "match_score": match_score,
                "is_active": j.status == "PUBLISHED",
            })

        return items, total

    @staticmethod
    async def get_job_by_id(db: AsyncSession, identifier: str) -> Optional[Job]:
        """Fetch job by primary UUID, job_id, or job_number."""
        stmt = (
            select(Job)
            .options(selectinload(Job.job_skills), selectinload(Job.recruiter))
            .where(
                or_(
                    Job.id == identifier,
                    Job.job_id == identifier,
                    Job.job_number == identifier,
                    Job.job_id == identifier.lower(),
                    Job.job_number == identifier.upper(),
                )
            )
        )
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    @staticmethod
    async def create_audit_log(
        db: AsyncSession,
        actor: str,
        action: str,
        entity: str,
        entity_id: str,
        metadata_json: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        """Create audit log entry."""
        log = AuditLog(
            id=f"audit-{uuid.uuid4().hex[:10]}",
            actor=actor,
            action=action,
            entity=entity,
            entity_id=entity_id,
            metadata_json=json.dumps(metadata_json) if metadata_json else None,
            timestamp=datetime.now(timezone.utc),
        )
        db.add(log)
        await db.commit()
        return log
