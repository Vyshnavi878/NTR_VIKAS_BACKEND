import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Tuple
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.job import Job, JobSkill
from app.models.recruiter import RecruiterProfile
from app.repositories.job_repository import JobRepository
from app.schemas.job import (
    JobCreate,
    JobUpdate,
    JobRead,
    PaginatedJobResponse,
    AdminJobDetail,
)


class JobService:
    """
    Business service layer for job postings, draft saving, governance approvals,
    pipeline statistics, and public candidate access.
    """

    @classmethod
    async def get_recruiter_jobs(
        cls,
        db: AsyncSession,
        current_user: User,
        status_filter: Optional[str] = "ALL",
        department: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> PaginatedJobResponse:
        """Fetch recruiter's jobs with multi-tenant isolation."""
        if current_user.role != "RECRUITER":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Recruiter account required to view recruiter job postings.",
            )

        profile = await JobRepository.get_recruiter_profile_by_user_id(db, current_user.id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recruiter profile not found. Complete your organization onboarding.",
            )

        items_data, total = await JobRepository.get_recruiter_jobs(
            db=db,
            recruiter_id=profile.id,
            company_id=profile.id,
            status_filter=status_filter,
            department=department,
            search=search,
            page=page,
            page_size=page_size,
        )

        items = [JobRead(**item) for item in items_data]
        total_pages = (total + page_size - 1) // page_size if total > 0 else 1

        return PaginatedJobResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    @classmethod
    async def create_job(
        cls,
        db: AsyncSession,
        current_user: User,
        data: JobCreate,
        as_draft: bool = False,
    ) -> JobRead:
        """
        Create a new job posting.
        If as_draft is True, status is DRAFT.
        Otherwise, status is strictly set to PENDING for administrator approval.
        """
        if current_user.role != "RECRUITER":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Recruiter account required to create job postings.",
            )

        profile = await JobRepository.get_recruiter_profile_by_user_id(db, current_user.id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recruiter profile not found. Please complete organization registration first.",
            )

        # Basic validations
        if not data.title or not data.title.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Job Title is mandatory.",
            )

        if not as_draft:
            # Full validation for approval submission
            desc = data.description or data.job_summary
            if not desc or not desc.strip():
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Job Summary / Overview is required for approval submission.",
                )

        # Load Platform Settings
        from app.repositories.platform_settings_repository import PlatformSettingsRepository
        settings = await PlatformSettingsRepository.get_settings(db)

        # 1. Check Mandatory Recruiter Legal Verification
        if settings and settings.mandatory_recruiter_legal_verification and not as_draft:
            if profile.status and profile.status.upper() in ["PENDING_APPROVAL", "REJECTED"]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Mandatory Legal Verification: Company COI & GST verification must be approved before posting vacancies.",
                )

        # 2. Check Strict Zero-Fee Candidate Rule
        if settings and settings.strict_zero_fee_candidate_rule:
            combined_text = f"{data.title or ''} {data.description or ''} {data.responsibilities or ''} {data.requirements or ''}".lower()
            fee_keywords = ["registration fee", "security deposit", "application fee", "training fee", "processing fee", "caution deposit"]
            for kw in fee_keywords:
                if kw in combined_text:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=f"Job posting violates the Zero-Fee Candidate Rule ('{kw}' detected). Recruiters are strictly prohibited from demanding fees from candidates.",
                    )

        now = datetime.now(timezone.utc)
        job_id_str, job_number_str = await JobRepository.generate_next_job_number(db)
        primary_id = str(uuid.uuid4())

        # 3. Check Pre-Publish Job Moderation Queue
        if as_draft:
            initial_status = "DRAFT"
        elif settings and not settings.pre_publish_job_moderation_queue:
            initial_status = "PUBLISHED"
        else:
            initial_status = "PENDING"

        # Resolve aliases
        dept = data.department or "Core Engineering"
        emp_type = data.job_type or data.employment_type or "Full-time"
        work_mode = data.work_mode or data.workplace_policy or "Hybrid"
        loc = data.location or "Bengaluru, Karnataka"
        exp = data.experience or data.experience_level or "3-5 years"
        num_openings = data.openings or data.number_of_openings or 1
        app_deadline = data.deadline or data.application_deadline
        job_desc = data.description or data.job_summary
        resp = data.responsibilities or data.key_responsibilities
        reqs = data.requirements or data.technical_requirements
        quals = data.qualifications or data.educational_qualifications

        # Normalize salary display
        salary_str = data.salary
        if not salary_str and data.salary_min and data.salary_max:
            salary_str = f"₹{data.salary_min:,} - ₹{data.salary_max:,} / year"

        # Skills list
        skills_list = data.skills or []
        skills_csv = ", ".join(skills_list) if skills_list else None

        new_job = Job(
            id=primary_id,
            job_id=job_id_str,
            job_number=job_number_str,
            recruiter_id=profile.id,
            company_id=profile.id,
            created_by=current_user.email,
            company_name=profile.company_name or "Partner Employer",
            title=data.title.strip(),
            department=dept,
            job_type=emp_type,
            work_mode=work_mode,
            location=loc,
            experience=exp,
            salary=salary_str,
            salary_min=data.salary_min,
            salary_max=data.salary_max,
            salary_currency=data.salary_currency or "INR",
            openings=num_openings,
            status=initial_status,
            description=job_desc,
            responsibilities=resp,
            requirements=reqs,
            qualifications=quals,
            skills=skills_csv,
            deadline=app_deadline,
            created_at=now,
            updated_at=now,
        )
        db.add(new_job)
        await db.commit()

        # Save normalized skills
        if skills_list:
            await JobRepository.save_job_skills(db, new_job.id, skills_list)
            await db.commit()

        # Audit log
        action_name = "JOB_SAVED_AS_DRAFT" if as_draft else "JOB_SUBMITTED_FOR_APPROVAL"
        await JobRepository.create_audit_log(
            db=db,
            actor=current_user.email,
            action=action_name,
            entity="JOB",
            entity_id=new_job.id,
            metadata_json={
                "job_number": job_number_str,
                "title": new_job.title,
                "status": initial_status,
            },
        )

        # Recruiter notification
        try:
            from app.models.notification import Notification
            notif_msg = (
                f"Job requisition '{new_job.title}' saved as draft."
                if as_draft
                else f"Job requisition '{new_job.title}' submitted for Admin review. Status: PENDING."
            )
            notif = Notification(
                id=f"notif-{uuid.uuid4().hex[:10]}",
                user_id=current_user.id,
                title="Job Requisition Submitted" if not as_draft else "Job Draft Saved",
                message=notif_msg,
                type="JOB",
                read=False,
                created_at=now,
            )
            db.add(notif)
            await db.commit()
        except Exception:
            pass

        return JobRead(
            id=new_job.id,
            job_id=new_job.job_id,
            job_number=new_job.job_number,
            company_name=new_job.company_name,
            company_id=new_job.company_id,
            title=new_job.title,
            department=new_job.department,
            job_type=new_job.job_type,
            employment_type=new_job.job_type,
            work_mode=new_job.work_mode,
            workMode=new_job.work_mode,
            location=new_job.location,
            experience=new_job.experience,
            experience_level=new_job.experience,
            salary=new_job.salary,
            salary_min=new_job.salary_min,
            salary_max=new_job.salary_max,
            salary_currency=new_job.salary_currency,
            openings=new_job.openings,
            number_of_openings=new_job.openings,
            status=new_job.status,
            description=new_job.description,
            job_summary=new_job.description,
            responsibilities=new_job.responsibilities,
            key_responsibilities=new_job.responsibilities,
            requirements=new_job.requirements,
            technical_requirements=new_job.requirements,
            qualifications=new_job.qualifications,
            educational_qualifications=new_job.qualifications,
            skills=skills_list,
            deadline=new_job.deadline,
            application_deadline=new_job.deadline,
            posted_at=None,
            createdAt=new_job.created_at.strftime("%Y-%m-%d"),
            closed_at=None,
            created_at=new_job.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            updated_at=new_job.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
            applicantsCount=0,
            applicant_count=0,
            shortlistedCount=0,
            shortlisted_count=0,
            interviewsCount=0,
            interview_count=0,
        )

    @classmethod
    async def close_job(
        cls, db: AsyncSession, current_user: User, job_identifier: str
    ) -> JobRead:
        """Close an active job posting."""
        job = await JobRepository.get_job_by_id(db, job_identifier)
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found.",
            )

        # Check ownership
        if current_user.role != "ADMIN":
            profile = await JobRepository.get_recruiter_profile_by_user_id(db, current_user.id)
            if not profile or (job.recruiter_id != profile.id and job.company_id != profile.id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You are not authorized to close another organization's job.",
                )

        now = datetime.now(timezone.utc)
        job.status = "CLOSED"
        job.closed_at = now
        job.updated_at = now
        await db.commit()

        await JobRepository.create_audit_log(
            db=db,
            actor=current_user.email,
            action="JOB_CLOSED",
            entity="JOB",
            entity_id=job.id,
            metadata_json={"job_number": job.job_number, "status": "CLOSED"},
        )

        app_cnt, short_cnt, int_cnt = await JobRepository.get_pipeline_counts(
            db, job.job_id, job.job_number, job.id
        )
        skills_list = [s.skill_name for s in job.job_skills]

        return JobRead(
            id=job.id,
            job_id=job.job_id,
            job_number=job.job_number or job.job_id.upper(),
            company_name=job.company_name,
            company_id=job.company_id or job.recruiter_id,
            title=job.title,
            department=job.department,
            job_type=job.job_type,
            employment_type=job.job_type,
            work_mode=job.work_mode,
            workMode=job.work_mode,
            location=job.location,
            experience=job.experience,
            experience_level=job.experience,
            salary=job.salary,
            salary_min=job.salary_min,
            salary_max=job.salary_max,
            salary_currency=job.salary_currency,
            openings=job.openings,
            number_of_openings=job.openings,
            status=job.status,
            description=job.description,
            job_summary=job.description,
            responsibilities=job.responsibilities,
            key_responsibilities=job.responsibilities,
            requirements=job.requirements,
            technical_requirements=job.requirements,
            qualifications=job.qualifications,
            educational_qualifications=job.qualifications,
            skills=skills_list,
            deadline=job.deadline,
            application_deadline=job.deadline,
            posted_at=job.posted_at.strftime("%Y-%m-%d %H:%M:%S") if job.posted_at else None,
            createdAt=job.posted_at.strftime("%Y-%m-%d") if job.posted_at else (job.created_at.strftime("%Y-%m-%d") if job.created_at else None),
            closed_at=job.closed_at.strftime("%Y-%m-%d %H:%M:%S") if job.closed_at else None,
            created_at=job.created_at.strftime("%Y-%m-%d %H:%M:%S") if job.created_at else None,
            updated_at=job.updated_at.strftime("%Y-%m-%d %H:%M:%S") if job.updated_at else None,
            rejection_reason=job.rejection_reason,
            approved_by=job.approved_by,
            approved_at=job.approved_at.strftime("%Y-%m-%d %H:%M:%S") if job.approved_at else None,
            applicantsCount=app_cnt,
            applicant_count=app_cnt,
            shortlistedCount=short_cnt,
            shortlisted_count=short_cnt,
            interviewsCount=int_cnt,
            interview_count=int_cnt,
        )

    @classmethod
    async def update_job(
        cls,
        db: AsyncSession,
        current_user: User,
        job_identifier: str,
        data: JobUpdate,
    ) -> JobRead:
        """
        Update job posting.
        Business rule: If a PUBLISHED job is materially modified by recruiter,
        it transitions back to PENDING for admin re-approval.
        """
        job = await JobRepository.get_job_by_id(db, job_identifier)
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found.",
            )

        if current_user.role != "ADMIN":
            profile = await JobRepository.get_recruiter_profile_by_user_id(db, current_user.id)
            if not profile or (job.recruiter_id != profile.id and job.company_id != profile.id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You are not authorized to edit another organization's job.",
                )

        now = datetime.now(timezone.utc)
        previous_status = job.status

        # If recruiter submits a draft for approval
        if data.status == "PENDING":
            job.status = "PENDING"
        elif job.status == "PUBLISHED" and current_user.role != "ADMIN":
            # Material changes trigger re-approval
            job.status = "PENDING"

        # Apply updates
        if data.title is not None:
            job.title = data.title.strip()
        if data.department is not None:
            job.department = data.department.strip()
        if data.job_type is not None or data.employment_type is not None:
            job.job_type = data.job_type or data.employment_type
        if data.work_mode is not None or data.workplace_policy is not None:
            job.work_mode = data.work_mode or data.workplace_policy
        if data.location is not None:
            job.location = data.location.strip()
        if data.experience is not None or data.experience_level is not None:
            job.experience = data.experience or data.experience_level
        if data.salary is not None:
            job.salary = data.salary
        if data.salary_min is not None:
            job.salary_min = data.salary_min
        if data.salary_max is not None:
            job.salary_max = data.salary_max
        if data.openings is not None or data.number_of_openings is not None:
            job.openings = data.openings or data.number_of_openings
        if data.deadline is not None or data.application_deadline is not None:
            job.deadline = data.deadline or data.application_deadline
        if data.description is not None or data.job_summary is not None:
            job.description = data.description or data.job_summary
        if data.responsibilities is not None or data.key_responsibilities is not None:
            job.responsibilities = data.responsibilities or data.key_responsibilities
        if data.requirements is not None or data.technical_requirements is not None:
            job.requirements = data.requirements or data.technical_requirements
        if data.qualifications is not None or data.educational_qualifications is not None:
            job.qualifications = data.qualifications or data.educational_qualifications

        job.updated_at = now
        await db.commit()

        # Update skills if provided
        if data.skills is not None:
            from sqlalchemy import delete
            await db.execute(delete(JobSkill).where(JobSkill.job_id == job.id))
            await JobRepository.save_job_skills(db, job.id, data.skills)
            job.skills = ", ".join(data.skills)
            await db.commit()

        await JobRepository.create_audit_log(
            db=db,
            actor=current_user.email,
            action="JOB_UPDATED",
            entity="JOB",
            entity_id=job.id,
            metadata_json={
                "job_number": job.job_number,
                "previous_status": previous_status,
                "current_status": job.status,
            },
        )

        app_cnt, short_cnt, int_cnt = await JobRepository.get_pipeline_counts(
            db, job.job_id, job.job_number, job.id
        )
        skills_list = [s.skill_name for s in job.job_skills]

        return JobRead(
            id=job.id,
            job_id=job.job_id,
            job_number=job.job_number or job.job_id.upper(),
            company_name=job.company_name,
            company_id=job.company_id or job.recruiter_id,
            title=job.title,
            department=job.department,
            job_type=job.job_type,
            employment_type=job.job_type,
            work_mode=job.work_mode,
            workMode=job.work_mode,
            location=job.location,
            experience=job.experience,
            experience_level=job.experience,
            salary=job.salary,
            salary_min=job.salary_min,
            salary_max=job.salary_max,
            salary_currency=job.salary_currency,
            openings=job.openings,
            number_of_openings=job.openings,
            status=job.status,
            description=job.description,
            job_summary=job.description,
            responsibilities=job.responsibilities,
            key_responsibilities=job.responsibilities,
            requirements=job.requirements,
            technical_requirements=job.requirements,
            qualifications=job.qualifications,
            educational_qualifications=job.qualifications,
            skills=skills_list,
            deadline=job.deadline,
            application_deadline=job.deadline,
            posted_at=job.posted_at.strftime("%Y-%m-%d %H:%M:%S") if job.posted_at else None,
            createdAt=job.posted_at.strftime("%Y-%m-%d") if job.posted_at else (job.created_at.strftime("%Y-%m-%d") if job.created_at else None),
            closed_at=job.closed_at.strftime("%Y-%m-%d %H:%M:%S") if job.closed_at else None,
            created_at=job.created_at.strftime("%Y-%m-%d %H:%M:%S") if job.created_at else None,
            updated_at=job.updated_at.strftime("%Y-%m-%d %H:%M:%S") if job.updated_at else None,
            rejection_reason=job.rejection_reason,
            approved_by=job.approved_by,
            approved_at=job.approved_at.strftime("%Y-%m-%d %H:%M:%S") if job.approved_at else None,
            applicantsCount=app_cnt,
            applicant_count=app_cnt,
            shortlistedCount=short_cnt,
            shortlisted_count=short_cnt,
            interviewsCount=int_cnt,
            interview_count=int_cnt,
        )

    # ── Admin Governance ────────────────────────────────────────────────────────

    @classmethod
    async def get_admin_jobs(
        cls,
        db: AsyncSession,
        status_filter: Optional[str] = "ALL",
        department: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> PaginatedJobResponse:
        """Cross-company governance query for Admin."""
        items_data, total = await JobRepository.get_admin_jobs(
            db=db,
            status_filter=status_filter,
            department=department,
            search=search,
            page=page,
            page_size=page_size,
        )
        items = [JobRead(**item) for item in items_data]
        total_pages = (total + page_size - 1) // page_size if total > 0 else 1
        return PaginatedJobResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    @classmethod
    async def get_admin_job_detail(
        cls, db: AsyncSession, job_identifier: str
    ) -> AdminJobDetail:
        """Full details of a job requisition for Administrator."""
        job = await JobRepository.get_job_by_id(db, job_identifier)
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found.",
            )

        app_cnt, short_cnt, int_cnt = await JobRepository.get_pipeline_counts(
            db, job.job_id, job.job_number, job.id
        )
        skills_list = [s.skill_name for s in job.job_skills]
        rec = job.recruiter

        return AdminJobDetail(
            id=job.id,
            job_id=job.job_id,
            job_number=job.job_number or job.job_id.upper(),
            company_name=job.company_name,
            company=job.company_name,
            company_id=job.company_id or job.recruiter_id,
            title=job.title,
            department=job.department or "Core Engineering",
            job_type=job.job_type,
            employment_type=job.job_type,
            work_mode=job.work_mode,
            workMode=job.work_mode,
            location=job.location,
            experience=job.experience or "3-5 years",
            experience_level=job.experience or "3-5 years",
            salary=job.salary,
            salary_min=job.salary_min,
            salary_max=job.salary_max,
            salary_currency=job.salary_currency or "INR",
            openings=job.openings,
            number_of_openings=job.openings,
            status=job.status,
            description=job.description,
            job_summary=job.description,
            responsibilities=job.responsibilities,
            key_responsibilities=job.responsibilities,
            requirements=job.requirements,
            technical_requirements=job.requirements,
            qualifications=job.qualifications,
            educational_qualifications=job.qualifications,
            skills=skills_list,
            deadline=job.deadline,
            application_deadline=job.deadline,
            posted_at=job.posted_at.strftime("%Y-%m-%d %H:%M:%S") if job.posted_at else None,
            createdAt=job.posted_at.strftime("%Y-%m-%d") if job.posted_at else (job.created_at.strftime("%Y-%m-%d") if job.created_at else None),
            closed_at=job.closed_at.strftime("%Y-%m-%d %H:%M:%S") if job.closed_at else None,
            created_at=job.created_at.strftime("%Y-%m-%d %H:%M:%S") if job.created_at else None,
            updated_at=job.updated_at.strftime("%Y-%m-%d %H:%M:%S") if job.updated_at else None,
            rejection_reason=job.rejection_reason,
            approved_by=job.approved_by,
            approved_at=job.approved_at.strftime("%Y-%m-%d %H:%M:%S") if job.approved_at else None,
            applicantsCount=app_cnt,
            applicant_count=app_cnt,
            shortlistedCount=short_cnt,
            shortlisted_count=short_cnt,
            interviewsCount=int_cnt,
            interview_count=int_cnt,
            recruiter_name=rec.recruiter_name if rec else None,
            recruiter=rec.recruiter_name if rec else None,
            recruiter_email=rec.work_email if rec else None,
            recruiter_phone=rec.mobile_phone if rec else None,
        )

    @classmethod
    async def approve_job(
        cls, db: AsyncSession, current_admin: User, job_identifier: str
    ) -> Dict[str, Any]:
        """Admin approves job: PENDING -> PUBLISHED."""
        job = await JobRepository.get_job_by_id(db, job_identifier)
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found.",
            )

        now = datetime.now(timezone.utc)
        job.status = "PUBLISHED"
        job.approved_by = current_admin.email
        job.approved_at = now
        job.posted_at = now
        job.updated_at = now
        await db.commit()

        await JobRepository.create_audit_log(
            db=db,
            actor=current_admin.email,
            action="JOB_APPROVED",
            entity="JOB",
            entity_id=job.id,
            metadata_json={"job_number": job.job_number, "status": "PUBLISHED"},
        )

        # Notify recruiter
        try:
            from app.models.notification import Notification
            if job.recruiter and job.recruiter.user_id:
                notif = Notification(
                    id=f"notif-{uuid.uuid4().hex[:10]}",
                    user_id=job.recruiter.user_id,
                    title="Job Requisition Approved",
                    message=f"Your job '{job.title}' has been approved and published.",
                    type="JOB",
                    read=False,
                    created_at=now,
                )
                db.add(notif)
                await db.commit()
        except Exception:
            pass

        return {
            "id": job.id,
            "job_id": job.job_id,
            "job_number": job.job_number,
            "status": "PUBLISHED",
            "posted_at": job.posted_at.strftime("%Y-%m-%d %H:%M:%S"),
            "approved_by": job.approved_by,
            "approved_at": job.approved_at.strftime("%Y-%m-%d %H:%M:%S"),
            "message": f"Job '{job.title}' has been approved and published successfully.",
        }

    @classmethod
    async def reject_job(
        cls, db: AsyncSession, current_admin: User, job_identifier: str, reason: str
    ) -> Dict[str, Any]:
        """Admin rejects job: PENDING -> REJECTED with mandatory reason."""
        job = await JobRepository.get_job_by_id(db, job_identifier)
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found.",
            )

        now = datetime.now(timezone.utc)
        job.status = "REJECTED"
        job.rejection_reason = reason.strip()
        job.approved_by = None
        job.updated_at = now
        await db.commit()

        await JobRepository.create_audit_log(
            db=db,
            actor=current_admin.email,
            action="JOB_REJECTED",
            entity="JOB",
            entity_id=job.id,
            metadata_json={
                "job_number": job.job_number,
                "status": "REJECTED",
                "reason": reason.strip(),
            },
        )

        # Notify recruiter
        try:
            from app.models.notification import Notification
            if job.recruiter and job.recruiter.user_id:
                notif = Notification(
                    id=f"notif-{uuid.uuid4().hex[:10]}",
                    user_id=job.recruiter.user_id,
                    title="Job Requisition Rejected",
                    message=f"Your job '{job.title}' was rejected. Reason: {reason.strip()}",
                    type="JOB",
                    read=False,
                    created_at=now,
                )
                db.add(notif)
                await db.commit()
        except Exception:
            pass

        return {
            "id": job.id,
            "job_id": job.job_id,
            "job_number": job.job_number,
            "status": "REJECTED",
            "rejection_reason": job.rejection_reason,
            "message": f"Job '{job.title}' has been rejected.",
        }

    # ── Candidate & Public API ──────────────────────────────────────────────────

    @classmethod
    async def get_published_jobs(
        cls,
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
    ) -> PaginatedJobResponse:
        """Candidate and public view. Strictly returns only PUBLISHED jobs."""
        items_data, total = await JobRepository.get_published_jobs(
            db=db,
            search=search,
            department=department,
            location=location,
            experience_level=experience_level,
            salary_min=salary_min,
            salary_max=salary_max,
            salary_range=salary_range,
            work_mode=work_mode,
            employment_type=employment_type,
            required_skill=required_skill,
            industry_sector=industry_sector,
            sort=sort,
            page=page,
            page_size=page_size,
            current_user=current_user,
        )
        items = [JobRead(**item) for item in items_data]
        total_pages = (total + page_size - 1) // page_size if total > 0 else 1
        return PaginatedJobResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    @classmethod
    async def get_job_public_or_authenticated(
        cls, db: AsyncSession, job_identifier: str, current_user: Optional[User] = None
    ) -> JobRead:
        """
        Fetch single job detail.
        Public candidates can ONLY view PUBLISHED jobs.
        Owning recruiter and admins can view any status.
        """
        job = await JobRepository.get_job_by_id(db, job_identifier)
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job opening not found.",
            )

        # Access check for non-published jobs
        if job.status != "PUBLISHED":
            is_authorized = False
            if current_user:
                if current_user.role == "ADMIN":
                    is_authorized = True
                elif current_user.role == "RECRUITER":
                    profile = await JobRepository.get_recruiter_profile_by_user_id(db, current_user.id)
                    if profile and (job.recruiter_id == profile.id or job.company_id == profile.id):
                        is_authorized = True

            if not is_authorized:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Job opening not found or not published.",
                )

        app_cnt, short_cnt, int_cnt = await JobRepository.get_pipeline_counts(
            db, job.job_id, job.job_number, job.id
        )
        skills_list = [s.skill_name for s in job.job_skills]
        if not skills_list and job.skills:
            skills_list = [s.strip() for s in job.skills.split(",") if s.strip()]

        is_saved = False
        has_applied = False
        match_score = None
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
                    select(SavedJob.id).where(
                        SavedJob.candidate_profile_id == profile.id,
                        SavedJob.job_id.in_([job.id, job.job_id, job.job_number or ""])
                    )
                )
                is_saved = bool(s_res.first())

                a_res = await db.execute(
                    select(CandidateApplication.id).where(
                        CandidateApplication.candidate_profile_id == profile.id,
                        CandidateApplication.job_id.in_([job.id, job.job_id, job.job_number or ""])
                    )
                )
                has_applied = bool(a_res.first())

                sk_res = await db.execute(
                    select(CandidateSkill.skill_name).where(CandidateSkill.candidate_profile_id == profile.id)
                )
                cand_skills = [r[0].lower().strip() for r in sk_res.fetchall() if r[0]]
                if cand_skills and skills_list:
                    job_tags = [s.lower().strip() for s in skills_list]
                    matches = [s for s in job_tags if any(cs in s or s in cs for cs in cand_skills)]
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
            "id": job.company_id or job.recruiter_id,
            "name": job.company_name,
            "logo_url": job.recruiter.company_logo_path if job.recruiter else None,
            "verified": True,
        }
        industry_val = (
            job.recruiter.primary_industry
            if (job.recruiter and job.recruiter.primary_industry)
            else (job.department or "Information Technology")
        )

        return JobRead(
            id=job.id,
            job_id=job.job_id,
            job_number=job.job_number or job.job_id.upper(),
            company_name=job.company_name,
            company_id=job.company_id or job.recruiter_id,
            company=company_obj,
            company_verified=True,
            company_logo=job.recruiter.company_logo_path if job.recruiter else None,
            company_logo_path=job.recruiter.company_logo_path if job.recruiter else None,
            title=job.title,
            department=job.department or "Core Engineering",
            industry=industry_val,
            job_type=job.job_type,
            employment_type=job.job_type,
            work_mode=job.work_mode,
            workMode=job.work_mode,
            location=job.location,
            experience=job.experience,
            experience_level=job.experience,
            salary=job.salary,
            salary_min=job.salary_min,
            salary_max=job.salary_max,
            salary_currency=job.salary_currency,
            openings=job.openings,
            number_of_openings=job.openings,
            status=job.status,
            description=job.description,
            job_summary=job.description,
            responsibilities=job.responsibilities,
            key_responsibilities=job.responsibilities,
            requirements=job.requirements,
            technical_requirements=job.requirements,
            qualifications=job.qualifications,
            educational_qualifications=job.qualifications,
            skills=skills_list,
            tags=skills_list,
            deadline=job.deadline,
            application_deadline=job.deadline,
            posted_at=job.posted_at.strftime("%Y-%m-%d %H:%M:%S") if job.posted_at else None,
            createdAt=job.posted_at.strftime("%Y-%m-%d") if job.posted_at else (job.created_at.strftime("%Y-%m-%d") if job.created_at else None),
            closed_at=job.closed_at.strftime("%Y-%m-%d %H:%M:%S") if job.closed_at else None,
            created_at=job.created_at.strftime("%Y-%m-%d %H:%M:%S") if job.created_at else None,
            updated_at=job.updated_at.strftime("%Y-%m-%d %H:%M:%S") if job.updated_at else None,
            rejection_reason=job.rejection_reason,
            approved_by=job.approved_by,
            approved_at=job.approved_at.strftime("%Y-%m-%d %H:%M:%S") if job.approved_at else None,
            applicantsCount=app_cnt,
            applicant_count=app_cnt,
            shortlistedCount=short_cnt,
            shortlisted_count=short_cnt,
            interviewsCount=int_cnt,
            interview_count=int_cnt,
            is_saved=is_saved,
            has_applied=has_applied,
            match_score=match_score,
            is_active=job.status == "PUBLISHED",
        )

    @classmethod
    async def submit_draft_job(
        cls,
        db: AsyncSession,
        current_user: User,
        job_identifier: str,
    ) -> JobRead:
        """
        Transition a DRAFT or REJECTED job to PENDING for administrator review.
        """
        job = await JobRepository.get_job_by_id(db, job_identifier)
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found.",
            )

        if current_user.role != "ADMIN":
            profile = await JobRepository.get_recruiter_profile_by_user_id(db, current_user.id)
            if not profile or (job.recruiter_id != profile.id and job.company_id != profile.id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You are not authorized to submit another organization's job.",
                )

        now = datetime.now(timezone.utc)
        job.status = "PENDING"
        job.rejection_reason = None
        job.updated_at = now
        await db.commit()

        await JobRepository.create_audit_log(
            db=db,
            actor=current_user.email,
            action="JOB_SUBMITTED_FOR_APPROVAL",
            entity="JOB",
            entity_id=job.id,
            metadata_json={"job_number": job.job_number, "status": "PENDING"},
        )

        app_cnt, short_cnt, int_cnt = await JobRepository.get_pipeline_counts(
            db, job.job_id, job.job_number, job.id
        )
        skills_list = [s.skill_name for s in job.job_skills]

        return JobRead(
            id=job.id,
            job_id=job.job_id,
            job_number=job.job_number or job.job_id.upper(),
            company_name=job.company_name,
            company_id=job.company_id or job.recruiter_id,
            title=job.title,
            department=job.department or "Core Engineering",
            job_type=job.job_type,
            employment_type=job.job_type,
            work_mode=job.work_mode,
            workMode=job.work_mode,
            location=job.location,
            experience=job.experience or "3-5 years",
            experience_level=job.experience or "3-5 years",
            salary=job.salary,
            salary_min=job.salary_min,
            salary_max=job.salary_max,
            salary_currency=job.salary_currency or "INR",
            openings=job.openings,
            number_of_openings=job.openings,
            status=job.status,
            description=job.description,
            job_summary=job.description,
            responsibilities=job.responsibilities,
            key_responsibilities=job.responsibilities,
            requirements=job.requirements,
            technical_requirements=job.requirements,
            qualifications=job.qualifications,
            educational_qualifications=job.qualifications,
            skills=skills_list,
            deadline=job.deadline,
            application_deadline=job.deadline,
            posted_at=job.posted_at.strftime("%Y-%m-%d %H:%M:%S") if job.posted_at else None,
            createdAt=job.posted_at.strftime("%Y-%m-%d") if job.posted_at else (job.created_at.strftime("%Y-%m-%d") if job.created_at else None),
            closed_at=job.closed_at.strftime("%Y-%m-%d %H:%M:%S") if job.closed_at else None,
            created_at=job.created_at.strftime("%Y-%m-%d %H:%M:%S") if job.created_at else None,
            updated_at=job.updated_at.strftime("%Y-%m-%d %H:%M:%S") if job.updated_at else None,
            rejection_reason=None,
            approved_by=job.approved_by,
            approved_at=job.approved_at.strftime("%Y-%m-%d %H:%M:%S") if job.approved_at else None,
            applicantsCount=app_cnt,
            applicant_count=app_cnt,
            shortlistedCount=short_cnt,
            shortlisted_count=short_cnt,
            interviewsCount=int_cnt,
            interview_count=int_cnt,
        )

