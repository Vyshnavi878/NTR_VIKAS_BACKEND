import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy import select, or_, and_, desc
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job_mela import JobMela, JobMelaCompanyParticipation
from app.models.recruiter import RecruiterProfile
from app.models.application import CandidateApplication
from app.models.interview import Interview


class JobMelaRepository:
    """
    Async database operations for Job Melas and Company Participation requests.
    """

    @staticmethod
    async def get_recruiter_profile_by_user_id(
        db: AsyncSession, user_id: str
    ) -> Optional[RecruiterProfile]:
        """Retrieve recruiter profile from authenticated user ID."""
        stmt = select(RecruiterProfile).where(RecruiterProfile.user_id == user_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_all_published_melas(db: AsyncSession) -> List[JobMela]:
        """Retrieve all upcoming / published Job Melas for dropdown selection."""
        stmt = (
            select(JobMela)
            .where(JobMela.status.in_(["PUBLISHED", "ACTIVE", "REGISTRATION_OPEN"]))
            .order_by(JobMela.event_date.asc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_job_mela_by_id_or_title(
        db: AsyncSession,
        mela_id: Optional[str] = None,
        title: Optional[str] = None,
    ) -> Optional[JobMela]:
        """Find Job Mela by exact ID, mela_number, or title."""
        conditions = []
        if mela_id:
            conditions.append(JobMela.id == mela_id)
            conditions.append(JobMela.mela_number == mela_id)
        if title:
            conditions.append(JobMela.title == title.strip())
            conditions.append(JobMela.title.ilike(f"%{title.strip()}%"))

        if not conditions:
            return None

        stmt = select(JobMela).where(or_(*conditions))
        result = await db.execute(stmt)
        return result.scalars().first()

    @staticmethod
    async def get_participation(
        db: AsyncSession, job_mela_id: str, company_id: str
    ) -> Optional[JobMelaCompanyParticipation]:
        """Check if company has already registered for a specific Job Mela."""
        stmt = select(JobMelaCompanyParticipation).where(
            JobMelaCompanyParticipation.job_mela_id == job_mela_id,
            JobMelaCompanyParticipation.company_id == company_id,
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def create_participation(
        db: AsyncSession,
        job_mela_id: str,
        company_id: str,
        openings: Optional[str] = None,
        target_hires: int = 1,
    ) -> JobMelaCompanyParticipation:
        """Create a new PENDING participation request."""
        now = datetime.now(timezone.utc)
        part_id = f"part-{uuid.uuid4().hex[:10]}"
        participation = JobMelaCompanyParticipation(
            id=part_id,
            job_mela_id=job_mela_id,
            company_id=company_id,
            openings=openings,
            target_hires=target_hires or 1,
            status="PENDING",
            booth_number="Awaiting Admin Allocation",
            booth_location="Pending Stall Allocation",
            registered_at=now,
            created_at=now,
            updated_at=now,
        )
        db.add(participation)
        await db.commit()
        await db.refresh(participation)
        return participation

    @staticmethod
    async def get_recruiter_job_melas(
        db: AsyncSession,
        recruiter_id: str,
        status_filter: Optional[str] = "ALL",
        search: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch Job Melas with participation context for the authenticated recruiter.
        Returns unified records matching both mock format and database schema.
        """
        # Outer join JobMela with JobMelaCompanyParticipation for this recruiter
        stmt = (
            select(JobMela, JobMelaCompanyParticipation)
            .outerjoin(
                JobMelaCompanyParticipation,
                and_(
                    JobMelaCompanyParticipation.job_mela_id == JobMela.id,
                    JobMelaCompanyParticipation.company_id == recruiter_id,
                ),
            )
            .order_by(JobMela.event_date.asc())
        )

        result = await db.execute(stmt)
        rows = result.all()

        events: List[Dict[str, Any]] = []
        for mela, part in rows:
            part_status = part.status if part else "NOT_REGISTERED"

            # Apply tab filter: 'ALL', 'APPROVED', 'PENDING'
            if status_filter == "APPROVED" and part_status != "APPROVED":
                continue
            if status_filter == "PENDING" and part_status != "PENDING":
                continue

            # Format positions list
            positions_str = part.openings if (part and part.openings) else ""
            positions_list = [p.strip() for p in positions_str.split(",") if p.strip()] if positions_str else []

            booth_num = part.booth_number if part else None
            if not booth_num or booth_num == "None":
                booth_num = "Awaiting Booth" if part_status == "PENDING" else "N/A"

            event_dict = {
                "id": mela.id,
                "participation_id": part.id if part else None,
                "mela_number": mela.mela_number,
                "title": mela.title,
                "date": mela.event_date,
                "time": f"{mela.start_time or '09:00 AM'} - {mela.end_time or '05:30 PM'}",
                "venue": mela.venue,
                "city": mela.city,
                "district": mela.district,
                "state": "Andhra Pradesh",
                "participation_status": part_status,
                "status": part_status,
                "booth_number": booth_num,
                "boothNumber": booth_num,
                "booth_location": part.booth_location if part else None,
                "positions": positions_str,
                "showcasedPositions": positions_list,
                "target_hires": part.target_hires if part else 0,
                "expectedHires": part.target_hires if part else 0,
                "registeredCandidatesAtBooth": 0,
                "candidatesCount": 0,
                "spotInterviewsConducted": 0,
                "interviewsCount": 0,
                "spotOffersGiven": 0,
                "spotOffers": 0,
                "registered_at": part.registered_at.strftime("%Y-%m-%d %H:%M:%S") if (part and part.registered_at) else None,
            }

            # Optional search filtering
            if search and search.strip():
                q = search.lower().strip()
                matches = (
                    q in event_dict["title"].lower()
                    or q in event_dict["venue"].lower()
                    or q in event_dict["city"].lower()
                    or q in str(event_dict["boothNumber"]).lower()
                    or any(q in p.lower() for p in positions_list)
                    or q in positions_str.lower()
                )
                if not matches:
                    continue

            events.append(event_dict)

        return events

    @staticmethod
    async def get_admin_participations(
        db: AsyncSession,
        status_filter: Optional[str] = "ALL",
        search: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch all company participation requests across all Job Melas for Administrator review.
        """
        stmt = (
            select(JobMelaCompanyParticipation, JobMela, RecruiterProfile)
            .join(JobMela, JobMelaCompanyParticipation.job_mela_id == JobMela.id)
            .join(RecruiterProfile, JobMelaCompanyParticipation.company_id == RecruiterProfile.id)
            .order_by(JobMelaCompanyParticipation.created_at.desc())
        )

        result = await db.execute(stmt)
        rows = result.all()

        requests: List[Dict[str, Any]] = []
        for part, mela, rec in rows:
            if status_filter and status_filter != "ALL" and part.status != status_filter:
                continue

            hiring_positions = [p.strip() for p in (part.openings or "").split(",") if p.strip()]

            item = {
                "id": part.id,
                "participation_id": part.id,
                "company_id": rec.id,
                "company_name": rec.company_name,
                "companyName": rec.company_name,
                "recruiter_name": rec.recruiter_name,
                "recruiterName": rec.recruiter_name,
                "recruiter_phone": rec.mobile_phone,
                "recruiterPhone": rec.mobile_phone,
                "job_mela_id": mela.id,
                "event_name": mela.title,
                "eventName": mela.title,
                "event_date": mela.event_date,
                "status": part.status,
                "allocated_booth": part.booth_number or "Awaiting Allocation",
                "allocatedBooth": part.booth_number or "Awaiting Allocation",
                "openings": part.openings,
                "hiring_positions": hiring_positions,
                "hiringPositions": hiring_positions,
                "target_hires": part.target_hires,
                "expected_hires": part.target_hires,
                "expectedHires": part.target_hires,
                "registered_at": part.registered_at.strftime("%Y-%m-%d %H:%M:%S") if part.registered_at else "",
                "requested_date": part.registered_at.strftime("%Y-%m-%d") if part.registered_at else "",
                "requestedDate": part.registered_at.strftime("%Y-%m-%d") if part.registered_at else "",
                "rejection_reason": part.rejection_reason,
            }

            if search and search.strip():
                q = search.lower().strip()
                if (
                    q not in item["companyName"].lower()
                    and q not in item["eventName"].lower()
                    and q not in item["recruiterName"].lower()
                ):
                    continue

            requests.append(item)

        return requests

    @staticmethod
    async def get_participation_by_id(
        db: AsyncSession, participation_id: str
    ) -> Optional[JobMelaCompanyParticipation]:
        """Fetch participation request by primary key ID."""
        stmt = select(JobMelaCompanyParticipation).where(
            JobMelaCompanyParticipation.id == participation_id
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_approved_companies_for_mela(
        db: AsyncSession, job_mela_id: str
    ) -> List[Dict[str, Any]]:
        """Fetch all APPROVED participating companies for a Job Mela (for candidate portal)."""
        stmt = (
            select(JobMelaCompanyParticipation, RecruiterProfile)
            .join(RecruiterProfile, JobMelaCompanyParticipation.company_id == RecruiterProfile.id)
            .where(
                JobMelaCompanyParticipation.job_mela_id == job_mela_id,
                JobMelaCompanyParticipation.status == "APPROVED",
            )
        )
        result = await db.execute(stmt)
        rows = result.all()

        companies = []
        for part, rec in rows:
            companies.append({
                "company_id": rec.id,
                "company_name": rec.company_name,
                "industry": rec.primary_industry,
                "openings": part.openings,
                "target_hires": part.target_hires,
                "booth_number": part.booth_number,
                "status": "APPROVED",
            })
        return companies
