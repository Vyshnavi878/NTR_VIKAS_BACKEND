import uuid
import json
import re
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy import select, func, or_, and_, desc
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.internship import Internship, InternshipApplication, AuditLog
from app.models.recruiter import RecruiterProfile
from app.models.user import User


class InternshipRepository:
    """
    Database repository layer for Internship entities using SQLAlchemy 2.0 AsyncIO.
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
    async def generate_next_internship_number(db: AsyncSession) -> str:
        """
        Generate sequential unique internship number in format INT-0001, INT-0002, etc.
        """
        stmt = select(Internship.internship_number).order_by(Internship.created_at.desc())
        result = await db.execute(stmt)
        numbers = result.scalars().all()

        max_num = 0
        for num in numbers:
            if num:
                match = re.search(r"INT-(\d+)", num, re.IGNORECASE)
                if match:
                    val = int(match.group(1))
                    if val > max_num:
                        max_num = val

        next_val = max_num + 1
        return f"INT-{next_val:04d}"

    @staticmethod
    async def create_internship(
        db: AsyncSession,
        company_id: str,
        created_by: str,
        title: str,
        stipend_monthly: int,
        stipend: str,
        duration: str,
        work_mode: str,
        location: str,
        number_of_interns: int,
        description: str,
        status: str = "PENDING",
    ) -> Internship:
        """Create and persist a new internship record."""
        now = datetime.now(timezone.utc)
        intern_id = f"intern-{uuid.uuid4().hex[:8]}"
        intern_number = await InternshipRepository.generate_next_internship_number(db)

        internship = Internship(
            id=intern_id,
            internship_number=intern_number,
            company_id=company_id,
            created_by=created_by,
            title=title,
            stipend_monthly=stipend_monthly,
            stipend=stipend,
            duration=duration,
            work_mode=work_mode,
            location=location,
            number_of_interns=number_of_interns,
            description=description,
            status=status,
            created_at=now,
            updated_at=now,
        )
        db.add(internship)
        await db.commit()
        await db.refresh(internship)
        return internship

    @staticmethod
    async def get_applicant_count_for_internship(
        db: AsyncSession, internship_id: str, internship_number: Optional[str] = None
    ) -> int:
        """Count actual applications submitted for an internship."""
        conditions = [InternshipApplication.internship_id == internship_id]
        if internship_number:
            conditions.append(InternshipApplication.internship_id == internship_number)

        stmt = select(func.count(InternshipApplication.id)).where(or_(*conditions))
        result = await db.execute(stmt)
        return result.scalar() or 0

    @staticmethod
    async def get_recruiter_internships(
        db: AsyncSession,
        company_id: str,
        status_filter: Optional[str] = "ALL",
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Fetch paginated internships belonging to the authenticated recruiter's company.
        """
        base_conds = [Internship.company_id == company_id]

        # Status filter mapping
        if status_filter:
            norm_status = status_filter.upper().strip()
            if norm_status in ("ACTIVE", "PUBLISHED"):
                base_conds.append(Internship.status == "PUBLISHED")
            elif norm_status == "PENDING":
                base_conds.append(Internship.status == "PENDING")
            elif norm_status == "DRAFT":
                base_conds.append(Internship.status == "DRAFT")
            elif norm_status == "CLOSED":
                base_conds.append(Internship.status == "CLOSED")
            elif norm_status == "REJECTED":
                base_conds.append(Internship.status == "REJECTED")

        # Search filter
        if search and search.strip():
            q = f"%{search.strip()}%"
            base_conds.append(
                or_(
                    Internship.title.ilike(q),
                    Internship.internship_number.ilike(q),
                    Internship.work_mode.ilike(q),
                    Internship.location.ilike(q),
                    Internship.description.ilike(q),
                )
            )

        filter_clause = and_(*base_conds)

        # Count total
        count_stmt = select(func.count(Internship.id)).where(filter_clause)
        total = (await db.execute(count_stmt)).scalar() or 0

        # Query items
        stmt = (
            select(Internship)
            .options(selectinload(Internship.company))
            .where(filter_clause)
            .order_by(Internship.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await db.execute(stmt)
        internships = result.scalars().all()

        items = []
        for i in internships:
            app_count = await InternshipRepository.get_applicant_count_for_internship(
                db, i.id, i.internship_number
            )
            items.append({
                "id": i.id,
                "internship_number": i.internship_number,
                "company_id": i.company_id,
                "company_name": i.company.company_name if i.company else None,
                "title": i.title,
                "stipend_monthly": i.stipend_monthly,
                "stipend": i.stipend or f"₹{i.stipend_monthly:,} / month",
                "duration": i.duration,
                "work_mode": i.work_mode,
                "workMode": i.work_mode,
                "location": i.location,
                "number_of_interns": i.number_of_interns,
                "openings": i.number_of_interns,
                "description": i.description,
                "status": i.status,
                "applicantsCount": app_count,
                "candidate_count": app_count,
                "candidates_count": app_count,
                "rejection_reason": i.rejection_reason,
                "published_at": i.published_at.strftime("%Y-%m-%d %H:%M:%S") if i.published_at else None,
                "closed_at": i.closed_at.strftime("%Y-%m-%d %H:%M:%S") if i.closed_at else None,
                "postedOn": i.created_at.strftime("%Y-%m-%d") if i.created_at else None,
                "created_at": i.created_at.strftime("%Y-%m-%d %H:%M:%S") if i.created_at else None,
                "updated_at": i.updated_at.strftime("%Y-%m-%d %H:%M:%S") if i.updated_at else None,
            })

        return items, total

    @staticmethod
    async def get_internship_by_id(
        db: AsyncSession, internship_id: str
    ) -> Optional[Internship]:
        """Fetch internship by primary ID or internship_number."""
        stmt = (
            select(Internship)
            .options(selectinload(Internship.company))
            .where(
                or_(
                    Internship.id == internship_id,
                    Internship.internship_number == internship_id,
                )
            )
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_admin_internships(
        db: AsyncSession,
        status_filter: Optional[str] = "ALL",
        search: Optional[str] = None,
        company: Optional[str] = None,
        company_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Fetch paginated internships across all companies for Administrator governance."""
        conds = []

        if status_filter and status_filter.upper() != "ALL":
            conds.append(Internship.status == status_filter.upper())

        if company and company.strip() and company.strip().upper() != "ALL":
            conds.append(RecruiterProfile.company_name.ilike(f"%{company.strip()}%"))

        if company_id and company_id.strip() and company_id.strip().upper() != "ALL":
            conds.append(Internship.company_id == company_id.strip())

        if search and search.strip():
            q = f"%{search.strip()}%"
            conds.append(
                or_(
                    Internship.title.ilike(q),
                    Internship.internship_number.ilike(q),
                    Internship.location.ilike(q),
                    Internship.work_mode.ilike(q),
                    RecruiterProfile.company_name.ilike(q),
                )
            )

        filter_clause = and_(*conds) if conds else True

        count_stmt = (
            select(func.count(Internship.id))
            .join(RecruiterProfile, Internship.company_id == RecruiterProfile.id)
            .where(filter_clause)
        )
        total = (await db.execute(count_stmt)).scalar() or 0

        stmt = (
            select(Internship, RecruiterProfile)
            .join(RecruiterProfile, Internship.company_id == RecruiterProfile.id)
            .where(filter_clause)
            .order_by(Internship.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await db.execute(stmt)
        rows = result.all()

        items = []
        for intern, rec in rows:
            app_count = await InternshipRepository.get_applicant_count_for_internship(
                db, intern.id, intern.internship_number
            )
            items.append({
                "id": intern.id,
                "internship_number": intern.internship_number,
                "title": intern.title,
                "company_id": rec.id,
                "company_name": rec.company_name,
                "recruiter_name": rec.recruiter_name,
                "recruiter_email": rec.work_email,
                "recruiter_phone": rec.mobile_phone,
                "stipend_monthly": intern.stipend_monthly,
                "stipend": intern.stipend or f"₹{intern.stipend_monthly:,} / month",
                "duration": intern.duration,
                "work_mode": intern.work_mode,
                "location": intern.location,
                "number_of_interns": intern.number_of_interns,
                "description": intern.description,
                "status": intern.status,
                "applicants_count": app_count,
                "rejection_reason": intern.rejection_reason,
                "approved_by": intern.approved_by,
                "approved_at": intern.approved_at.strftime("%Y-%m-%d %H:%M:%S") if intern.approved_at else None,
                "published_at": intern.published_at.strftime("%Y-%m-%d %H:%M:%S") if intern.published_at else None,
                "created_at": intern.created_at.strftime("%Y-%m-%d %H:%M:%S") if intern.created_at else "",
            })

        return items, total

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
