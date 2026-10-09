import uuid
import re
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, func, or_, and_, desc
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.recruiter import RecruiterProfile
from app.models.user import User
from app.models.company_team import CompanyMember
from app.models.job import Job
from app.models.internship import Internship
from app.models.application import CandidateApplication
from app.models.password_reset_token import PasswordResetToken
from app.core.security import hash_password
from app.services.audit_service import AuditService


class AdminRecruiterRepository:
    """
    Database repository layer for Admin Recruiter management.
    Handles querying, verification, account suspension/activation, and direct onboarding.
    """

    @staticmethod
    async def get_admin_recruiters(
        db: AsyncSession,
        status_filter: Optional[str] = "ALL",
        company_filter: Optional[str] = "ALL",
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> Tuple[List[Dict[str, Any]], int, int, int, int]:
        """
        Fetch paginated recruiters across the platform for Administrator governance.
        Returns: (items, total, verified_count, pending_count, suspended_count)
        """
        # Base query joining RecruiterProfile and User
        conds = []

        # 1. Company Filter
        if company_filter and company_filter.strip() and company_filter.strip().upper() != "ALL":
            clean_comp = company_filter.strip()
            conds.append(
                or_(
                    RecruiterProfile.company_name.ilike(f"%{clean_comp}%"),
                    RecruiterProfile.id == clean_comp,
                )
            )

        # 2. Status Filter
        if status_filter and status_filter.strip() and status_filter.strip().upper() != "ALL":
            norm_status = status_filter.strip().upper()
            if norm_status == "VERIFIED":
                conds.append(
                    and_(
                        RecruiterProfile.status.in_(["VERIFIED", "APPROVED"]),
                        or_(
                            RecruiterProfile.user.has(User.is_active.is_(True)),
                            RecruiterProfile.user_id.is_(None),
                        ),
                    )
                )
            elif norm_status == "PENDING":
                conds.append(RecruiterProfile.status.in_(["PENDING", "PENDING_APPROVAL"]))
            elif norm_status == "SUSPENDED":
                conds.append(
                    or_(
                        RecruiterProfile.status == "SUSPENDED",
                        RecruiterProfile.user.has(User.is_active.is_(False)),
                    )
                )
            elif norm_status == "REJECTED":
                conds.append(RecruiterProfile.status == "REJECTED")

        # 3. Search Filter
        if search and search.strip():
            q = f"%{search.strip()}%"
            conds.append(
                or_(
                    RecruiterProfile.recruiter_name.ilike(q),
                    RecruiterProfile.work_email.ilike(q),
                    RecruiterProfile.company_name.ilike(q),
                    RecruiterProfile.designation.ilike(q),
                    RecruiterProfile.mobile_phone.ilike(q),
                    RecruiterProfile.headquarters_city_state.ilike(q),
                )
            )

        filter_clause = and_(*conds) if conds else None

        # Calculate metrics over the entire recruiter population (respecting company filter if set)
        metrics_base_conds = []
        if company_filter and company_filter.strip() and company_filter.strip().upper() != "ALL":
            metrics_base_conds.append(
                or_(
                    RecruiterProfile.company_name.ilike(f"%{company_filter.strip()}%"),
                    RecruiterProfile.id == company_filter.strip(),
                )
            )
        metrics_clause = and_(*metrics_base_conds) if metrics_base_conds else True

        # Verified count
        v_stmt = (
            select(func.count(RecruiterProfile.id))
            .join(User, RecruiterProfile.user_id == User.id, isouter=True)
            .where(
                and_(
                    metrics_clause,
                    RecruiterProfile.status.in_(["VERIFIED", "APPROVED"]),
                    or_(User.is_active.is_(True), User.id.is_(None)),
                )
            )
        )
        verified_count = (await db.execute(v_stmt)).scalar() or 0

        # Pending count
        p_stmt = (
            select(func.count(RecruiterProfile.id))
            .where(
                and_(
                    metrics_clause,
                    RecruiterProfile.status.in_(["PENDING", "PENDING_APPROVAL"]),
                )
            )
        )
        pending_count = (await db.execute(p_stmt)).scalar() or 0

        # Suspended count
        s_stmt = (
            select(func.count(RecruiterProfile.id))
            .join(User, RecruiterProfile.user_id == User.id, isouter=True)
            .where(
                and_(
                    metrics_clause,
                    or_(
                        RecruiterProfile.status == "SUSPENDED",
                        User.is_active.is_(False),
                    ),
                )
            )
        )
        suspended_count = (await db.execute(s_stmt)).scalar() or 0

        # Count total filtered records
        count_stmt = select(func.count(RecruiterProfile.id)).join(User, RecruiterProfile.user_id == User.id, isouter=True)
        if filter_clause is not None:
            count_stmt = count_stmt.where(filter_clause)
        total = (await db.execute(count_stmt)).scalar() or 0

        # Fetch paginated rows
        stmt = (
            select(RecruiterProfile, User)
            .join(User, RecruiterProfile.user_id == User.id, isouter=True)
        )
        if filter_clause is not None:
            stmt = stmt.where(filter_clause)
        stmt = (
            stmt.order_by(RecruiterProfile.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        rows = (await db.execute(stmt)).all()

        profile_ids = [p.id for p, _ in rows if p]

        # Batch query job counts for recruiters
        job_counts: Dict[str, int] = {}
        if profile_ids:
            j_stmt = (
                select(
                    func.coalesce(Job.recruiter_id, Job.company_id).label("c_id"),
                    func.count(Job.id),
                )
                .where(
                    and_(
                        or_(Job.recruiter_id.in_(profile_ids), Job.company_id.in_(profile_ids)),
                        Job.closed_at.is_(None),
                    )
                )
                .group_by("c_id")
            )
            for cid, cnt in (await db.execute(j_stmt)).all():
                if cid:
                    job_counts[cid] = cnt

        items = []
        for profile, user in rows:
            # Determine verification status
            raw_v_status = profile.status or "PENDING"
            v_status = "VERIFIED" if raw_v_status in ["VERIFIED", "APPROVED"] else (
                "PENDING" if raw_v_status in ["PENDING", "PENDING_APPROVAL"] else raw_v_status
            )

            # Determine account status
            is_active = user.is_active if user else (raw_v_status != "SUSPENDED")
            acc_status = "ACTIVE" if is_active else "SUSPENDED"

            reg_date = (
                profile.created_at.strftime("%Y-%m-%d")
                if profile.created_at
                else datetime.now(timezone.utc).strftime("%Y-%m-%d")
            )

            posted_jobs = job_counts.get(profile.id, 0)

            items.append({
                "id": profile.id,
                "user_id": profile.user_id,
                "name": profile.recruiter_name,
                "recruiter_name": profile.recruiter_name,
                "email": profile.work_email or (user.email if user else ""),
                "work_email": profile.work_email or (user.email if user else ""),
                "phone": profile.mobile_phone or (user.phone if user else ""),
                "mobile_phone": profile.mobile_phone or (user.phone if user else ""),
                "designation": profile.designation or "Talent Acquisition Manager",
                "company": profile.company_name,
                "company_name": profile.company_name,
                "company_id": profile.id,
                "industry": profile.primary_industry or "Information Technology & Services",
                "location": profile.headquarters_city_state or "Vijayawada, NTR District",
                "district": profile.district or "NTR District",
                "mandal": profile.mandal or "Vijayawada Urban",
                "village": profile.village or "",
                "registration_date": reg_date,
                "registrationDate": reg_date,
                "created_at": profile.created_at.strftime("%Y-%m-%d %H:%M:%S") if profile.created_at else None,
                "verification_status": v_status,
                "verificationStatus": v_status,
                "account_status": acc_status,
                "accountStatus": acc_status,
                "posted_jobs_count": posted_jobs,
                "postedJobsCount": posted_jobs,
                "open_jobs": posted_jobs,
                "onboarded_by": profile.reviewed_by or profile.onboarded_by_role or "ADMIN",
            })

        return items, total, verified_count, pending_count, suspended_count

    @staticmethod
    async def get_recruiter_by_id(
        db: AsyncSession, recruiter_id: str
    ) -> Optional[Dict[str, Any]]:
        """Fetch complete recruiter dossier by RecruiterProfile ID or User ID."""
        stmt = (
            select(RecruiterProfile, User)
            .join(User, RecruiterProfile.user_id == User.id, isouter=True)
            .where(
                or_(
                    RecruiterProfile.id == recruiter_id,
                    RecruiterProfile.user_id == recruiter_id,
                )
            )
        )
        row = (await db.execute(stmt)).first()
        if not row:
            return None

        profile, user = row

        # Fetch posted jobs
        j_stmt = (
            select(Job)
            .where(
                or_(
                    Job.recruiter_id == profile.id,
                    Job.company_id == profile.id,
                )
            )
            .order_by(Job.created_at.desc())
        )
        jobs_res = (await db.execute(j_stmt)).scalars().all()
        jobs_list = [
            {
                "id": j.id,
                "job_id": j.job_id,
                "title": j.title,
                "status": j.status,
                "location": j.location,
                "salary": j.salary,
                "type": j.job_type,
                "postedDate": j.created_at.strftime("%Y-%m-%d") if j.created_at else None,
            }
            for j in jobs_res
        ]

        # Fetch posted internships
        in_stmt = (
            select(Internship)
            .where(Internship.company_id == profile.id)
            .order_by(Internship.created_at.desc())
        )
        intern_res = (await db.execute(in_stmt)).scalars().all()
        intern_list = [
            {
                "id": i.id,
                "title": i.title,
                "status": i.status,
                "stipend": i.stipend,
                "duration": i.duration,
                "location": i.location,
                "created_at": i.created_at.strftime("%Y-%m-%d") if i.created_at else None,
            }
            for i in intern_res
        ]

        raw_v_status = profile.status or "PENDING"
        v_status = "VERIFIED" if raw_v_status in ["VERIFIED", "APPROVED"] else (
            "PENDING" if raw_v_status in ["PENDING", "PENDING_APPROVAL"] else raw_v_status
        )
        is_active = user.is_active if user else (raw_v_status != "SUSPENDED")
        acc_status = "ACTIVE" if is_active else "SUSPENDED"

        reg_date = (
            profile.created_at.strftime("%Y-%m-%d")
            if profile.created_at
            else datetime.now(timezone.utc).strftime("%Y-%m-%d")
        )

        return {
            "id": profile.id,
            "user_id": profile.user_id,
            "name": profile.recruiter_name,
            "recruiter_name": profile.recruiter_name,
            "email": profile.work_email or (user.email if user else ""),
            "work_email": profile.work_email or (user.email if user else ""),
            "phone": profile.mobile_phone or (user.phone if user else ""),
            "mobile_phone": profile.mobile_phone or (user.phone if user else ""),
            "designation": profile.designation or "Talent Acquisition Manager",
            "company": profile.company_name,
            "company_name": profile.company_name,
            "company_id": profile.id,
            "company_website": profile.company_website,
            "company_size": profile.company_size,
            "company_type": profile.company_type,
            "registered_office_address": profile.registered_office_address,
            "company_description": profile.company_description,
            "cin_number": profile.cin_number,
            "gst_number": profile.gst_number,
            "company_logo_path": profile.company_logo_path,
            "industry": profile.primary_industry,
            "location": profile.headquarters_city_state,
            "district": profile.district,
            "mandal": profile.mandal,
            "village": profile.village,
            "registration_date": reg_date,
            "registrationDate": reg_date,
            "created_at": profile.created_at.strftime("%Y-%m-%d %H:%M:%S") if profile.created_at else None,
            "verification_status": v_status,
            "verificationStatus": v_status,
            "account_status": acc_status,
            "accountStatus": acc_status,
            "posted_jobs_count": len(jobs_list),
            "postedJobsCount": len(jobs_list),
            "open_jobs": len(jobs_list),
            "open_internships": len(intern_list),
            "rejection_reason": profile.rejection_reason,
            "reviewed_by": profile.reviewed_by,
            "reviewed_at": profile.reviewed_at.strftime("%Y-%m-%d %H:%M:%S") if profile.reviewed_at else None,
            "onboarded_by_admin_id": profile.onboarded_by_admin_id,
            "jobs": jobs_list,
            "internships": intern_list,
        }

    @staticmethod
    async def create_admin_recruiter(
        db: AsyncSession,
        admin_user: User,
        payload: Any,
    ) -> Dict[str, Any]:
        """
        Direct Onboard Recruiter / Employer by Platform Administrator.
        Reuses or creates company record, associates recruiter, sets status VERIFIED,
        creates activation token and audit log.
        """
        clean_email = payload.email.strip().lower()
        clean_phone = payload.phone.strip() if payload.phone and payload.phone.strip() else None

        # 1. Prevent duplicate accounts for the same email
        u_stmt = select(User).where(User.email == clean_email)
        existing_user = (await db.execute(u_stmt)).scalar_one_or_none()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"An account with email '{clean_email}' already exists.",
            )

        rp_stmt = select(RecruiterProfile).where(RecruiterProfile.work_email == clean_email)
        existing_rp = (await db.execute(rp_stmt)).scalar_one_or_none()
        if existing_rp:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"A recruiter profile with email '{clean_email}' already exists.",
            )

        # 2. Company Assignment
        assigned_company_name = None
        parent_profile: Optional[RecruiterProfile] = None

        if payload.company_type == "NEW" or (not payload.selected_company and payload.new_company_name):
            assigned_company_name = (payload.new_company_name or "").strip()
            if not assigned_company_name:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="New company name is required when registering a new company.",
                )
            # Check if company with this name already exists
            cp_stmt = select(RecruiterProfile).where(
                func.lower(RecruiterProfile.company_name) == assigned_company_name.lower()
            )
            parent_profile = (await db.execute(cp_stmt)).scalars().first()
        else:
            # Existing company assignment
            target_name = (payload.selected_company or payload.company or "").strip()
            if payload.company_id:
                cp_stmt = select(RecruiterProfile).where(RecruiterProfile.id == payload.company_id.strip())
                parent_profile = (await db.execute(cp_stmt)).scalars().first()
            if not parent_profile and target_name:
                cp_stmt = select(RecruiterProfile).where(
                    func.lower(RecruiterProfile.company_name) == target_name.lower()
                )
                parent_profile = (await db.execute(cp_stmt)).scalars().first()

            if parent_profile:
                assigned_company_name = parent_profile.company_name
            else:
                assigned_company_name = target_name or "NTR Enterprise Partner"

        # 3. Create Recruiter User
        now = datetime.now(timezone.utc)
        new_user = User(
            id=str(uuid.uuid4()),
            email=clean_email,
            phone=clean_phone,
            hashed_password=hash_password(f"NtrRecruiter@{str(uuid.uuid4().hex[:6])}"),
            role="RECRUITER",
            is_active=True,
            is_verified=True,
            created_at=now,
            updated_at=now,
        )
        db.add(new_user)
        await db.flush()

        # 4. Generate one-time secure activation token
        import hashlib
        raw_token = str(uuid.uuid4())
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        activation_token = PasswordResetToken(
            id=str(uuid.uuid4()),
            user_id=new_user.id,
            token_hash=token_hash,
            expires_at=now + timedelta(days=7),
            created_at=now,
        )
        db.add(activation_token)

        # 5. Location and details resolution
        location_val = (
            payload.location.strip()
            if payload.location and payload.location.strip()
            else (parent_profile.headquarters_city_state if parent_profile else "Vijayawada, NTR District")
        )
        industry_val = (
            payload.industry.strip()
            if payload.industry and payload.industry.strip()
            else (parent_profile.primary_industry if parent_profile else "Information Technology & Services")
        )

        # 6. Create RecruiterProfile for this recruiter
        new_recruiter_profile = RecruiterProfile(
            id=str(uuid.uuid4()),
            user_id=new_user.id,
            recruiter_name=payload.name.strip(),
            designation=payload.designation.strip() if payload.designation else "Talent Acquisition Manager",
            work_email=clean_email,
            mobile_phone=clean_phone or f"+91 98480 {str(uuid.uuid4().int)[:5]}",
            company_name=assigned_company_name,
            company_website=(
                parent_profile.company_website
                if parent_profile
                else f"https://www.{re.sub(r'[^a-zA-Z0-9]', '', assigned_company_name).lower()}.com"
            ),
            corporate_email=clean_email,
            company_phone=clean_phone or "+91 866 245 0000",
            primary_industry=industry_val,
            company_size=parent_profile.company_size if parent_profile else "100-500 employees",
            company_type=parent_profile.company_type if parent_profile else "Private Limited (Pvt Ltd)",
            headquarters_city_state=location_val,
            registered_office_address=location_val,
            company_description=(
                parent_profile.company_description
                if parent_profile
                else f"Verified enterprise hiring organization: {assigned_company_name}."
            ),
            district=payload.district or (parent_profile.district if parent_profile else "NTR District"),
            mandal=payload.mandal or (parent_profile.mandal if parent_profile else "Vijayawada Urban"),
            village=payload.village or (parent_profile.village if parent_profile else ""),
            status="VERIFIED",
            onboarded_by_admin_id=admin_user.id,
            onboarded_by_role="ADMIN",
            reviewed_by=admin_user.email,
            reviewed_at=now,
            created_at=now,
            updated_at=now,
        )
        db.add(new_recruiter_profile)
        await db.flush()

        # 7. Create CompanyMember relationship (links to canonical parent company or to self if root)
        parent_comp_id = parent_profile.id if parent_profile else new_recruiter_profile.id
        company_member = CompanyMember(
            id=str(uuid.uuid4()),
            company_id=parent_comp_id,
            user_id=new_user.id,
            role=payload.designation or "TALENT_ACQUISITION_MANAGER",
            status="ACTIVE",
            invited_by=admin_user.id,
            joined_at=now,
            created_at=now,
            updated_at=now,
        )
        db.add(company_member)

        # 8. Commit everything
        await db.commit()
        await db.refresh(new_recruiter_profile)

        # 9. Log administrative audit trail
        await AuditService.log_event(
            db=db,
            actor=admin_user.email or "Admin",
            action="RECRUITER_ONBOARDED",
            entity="RECRUITER",
            entity_id=new_recruiter_profile.id,
            target_name=f"{payload.name} ({assigned_company_name})",
            result="SUCCESS",
            metadata={
                "recruiter_name": payload.name,
                "email": clean_email,
                "company": assigned_company_name,
                "company_id": parent_comp_id,
                "onboarded_by_admin_id": admin_user.id,
            },
        )

        reg_date = now.strftime("%Y-%m-%d")

        return {
            "id": new_recruiter_profile.id,
            "user_id": new_user.id,
            "name": new_recruiter_profile.recruiter_name,
            "recruiter_name": new_recruiter_profile.recruiter_name,
            "email": clean_email,
            "work_email": clean_email,
            "phone": new_recruiter_profile.mobile_phone,
            "mobile_phone": new_recruiter_profile.mobile_phone,
            "designation": new_recruiter_profile.designation,
            "company": assigned_company_name,
            "company_name": assigned_company_name,
            "company_id": parent_comp_id,
            "industry": industry_val,
            "location": location_val,
            "registration_date": reg_date,
            "registrationDate": reg_date,
            "created_at": now.strftime("%Y-%m-%d %H:%M:%S"),
            "verification_status": "VERIFIED",
            "verificationStatus": "VERIFIED",
            "account_status": "ACTIVE",
            "accountStatus": "ACTIVE",
            "posted_jobs_count": 0,
            "postedJobsCount": 0,
            "onboarded_by": "ADMIN",
        }

    @staticmethod
    async def update_recruiter_verification(
        db: AsyncSession,
        admin_user: User,
        recruiter_id: str,
        target_status: str,
        notes: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update recruiter verification status (VERIFIED, REJECTED, PENDING)."""
        stmt = (
            select(RecruiterProfile, User)
            .join(User, RecruiterProfile.user_id == User.id, isouter=True)
            .where(
                or_(
                    RecruiterProfile.id == recruiter_id,
                    RecruiterProfile.user_id == recruiter_id,
                )
            )
        )
        row = (await db.execute(stmt)).first()
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Recruiter with ID '{recruiter_id}' not found.",
            )

        profile, user = row
        now = datetime.now(timezone.utc)

        norm_status = target_status.strip().upper()
        if norm_status in ["VERIFIED", "APPROVED"]:
            profile.status = "VERIFIED"
            profile.reviewed_by = admin_user.email
            profile.reviewed_at = now
            if user:
                user.is_verified = True
        elif norm_status == "REJECTED":
            profile.status = "REJECTED"
            profile.rejection_reason = reason or notes or "Rejected by platform administrator."
            profile.reviewed_by = admin_user.email
            profile.reviewed_at = now
        else:
            profile.status = "PENDING"

        profile.updated_at = now
        if user:
            user.updated_at = now

        await db.commit()
        await db.refresh(profile)

        # Audit log
        await AuditService.log_event(
            db=db,
            actor=admin_user.email or "Admin",
            action=f"RECRUITER_{norm_status}",
            entity="RECRUITER",
            entity_id=profile.id,
            target_name=f"{profile.recruiter_name} ({profile.company_name})",
            result="SUCCESS",
            metadata={
                "new_status": profile.status,
                "notes": notes,
                "reason": reason,
            },
        )

        return await AdminRecruiterRepository.get_recruiter_by_id(db, profile.id)

    @staticmethod
    async def update_recruiter_account_status(
        db: AsyncSession,
        admin_user: User,
        recruiter_id: str,
        target_status: str,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Suspend or Activate a recruiter account without affecting the entire company."""
        stmt = (
            select(RecruiterProfile, User)
            .join(User, RecruiterProfile.user_id == User.id, isouter=True)
            .where(
                or_(
                    RecruiterProfile.id == recruiter_id,
                    RecruiterProfile.user_id == recruiter_id,
                )
            )
        )
        row = (await db.execute(stmt)).first()
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Recruiter with ID '{recruiter_id}' not found.",
            )

        profile, user = row
        now = datetime.now(timezone.utc)
        norm_status = target_status.strip().upper()

        if norm_status == "SUSPENDED":
            if user:
                user.is_active = False
                user.updated_at = now
            profile.updated_at = now

            # If user has team membership, update member status
            if user:
                m_stmt = select(CompanyMember).where(CompanyMember.user_id == user.id)
                members = (await db.execute(m_stmt)).scalars().all()
                for m in members:
                    m.status = "SUSPENDED"
                    m.updated_at = now

            action_name = "RECRUITER_SUSPENDED"
        else:
            # ACTIVE
            if user:
                user.is_active = True
                user.updated_at = now
            if profile.status == "SUSPENDED":
                profile.status = "VERIFIED"
            profile.updated_at = now

            if user:
                m_stmt = select(CompanyMember).where(CompanyMember.user_id == user.id)
                members = (await db.execute(m_stmt)).scalars().all()
                for m in members:
                    m.status = "ACTIVE"
                    m.updated_at = now

            action_name = "RECRUITER_ACTIVATED"

        await db.commit()
        await db.refresh(profile)

        # Audit log
        await AuditService.log_event(
            db=db,
            actor=admin_user.email or "Admin",
            action=action_name,
            entity="RECRUITER",
            entity_id=profile.id,
            target_name=f"{profile.recruiter_name} ({profile.company_name})",
            result="SUCCESS",
            metadata={
                "account_status": norm_status,
                "reason": reason,
            },
        )

        return await AdminRecruiterRepository.get_recruiter_by_id(db, profile.id)
