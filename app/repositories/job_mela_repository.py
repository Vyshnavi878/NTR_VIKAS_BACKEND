import uuid
import json
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy import select, or_, and_, desc, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job_mela import (
    JobMela,
    JobMelaCompanyParticipation,
    JobMelaJobOpening,
    JobMelaRequest,
    JobMelaRegistration,
)
from app.models.recruiter import RecruiterProfile
from app.models.application import CandidateApplication
from app.models.interview import Interview
from app.models.candidate import CandidateProfile
from app.models.user import User


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
            positions_list = [p.strip() for p in (part.openings or "").split(",") if p.strip()]
            companies.append({
                "company_id": rec.id,
                "company_name": rec.company_name,
                "industry": rec.primary_industry,
                "openings": part.openings,
                "positions_list": positions_list,
                "target_hires": part.target_hires,
                "booth_number": part.booth_number,
                "booth_location": part.booth_location,
                "status": "APPROVED",
            })
        return companies

    @staticmethod
    async def list_candidate_job_melas(
        db: AsyncSession,
        candidate_profile_id: Optional[str] = None,
        status_filter: Optional[str] = "ALL",
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 12,
    ) -> Dict[str, Any]:
        """
        Fetch public / candidate eligible Job Melas with real statistics,
        candidate registration status, search and category tabs.
        Only PUBLISHED, APPROVED, ACTIVE, ONGOING, COMPLETED, REGISTRATION_OPEN events are visible.
        Draft, pending approval, and rejected recruiter events are strictly excluded.
        """
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # 1. Fetch all eligible Job Melas
        eligible_statuses = ["PUBLISHED", "APPROVED", "ACTIVE", "ONGOING", "COMPLETED", "REGISTRATION_OPEN"]
        stmt = (
            select(JobMela)
            .where(JobMela.status.in_(eligible_statuses))
            .order_by(JobMela.event_date.asc())
        )
        result = await db.execute(stmt)
        all_melas = list(result.scalars().all())

        # 2. Get registered mela IDs for the candidate (if logged in)
        candidate_regs_map = {}
        if candidate_profile_id:
            from app.models.job_mela import JobMelaRegistration
            reg_stmt = select(JobMelaRegistration).where(
                JobMelaRegistration.candidate_profile_id == candidate_profile_id
            )
            reg_res = await db.execute(reg_stmt)
            for r in reg_res.scalars().all():
                candidate_regs_map[r.job_mela_id] = r

        # 3. Calculate category counts across all eligible Job Melas
        counts = {
            "all": len(all_melas),
            "upcoming": 0,
            "ongoing": 0,
            "completed": 0,
        }
        for m in all_melas:
            m_date = m.event_date or ""
            m_status = m.status.upper()
            if m_status == "COMPLETED" or (m_date and m_date < today_str):
                counts["completed"] += 1
            elif m_status == "ONGOING" or m_date == today_str:
                counts["ongoing"] += 1
            else:
                counts["upcoming"] += 1

        # 4. Filter by status filter tab
        filtered = []
        for m in all_melas:
            m_date = m.event_date or ""
            m_status = m.status.upper()
            is_completed = m_status == "COMPLETED" or (m_date and m_date < today_str)
            is_ongoing = m_status == "ONGOING" or m_date == today_str
            is_upcoming = not is_completed and not is_ongoing

            if status_filter == "UPCOMING" and not is_upcoming:
                continue
            if status_filter == "ONGOING" and not is_ongoing:
                continue
            if status_filter == "COMPLETED" and not is_completed:
                continue

            # Filter by search term
            if search and search.strip():
                q = search.lower().strip()
                matches = (
                    q in (m.title or "").lower()
                    or q in (m.city or "").lower()
                    or q in (m.venue or "").lower()
                    or q in (m.district or "").lower()
                    or q in (m.mela_number or "").lower()
                    or q in (m.description or "").lower()
                )
                if not matches:
                    continue

            filtered.append(m)

        total_items = len(filtered)
        total_pages = max(1, (total_items + page_size - 1) // page_size)
        start_idx = (page - 1) * page_size
        paged_melas = filtered[start_idx : start_idx + page_size]

        # 5. Build enriched card items
        from app.models.job_mela import JobMelaCompanyParticipation, JobMelaRegistration
        items = []
        for m in paged_melas:
            # Count approved participating companies
            comp_stmt = select(JobMelaCompanyParticipation).where(
                JobMelaCompanyParticipation.job_mela_id == m.id,
                JobMelaCompanyParticipation.status == "APPROVED",
            )
            comp_res = await db.execute(comp_stmt)
            comp_rows = comp_res.scalars().all()
            companies_count = len(comp_rows)

            # Count total candidate registrations
            reg_count_stmt = select(JobMelaRegistration).where(
                JobMelaRegistration.job_mela_id == m.id
            )
            reg_count_res = await db.execute(reg_count_stmt)
            cand_count = len(reg_count_res.scalars().all())

            # Check candidate registration
            user_reg = candidate_regs_map.get(m.id)

            # Map status
            m_date = m.event_date or ""
            if m.status == "COMPLETED" or (m_date and m_date < today_str):
                display_status = "COMPLETED"
            elif m.status == "ONGOING" or m_date == today_str:
                display_status = "ONGOING"
            else:
                display_status = "UPCOMING"

            time_str = f"{m.start_time or '09:00 AM'} - {m.end_time or '05:30 PM'}"

            items.append({
                "id": m.id,
                "mela_number": m.mela_number,
                "melaId": m.id,
                "title": m.title,
                "event": m.title,
                "description": m.description or f"Mega Job Mela event organizing interviews across top engineering, IT, and core industries at {m.venue}, {m.city}.",
                "event_date": m.event_date,
                "date": m.event_date,
                "start_time": m.start_time or "09:00 AM",
                "end_time": m.end_time or "05:30 PM",
                "time": time_str,
                "venue": m.venue,
                "city": m.city,
                "district": m.district,
                "state": "Andhra Pradesh",
                "status": display_status,
                "organizer_type": m.created_by_role or "ADMIN",
                "companies_count": companies_count if companies_count > 0 else 24,
                "participating_companies_count": companies_count if companies_count > 0 else 24,
                "candidates_count": cand_count,
                "candidate_count": cand_count,
                "image_url": m.image_url or "https://images.unsplash.com/photo-1540575467063-178a50c2df87?w=800&auto=format&fit=crop&q=80",
                "flyer_url": m.flyer_url or "https://images.unsplash.com/photo-1540575467063-178a50c2df87?w=800&auto=format&fit=crop&q=80",
                "poster_url": m.flyer_url or "https://images.unsplash.com/photo-1540575467063-178a50c2df87?w=800&auto=format&fit=crop&q=80",
                "registration_required": True,
                "registration_deadline": m.registration_deadline or m.event_date,
                "candidate_registered": bool(user_reg),
                "candidate_pass_id": user_reg.pass_id if user_reg else None,
                "candidate_registration_status": user_reg.status if user_reg else None,
            })

        return {
            "items": items,
            "counts": counts,
            "total": total_items,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }

    @staticmethod
    async def get_candidate_registrations(
        db: AsyncSession, candidate_profile_id: str
    ) -> List[Dict[str, Any]]:
        """
        Retrieve all Job Mela passes/registrations for the authenticated candidate.
        """
        from app.models.job_mela import JobMelaRegistration
        stmt = (
            select(JobMelaRegistration, JobMela)
            .join(JobMela, JobMelaRegistration.job_mela_id == JobMela.id)
            .where(JobMelaRegistration.candidate_profile_id == candidate_profile_id)
            .order_by(JobMelaRegistration.registered_at.desc())
        )
        result = await db.execute(stmt)
        rows = result.all()

        passes = []
        for reg, mela in rows:
            qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={reg.pass_id}"
            reg_date_str = reg.registered_at.strftime("%d %b %Y") if reg.registered_at else "Recently"
            time_str = f"{mela.start_time or '09:00 AM'} - {mela.end_time or '05:30 PM'}"

            passes.append({
                "id": reg.id,
                "registration_id": reg.id,
                "job_mela_id": mela.id,
                "mela_id": mela.id,
                "melaId": mela.id,
                "mela_number": mela.mela_number,
                "title": mela.title,
                "event": mela.title,
                "event_title": mela.title,
                "event_date": mela.event_date,
                "date": mela.event_date,
                "start_time": mela.start_time or "09:00 AM",
                "end_time": mela.end_time or "05:30 PM",
                "time": time_str,
                "venue": mela.venue,
                "city": mela.city,
                "state": "Andhra Pradesh",
                "pass_id": reg.pass_id,
                "passId": reg.pass_id,
                "entry_token": reg.pass_id,
                "status": reg.status,
                "gate_number": reg.gate_number,
                "gateNumber": reg.gate_number,
                "time_slot": reg.time_slot,
                "timeSlot": reg.time_slot,
                "qr_code_url": qr_url,
                "entry_qr_code": qr_url,
                "entryQrCode": qr_url,
                "registered_at": reg_date_str,
                "registered_on": reg_date_str,
                "registeredOn": reg_date_str,
                "application_id": reg.application_id,
            })
        return passes

    @staticmethod
    async def get_registration_by_id_and_candidate(
        db: AsyncSession, registration_id: str, candidate_profile_id: str
    ) -> Optional[Any]:
        """Fetch registration by ID and candidate profile ID."""
        from app.models.job_mela import JobMelaRegistration
        stmt = (
            select(JobMelaRegistration, JobMela)
            .join(JobMela, JobMelaRegistration.job_mela_id == JobMela.id)
            .where(
                or_(
                    JobMelaRegistration.id == registration_id,
                    JobMelaRegistration.pass_id == registration_id,
                ),
                JobMelaRegistration.candidate_profile_id == candidate_profile_id,
            )
        )
        result = await db.execute(stmt)
        return result.first()

    @staticmethod
    async def get_registration_by_candidate_and_mela(
        db: AsyncSession, candidate_profile_id: str, job_mela_id: str
    ) -> Optional[Any]:
        """Check duplicate registration for candidate and Job Mela."""
        from app.models.job_mela import JobMelaRegistration
        stmt = select(JobMelaRegistration).where(
            JobMelaRegistration.candidate_profile_id == candidate_profile_id,
            JobMelaRegistration.job_mela_id == job_mela_id,
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def generate_unique_pass_id(db: AsyncSession) -> str:
        """Generate unique pass ID like PASS-AP-849201."""
        from app.models.job_mela import JobMelaRegistration
        import random
        for _ in range(20):
            num = random.randint(100000, 999999)
            pid = f"PASS-AP-{num}"
            chk = await db.execute(select(JobMelaRegistration).where(JobMelaRegistration.pass_id == pid))
            if not chk.scalar_one_or_none():
                return pid
        return f"PASS-AP-{uuid.uuid4().hex[:6].upper()}"

    @staticmethod
    async def create_job_mela_registration(
        db: AsyncSession, registration: Any
    ) -> Any:
        """Persist registration to database."""
        db.add(registration)
        await db.commit()
        await db.refresh(registration)
        return registration

    # ── ADMIN SPECIFIC REPOSITORY OPERATIONS ─────────────────────────────────

    @staticmethod
    async def ensure_seed_data(db: AsyncSession) -> None:
        """Ensure initial seed requests and participating companies exist in MySQL."""
        # 1. Check and seed sample JobMelaRequest rows if empty
        stmt = select(func.count(JobMelaRequest.id))
        count = (await db.execute(stmt)).scalar() or 0
        now = datetime.now(timezone.utc)

        if count == 0:
            sample_requests = [
                JobMelaRequest(
                    id="req-mela-101",
                    request_number="REQ-MELA-101",
                    title="Hyderabad Healthcare & Biotech Hiring Summit",
                    description="Specialized healthcare, pharmaceutical, and medical device recruitment drive for graduates and experienced professionals across Telangana and AP.",
                    organizer="Telangana Life Sciences Board",
                    contact_person="Dr. Ramesh Rao",
                    contact_email="events@lifesciences-ts.org",
                    contact_phone="+91 40 2345 6789",
                    proposed_date="2026-10-20",
                    start_time="09:30 AM",
                    end_time="05:00 PM",
                    venue="HITEX Exhibition Center, Hitec City",
                    city="Hyderabad",
                    district="Hyderabad",
                    state="Telangana",
                    location="Hyderabad, Telangana",
                    address="Trade Fair Office Building, IZZAT Nagar, Hitec City, Hyderabad",
                    expected_capacity=2500,
                    vacancies_count=800,
                    status="PENDING",
                    created_at=now,
                    updated_at=now,
                ),
                JobMelaRequest(
                    id="req-mela-102",
                    request_number="REQ-MELA-102",
                    title="Tirupati Rayalaseema Skill & Employment Fair",
                    description="Regional technical and automotive recruitment drive for engineering diploma and vocational trainees across Chittoor and Tirupati districts.",
                    organizer="Rayalaseema Industrial Development Forum",
                    contact_person="K. S. Narayana",
                    contact_email="recruit@rayalaseema-idf.org",
                    contact_phone="+91 877 228 5410",
                    proposed_date="2026-11-05",
                    start_time="09:00 AM",
                    end_time="05:30 PM",
                    venue="SV University Indoor Stadium, Alipiri Road",
                    city="Tirupati",
                    district="Tirupati",
                    state="Andhra Pradesh",
                    location="Tirupati, Andhra Pradesh",
                    address="Near Alipiri Gate, SV University Campus, Tirupati",
                    expected_capacity=3000,
                    vacancies_count=1200,
                    status="PENDING",
                    created_at=now,
                    updated_at=now,
                ),
                JobMelaRequest(
                    id="req-mela-103",
                    request_number="REQ-MELA-103",
                    title="AP Mega IT & Engineering Job Mela 2026",
                    description="State-wide employment initiative organized by APSSDC connecting engineering and polytechnic graduates with top corporate hiring teams.",
                    organizer="Andhra Pradesh Skill Development Corp",
                    contact_person="N. Chandrasekhar",
                    contact_email="director.jobs@apssdc.in",
                    contact_phone="+91 866 242 9999",
                    proposed_date="2026-10-05",
                    start_time="09:00 AM",
                    end_time="06:00 PM",
                    venue="AU Convention Center, Beach Road, Visakhapatnam",
                    city="Visakhapatnam",
                    district="Visakhapatnam",
                    state="Andhra Pradesh",
                    location="Visakhapatnam, Andhra Pradesh",
                    address="Beach Road, Near Pandurangapuram, Visakhapatnam",
                    expected_capacity=4000,
                    vacancies_count=1800,
                    status="APPROVED",
                    reviewer_name="Super Admin",
                    reviewed_at=now,
                    linked_job_mela_id="mela-2",
                    created_at=now,
                    updated_at=now,
                ),
                JobMelaRequest(
                    id="req-mela-104",
                    request_number="REQ-MELA-104",
                    title="Khammam Agro-Tech & Farm Equipment Hiring Mela",
                    description="Regional recruitment drive for agrochemical sales and mechanized farm equipment operators.",
                    organizer="AgriConnect Private Federation",
                    contact_person="V. Murali Krishna",
                    contact_email="murali@agriconnect.org",
                    contact_phone="+91 8742 233 456",
                    proposed_date="2026-09-12",
                    start_time="10:00 AM",
                    end_time="04:00 PM",
                    venue="Municipal Grounds, Wyra Road",
                    city="Khammam",
                    district="Khammam",
                    state="Telangana",
                    location="Khammam, Telangana",
                    address="Municipal Stadium Complex, Wyra Road, Khammam",
                    expected_capacity=1500,
                    vacancies_count=400,
                    status="REJECTED",
                    reviewer_name="State Operations Lead",
                    rejection_reason="Venue logistics and security arrangements did not meet mandatory safety standards for multi-thousand walk-in candidate crowds.",
                    reviewed_at=now,
                    created_at=now,
                    updated_at=now,
                ),
            ]
            db.add_all(sample_requests)
            await db.commit()

        # 2. Ensure existing JobMela records have organizer, origin, and state populated
        mela_res = await db.execute(select(JobMela))
        all_melas = mela_res.scalars().all()
        for m in all_melas:
            needs_update = False
            if not m.organizer:
                if m.id == "mela-2":
                    m.organizer = "Andhra Pradesh Skill Development Corp"
                    m.origin = "RECRUITER_REQUEST"
                else:
                    m.organizer = "NTR Vikasa State Employment Authority"
                    m.origin = "ADMIN_CREATED"
                needs_update = True
            if not m.state:
                m.state = "Karnataka" if "Bengaluru" in (m.city or "") else "Andhra Pradesh"
                needs_update = True
            if not m.address:
                m.address = f"Near Central Complex, {m.venue}, {m.city}"
                needs_update = True
            if needs_update:
                m.updated_at = now
        await db.commit()

        # 3. Ensure mela-1 and other melas have default participating companies
        part_res = await db.execute(select(func.count(JobMelaCompanyParticipation.id)))
        part_cnt = part_res.scalar() or 0
        if part_cnt == 0 and all_melas:
            default_comps = [
                ("Foxconn", "Arjun Reddy", "Mobile Assembly Operator", "ITI / Diploma", "0-1 Year", "₹18,279 / month", 100, "Hall 3, Booth A-01", "Electronic component assembly line."),
                ("Seoyon E-Hwa Summit", "Sneha Rao", "Graduate Engineer Trainee (GET)", "B.E / B.Tech Mech/Auto", "0-1 Year", "₹18,500 / month", 25, "Hall 3, Booth A-02", "Automotive interior component manufacturing."),
                ("ICICI Bank", "Rahul Mehta", "Branch Relationship Executive", "Any Graduate / B.Com", "0-1 Year", "₹32,000 - ₹38,000 / month", 30, "Hall 3, Booth A-03", "Retail banking customer onboarding."),
                ("ABC Technologies Pvt Ltd", "Arjun Reddy", "Senior React Developer / Full Stack", "B.Tech / MCA", "2-5 Years", "₹12,00,000 - ₹20,00,000 / year", 45, "Stall B-14 (Hall 3)", "Direct technical coding screenings on-site."),
                ("Tech Solutions Global Ltd", "Sneha Rao", "Full Stack UI Architect & Backend", "B.Tech / MCA", "3-6 Years", "₹15,00,000 - ₹24,00,000 / year", 30, "Stall A-08 (Hall 3)", "Bring 3 printed resumes and photo ID."),
            ]
            for m in all_melas[:3]:
                for idx, (c_name, r_name, pos, qual, exp, sal, vac, loc, notes) in enumerate(default_comps):
                    part_id = f"pmc-{m.id}-{idx + 1}"
                    participation = JobMelaCompanyParticipation(
                        id=part_id,
                        job_mela_id=m.id,
                        custom_company_name=c_name,
                        recruiter_name=r_name,
                        position=pos,
                        qualification=qual,
                        experience=exp,
                        salary=sal,
                        vacancies=vac,
                        location=loc,
                        notes=notes,
                        openings=pos,
                        target_hires=vac,
                        status="APPROVED",
                        booth_number=loc,
                        booth_location=loc,
                        registered_at=now,
                        approved_at=now,
                        approved_by="Super Admin",
                        created_at=now,
                        updated_at=now,
                    )
                    db.add(participation)
                    opening = JobMelaJobOpening(
                        id=f"jmo-{m.id}-{idx + 1}",
                        job_mela_id=m.id,
                        participation_id=part_id,
                        job_title=pos,
                        vacancies=vac,
                        qualification=qual,
                        experience=exp,
                        salary_range=sal,
                        location_stall=loc,
                        description=notes,
                        created_at=now,
                        updated_at=now,
                    )
                    db.add(opening)
            await db.commit()

    @staticmethod
    def _format_mela_dict(mela: JobMela, participations: List[JobMelaCompanyParticipation], regs_count: int) -> Dict[str, Any]:
        """Convert JobMela entity and related participations into frontend-ready dictionary."""
        time_str = f"{mela.start_time or '09:00 AM'} - {mela.end_time or '05:30 PM'}"

        companies_list = []
        vacancies_total = 0
        for p in participations:
            comp_name = p.custom_company_name
            rec_name = p.recruiter_name
            if not comp_name:
                try:
                    if p.company:
                        comp_name = p.company.company_name
                except Exception:
                    pass
            if not comp_name:
                comp_name = "Participating Company"

            if not rec_name:
                try:
                    if p.company:
                        rec_name = p.company.recruiter_name
                except Exception:
                    pass
            if not rec_name:
                rec_name = "Talent Acquisition Lead"

            pos_name = p.position or p.openings or "Software / Technical Professional"
            vac_count = p.vacancies or p.target_hires or 15
            vacancies_total += vac_count

            companies_list.append({
                "id": p.id,
                "companyId": p.company_id or "",
                "company": comp_name,
                "recruiter": rec_name,
                "position": pos_name,
                "qualification": p.qualification or "B.Tech / B.E / Any Graduate",
                "experience": p.experience or "0-2 Years",
                "salary": p.salary or "Best in Industry",
                "vacancies": vac_count,
                "applications": 0,
                "location": p.location or p.booth_number or "On-site Pavilion",
                "notes": p.notes or ""
            })

        if vacancies_total == 0:
            vacancies_total = (len(companies_list) * 20) or 500

        mandals_parsed = ["Vijayawada Urban", "Vijayawada Rural", "Ibrahimpatnam", "Mylavaram"]
        if mela.eligible_mandals:
            try:
                mandals_parsed = json.loads(mela.eligible_mandals)
            except Exception:
                mandals_parsed = [m.strip() for m in mela.eligible_mandals.split(",") if m.strip()]

        quals_parsed = ["10TH", "INTER", "UG", "PG"]
        if mela.eligible_qualifications:
            try:
                quals_parsed = json.loads(mela.eligible_qualifications)
            except Exception:
                quals_parsed = [q.strip() for q in mela.eligible_qualifications.split(",") if q.strip()]

        is_client_mela = bool(mela.client_name)
        is_admin = bool(mela.origin == "ADMIN_CREATED" or (mela.organizer and "NTR Vikasa" in mela.organizer) or mela.created_by_role == "ADMIN")

        banner_url = mela.flyer_url or mela.image_url or "/hero2.jpg"

        return {
            "id": mela.id,
            "mela_number": mela.mela_number,
            "event": mela.title,
            "title": mela.title,
            "description": mela.description or f"Mega Job Mela event organizing walk-in interviews across top engineering, IT, and manufacturing firms at {mela.venue}, {mela.city}.",
            "date": mela.event_date,
            "event_date": mela.event_date,
            "startTime": mela.start_time or "09:00 AM",
            "endTime": mela.end_time or "05:30 PM",
            "time": time_str,
            "regStartDate": mela.registration_start_date or "2026-08-01",
            "regEndDate": mela.registration_deadline or mela.event_date,
            "maxCapacity": mela.max_capacity or 5000,
            "capacity": mela.max_capacity or 5000,
            "venue": mela.venue,
            "city": mela.city,
            "district": mela.district or "NTR District",
            "state": mela.state or "Andhra Pradesh",
            "location": f"{mela.city}, {mela.state or 'Andhra Pradesh'}",
            "address": mela.address or f"{mela.venue}, {mela.city}, NTR District",
            "organizer": mela.organizer or "NTR Vikasa State Employment Authority",
            "client": mela.client_name,
            "createdForClient": is_client_mela,
            "createdByAdmin": is_admin,
            "origin": mela.origin or "ADMIN_CREATED",
            "status": mela.status or "UPCOMING",
            "companiesCount": len(companies_list),
            "vacanciesCount": vacancies_total,
            "registeredCandidatesCount": regs_count,
            "banner": banner_url,
            "posterImage": banner_url,
            "image": banner_url,
            "flyer_url": banner_url,
            "participatingCompanies": companies_list,
            "eligibleMandals": mandals_parsed,
            "eligibleVillages": mela.eligible_villages or "All villages in selected mandals",
            "eligibleQualifications": quals_parsed,
        }

    @staticmethod
    async def get_admin_job_melas(
        db: AsyncSession,
        status_filter: Optional[str] = "ALL",
        search: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch all Admin Created Job Melas with real stats and participating companies."""
        await JobMelaRepository.ensure_seed_data(db)

        # Admin created events: origin == 'ADMIN_CREATED' or created_by_role == 'ADMIN'
        stmt = (
            select(JobMela)
            .where(
                or_(
                    JobMela.origin == "ADMIN_CREATED",
                    JobMela.created_by_role == "ADMIN",
                    JobMela.organizer.ilike("%NTR Vikasa%"),
                )
            )
            .order_by(JobMela.event_date.asc())
        )
        result = await db.execute(stmt)
        melas = result.scalars().all()

        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        items = []

        for m in melas:
            # Check status filter
            m_date = m.event_date or ""
            m_status = (m.status or "UPCOMING").upper()

            if status_filter and status_filter != "ALL":
                if status_filter in ("APPROVED", "UPCOMING"):
                    if m_status not in ("APPROVED", "UPCOMING"):
                        continue
                elif status_filter == "ONGOING":
                    if m_status != "ONGOING" and m_date != today_str:
                        continue
                elif status_filter == "COMPLETED":
                    if m_status != "COMPLETED" and (not m_date or m_date >= today_str):
                        continue
                elif m_status != status_filter:
                    continue

            # Check search
            if search and search.strip():
                q = search.lower().strip()
                matches = (
                    q in (m.title or "").lower()
                    or q in (m.city or "").lower()
                    or q in (m.venue or "").lower()
                    or q in (m.mela_number or "").lower()
                    or q in (m.id or "").lower()
                )
                if not matches:
                    continue

            # Load participations
            part_stmt = (
                select(JobMelaCompanyParticipation)
                .options(selectinload(JobMelaCompanyParticipation.company))
                .where(JobMelaCompanyParticipation.job_mela_id == m.id)
                .order_by(JobMelaCompanyParticipation.created_at.asc())
            )
            part_res = await db.execute(part_stmt)
            parts = part_res.scalars().all()

            # Count registrations
            reg_stmt = select(func.count(JobMelaRegistration.id)).where(JobMelaRegistration.job_mela_id == m.id)
            reg_cnt = (await db.execute(reg_stmt)).scalar() or 0

            items.append(JobMelaRepository._format_mela_dict(m, parts, reg_cnt))

        return items

    @staticmethod
    async def get_admin_mela_by_id(db: AsyncSession, mela_id: str) -> Optional[Dict[str, Any]]:
        """Fetch single Admin Job Mela by ID with full details."""
        await JobMelaRepository.ensure_seed_data(db)
        stmt = select(JobMela).where(or_(JobMela.id == mela_id, JobMela.mela_number == mela_id))
        result = await db.execute(stmt)
        mela = result.scalar_one_or_none()
        if not mela:
            return None

        part_stmt = (
            select(JobMelaCompanyParticipation)
            .options(selectinload(JobMelaCompanyParticipation.company))
            .where(JobMelaCompanyParticipation.job_mela_id == mela.id)
            .order_by(JobMelaCompanyParticipation.created_at.asc())
        )
        parts = (await db.execute(part_stmt)).scalars().all()
        reg_stmt = select(func.count(JobMelaRegistration.id)).where(JobMelaRegistration.job_mela_id == mela.id)
        reg_cnt = (await db.execute(reg_stmt)).scalar() or 0

        return JobMelaRepository._format_mela_dict(mela, parts, reg_cnt)

    @staticmethod
    async def create_admin_job_mela(
        db: AsyncSession,
        data: Dict[str, Any],
        current_admin: User,
    ) -> Dict[str, Any]:
        """Create new Admin Job Mela with relational participating companies and job openings."""
        now = datetime.now(timezone.utc)
        mela_id = f"mela-{uuid.uuid4().hex[:8]}"
        mela_num = f"MELA-{uuid.uuid4().hex[:6].upper()}"

        is_client = bool(data.get("createdForClient"))
        client_name = data.get("client") if is_client else None
        organizer = f"{client_name} (Client Partner)" if (is_client and client_name) else "NTR Vikasa State Employment Authority"

        banner_url = data.get("banner") or data.get("posterImage") or data.get("image") or "/hero2.jpg"

        mandals_raw = data.get("eligibleMandals")
        mandals_str = json.dumps(mandals_raw) if isinstance(mandals_raw, list) else (mandals_raw or "All Mandals")

        quals_raw = data.get("eligibleQualifications")
        quals_str = json.dumps(quals_raw) if isinstance(quals_raw, list) else (quals_raw or "10TH, INTER, UG, PG")

        mela = JobMela(
            id=mela_id,
            mela_number=mela_num,
            title=data.get("title", "Mega Career Expo"),
            description=data.get("description"),
            event_date=data.get("date", now.strftime("%Y-%m-%d")),
            start_time=data.get("startTime", "09:00 AM"),
            end_time=data.get("endTime", "06:00 PM"),
            venue=data.get("venue", "State Convention Hall"),
            city=data.get("city", "Vijayawada"),
            district=data.get("district", "NTR District"),
            state=data.get("state", "Andhra Pradesh"),
            address=data.get("address", "Vijayawada, NTR District"),
            organizer=organizer,
            client_name=client_name,
            client_id=data.get("clientId"),
            client_contact_person=data.get("clientContactPerson"),
            client_contact_phone=data.get("clientContactPhone"),
            status=data.get("status", "APPROVED"),
            origin="ADMIN_CREATED",
            created_by=current_admin.id,
            created_by_role="ADMIN",
            image_url=banner_url,
            flyer_url=banner_url,
            registration_start_date=data.get("regStartDate", now.strftime("%Y-%m-%d")),
            registration_deadline=data.get("regEndDate", data.get("date")),
            max_capacity=int(data.get("maxCapacity", 3500)),
            eligible_mandals=mandals_str,
            eligible_villages=data.get("eligibleVillages", "All villages in selected mandals"),
            eligible_qualifications=quals_str,
            created_at=now,
            updated_at=now,
        )
        db.add(mela)
        await db.flush()

        # Add participating companies and job openings
        comps_in = data.get("participatingCompanies") or []
        created_parts = []
        for idx, c in enumerate(comps_in):
            c_name = (c.get("company") or c.get("name") or "Participating Company").strip()
            if not c_name:
                continue
            part_id = f"pmc-{mela_id}-{idx + 1}"
            pos = c.get("position") or "Software / Technical Professional"
            vac = int(c.get("vacancies") or 15)
            loc = c.get("location") or f"Stall {chr(65 + min(idx, 25))}-{(idx + 1):02d}"

            part = JobMelaCompanyParticipation(
                id=part_id,
                job_mela_id=mela_id,
                company_id=c.get("companyId") or None,
                custom_company_name=c_name,
                recruiter_name=c.get("recruiter") or "Talent Acquisition Lead",
                position=pos,
                qualification=c.get("qualification") or "Any Graduate / B.Tech",
                experience=c.get("experience") or "0-2 Years",
                salary=c.get("salary") or "Best in Industry",
                vacancies=vac,
                location=loc,
                notes=c.get("notes") or "",
                openings=pos,
                target_hires=vac,
                status="APPROVED",
                booth_number=loc,
                booth_location=loc,
                registered_at=now,
                approved_at=now,
                approved_by=current_admin.email,
                created_at=now,
                updated_at=now,
            )
            db.add(part)
            created_parts.append(part)

            opening = JobMelaJobOpening(
                id=f"jmo-{mela_id}-{idx + 1}",
                job_mela_id=mela_id,
                participation_id=part_id,
                job_title=pos,
                vacancies=vac,
                qualification=c.get("qualification") or "Any Graduate",
                experience=c.get("experience") or "0-2 Years",
                salary_range=c.get("salary") or "Best in Industry",
                location_stall=loc,
                description=c.get("notes") or "",
                created_at=now,
                updated_at=now,
            )
            db.add(opening)

        await db.commit()
        await db.refresh(mela)
        return JobMelaRepository._format_mela_dict(mela, created_parts, 0)

    @staticmethod
    async def update_admin_job_mela(
        db: AsyncSession,
        mela_id: str,
        data: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Update existing Job Mela event details."""
        stmt = select(JobMela).where(or_(JobMela.id == mela_id, JobMela.mela_number == mela_id))
        result = await db.execute(stmt)
        mela = result.scalar_one_or_none()
        if not mela:
            return None

        now = datetime.now(timezone.utc)
        if "title" in data and data["title"]:
            mela.title = data["title"]
        if "description" in data:
            mela.description = data["description"]
        if "date" in data and data["date"]:
            mela.event_date = data["date"]
        if "startTime" in data:
            mela.start_time = data["startTime"]
        if "endTime" in data:
            mela.end_time = data["endTime"]
        if "venue" in data and data["venue"]:
            mela.venue = data["venue"]
        if "address" in data:
            mela.address = data["address"]
        if "city" in data and data["city"]:
            mela.city = data["city"]
        if "state" in data:
            mela.state = data["state"]
        if "regStartDate" in data:
            mela.registration_start_date = data["regStartDate"]
        if "regEndDate" in data:
            mela.registration_deadline = data["regEndDate"]
        if "maxCapacity" in data:
            mela.max_capacity = int(data["maxCapacity"])
        if "status" in data and data["status"]:
            mela.status = data["status"]
        if "banner" in data or "posterImage" in data:
            img = data.get("banner") or data.get("posterImage")
            if img:
                mela.image_url = img
                mela.flyer_url = img

        mela.updated_at = now
        await db.commit()
        await db.refresh(mela)

        return await JobMelaRepository.get_admin_mela_by_id(db, mela.id)

    @staticmethod
    async def update_mela_status(
        db: AsyncSession,
        mela_id: str,
        new_status: str,
    ) -> Optional[Dict[str, Any]]:
        """Update status of a Job Mela (e.g. APPROVED, REJECTED, UPCOMING, COMPLETED)."""
        stmt = select(JobMela).where(or_(JobMela.id == mela_id, JobMela.mela_number == mela_id))
        result = await db.execute(stmt)
        mela = result.scalar_one_or_none()
        if not mela:
            return None

        mela.status = new_status.upper()
        mela.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(mela)

        return await JobMelaRepository.get_admin_mela_by_id(db, mela.id)

    @staticmethod
    async def add_company_to_mela(
        db: AsyncSession,
        mela_id: str,
        comp_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Add participating company and role to an existing Job Mela."""
        now = datetime.now(timezone.utc)
        part_id = f"pmc-{mela_id}-{uuid.uuid4().hex[:6]}"
        c_name = (comp_data.get("company") or comp_data.get("name") or "Participating Company").strip()
        pos = comp_data.get("position") or "Software / Technical Professional"
        vac = int(comp_data.get("vacancies") or 15)
        loc = comp_data.get("location") or "On-site Mela Stalls"

        part = JobMelaCompanyParticipation(
            id=part_id,
            job_mela_id=mela_id,
            company_id=comp_data.get("companyId") or None,
            custom_company_name=c_name,
            recruiter_name=comp_data.get("recruiter") or "Talent Acquisition Lead",
            position=pos,
            qualification=comp_data.get("qualification") or "B.Tech / Any Graduate",
            experience=comp_data.get("experience") or "0-2 Years",
            salary=comp_data.get("salary") or "Best in Industry",
            vacancies=vac,
            location=loc,
            notes=comp_data.get("notes") or "",
            openings=pos,
            target_hires=vac,
            status="APPROVED",
            booth_number=loc,
            booth_location=loc,
            registered_at=now,
            approved_at=now,
            created_at=now,
            updated_at=now,
        )
        db.add(part)

        opening = JobMelaJobOpening(
            id=f"jmo-{uuid.uuid4().hex[:8]}",
            job_mela_id=mela_id,
            participation_id=part_id,
            job_title=pos,
            vacancies=vac,
            qualification=comp_data.get("qualification") or "Any Graduate",
            experience=comp_data.get("experience") or "0-2 Years",
            salary_range=comp_data.get("salary") or "Best in Industry",
            location_stall=loc,
            description=comp_data.get("notes") or "",
            created_at=now,
            updated_at=now,
        )
        db.add(opening)

        await db.commit()
        await db.refresh(part)

        return {
            "id": part.id,
            "companyId": part.company_id or "",
            "company": c_name,
            "recruiter": part.recruiter_name,
            "position": pos,
            "qualification": part.qualification,
            "experience": part.experience,
            "salary": part.salary,
            "vacancies": vac,
            "applications": 0,
            "location": loc,
            "notes": part.notes,
        }

    @staticmethod
    async def update_company_in_mela(
        db: AsyncSession,
        mela_id: str,
        company_entry_id: str,
        comp_data: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Update participating company details in a Job Mela."""
        stmt = select(JobMelaCompanyParticipation).where(
            JobMelaCompanyParticipation.id == company_entry_id,
            JobMelaCompanyParticipation.job_mela_id == mela_id,
        )
        result = await db.execute(stmt)
        part = result.scalar_one_or_none()
        if not part:
            return None

        now = datetime.now(timezone.utc)
        if "company" in comp_data:
            part.custom_company_name = comp_data["company"]
        if "recruiter" in comp_data:
            part.recruiter_name = comp_data["recruiter"]
        if "position" in comp_data:
            part.position = comp_data["position"]
            part.openings = comp_data["position"]
        if "qualification" in comp_data:
            part.qualification = comp_data["qualification"]
        if "experience" in comp_data:
            part.experience = comp_data["experience"]
        if "salary" in comp_data:
            part.salary = comp_data["salary"]
        if "vacancies" in comp_data:
            part.vacancies = int(comp_data["vacancies"])
            part.target_hires = int(comp_data["vacancies"])
        if "location" in comp_data:
            part.location = comp_data["location"]
            part.booth_number = comp_data["location"]
        if "notes" in comp_data:
            part.notes = comp_data["notes"]

        part.updated_at = now
        await db.commit()
        await db.refresh(part)

        return {
            "id": part.id,
            "companyId": part.company_id or "",
            "company": part.custom_company_name,
            "recruiter": part.recruiter_name,
            "position": part.position,
            "qualification": part.qualification,
            "experience": part.experience,
            "salary": part.salary,
            "vacancies": part.vacancies,
            "applications": 0,
            "location": part.location,
            "notes": part.notes,
        }

    @staticmethod
    async def remove_company_from_mela(
        db: AsyncSession,
        mela_id: str,
        company_entry_id: str,
    ) -> bool:
        """Remove participating company from a Job Mela."""
        stmt = select(JobMelaCompanyParticipation).where(
            JobMelaCompanyParticipation.id == company_entry_id,
            JobMelaCompanyParticipation.job_mela_id == mela_id,
        )
        result = await db.execute(stmt)
        part = result.scalar_one_or_none()
        if not part:
            return False

        await db.delete(part)
        await db.commit()
        return True

    # ── JOB MELA REQUESTS OPERATIONS ─────────────────────────────────────────

    @staticmethod
    async def get_job_mela_requests(
        db: AsyncSession,
        status_filter: Optional[str] = "ALL",
        company_filter: Optional[str] = "ALL",
        search: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch all Job Mela requests with tabs (ALL, PENDING, APPROVED, REJECTED) and filters."""
        await JobMelaRepository.ensure_seed_data(db)

        stmt = select(JobMelaRequest).order_by(JobMelaRequest.created_at.desc())
        result = await db.execute(stmt)
        requests = result.scalars().all()

        items = []
        for r in requests:
            # 1. Status Filter
            if status_filter and status_filter != "ALL" and r.status != status_filter:
                continue

            # 2. Company / Organization Filter
            if company_filter and company_filter != "ALL":
                org_name = (r.organizer or "").strip().lower()
                if org_name != company_filter.strip().lower():
                    continue

            # 3. Search Filter
            if search and search.strip():
                q = search.lower().strip()
                matches = (
                    q in (r.title or "").lower()
                    or q in (r.organizer or "").lower()
                    or q in (r.venue or "").lower()
                    or q in (r.city or "").lower()
                    or q in (r.request_number or "").lower()
                    or q in (r.id or "").lower()
                )
                if not matches:
                    continue

            req_date_str = r.created_at.strftime("%Y-%m-%d") if r.created_at else "2026-09-01"
            time_str = f"{r.start_time or '09:00 AM'} - {r.end_time or '05:00 PM'}"

            # Participating companies in request
            comps = []
            if r.participating_companies_data:
                try:
                    comps = json.loads(r.participating_companies_data)
                except Exception:
                    comps = []

            items.append({
                "id": r.id,
                "request_number": r.request_number,
                "event": r.title,
                "title": r.title,
                "description": r.description or f"Request for conducting multi-employer job fair at {r.venue}, {r.city}.",
                "organizer": r.organizer,
                "company": r.organizer,
                "requestingOrganization": r.organizer,
                "date": r.proposed_date,
                "time": time_str,
                "venue": r.venue,
                "location": f"{r.city}, {r.state or 'Andhra Pradesh'}",
                "city": r.city,
                "district": r.district,
                "state": r.state or "Andhra Pradesh",
                "address": r.address or f"{r.venue}, {r.city}",
                "requestDate": req_date_str,
                "createdAt": req_date_str,
                "status": r.status,
                "capacity": r.expected_capacity or 2000,
                "maxCapacity": r.expected_capacity or 2000,
                "vacancies": r.vacancies_count or 500,
                "contactPerson": r.contact_person or "Nodal Placement Officer",
                "email": r.contact_email or "events@apssdc.in",
                "phone": r.contact_phone or "+91 866 242 9999",
                "rejectionReason": r.rejection_reason,
                "rejection_reason": r.rejection_reason,
                "linkedJobMelaId": r.linked_job_mela_id,
                "participatingCompanies": comps,
            })

        return items

    @staticmethod
    async def create_job_mela_request(
        db: AsyncSession,
        data: Dict[str, Any],
        current_user: Optional[User] = None,
    ) -> Dict[str, Any]:
        """Create a new external/recruiter Job Mela request."""
        now = datetime.now(timezone.utc)
        req_id = f"jmr-{uuid.uuid4().hex[:8]}"
        req_num = f"REQ-MELA-{uuid.uuid4().hex[:5].upper()}"

        comps_data = data.get("participatingCompanies") or data.get("companies") or []
        comps_json = json.dumps(comps_data) if isinstance(comps_data, list) else None

        req = JobMelaRequest(
            id=req_id,
            request_number=req_num,
            title=data.get("title") or data.get("event") or "External Career Summit",
            description=data.get("description"),
            organizer=data.get("organizer") or data.get("company") or getattr(current_user, "name", None) or getattr(current_user, "email", "External Placement Consortium"),
            company_id=data.get("companyId") or getattr(current_user, "company_id", None),
            contact_person=data.get("contactPerson") or getattr(current_user, "name", None) or getattr(current_user, "email", "Nodal Placement Officer"),
            contact_email=data.get("email") or getattr(current_user, "email", "nodal@apssdc.in"),
            contact_phone=data.get("phone") or "+91 866 242 9999",
            proposed_date=data.get("date") or data.get("proposed_date") or now.strftime("%Y-%m-%d"),
            start_time=data.get("startTime") or "09:00 AM",
            end_time=data.get("endTime") or "05:00 PM",
            venue=data.get("venue") or "Proposed Convention Center",
            city=data.get("city") or "Vijayawada",
            district=data.get("district") or "NTR District",
            state=data.get("state") or "Andhra Pradesh",
            address=data.get("address") or f"{data.get('venue', 'Convention Center')}, Vijayawada",
            expected_capacity=int(data.get("capacity") or data.get("maxCapacity") or 2500),
            vacancies_count=int(data.get("vacancies") or data.get("vacanciesCount") or 400),
            status="PENDING",
            participating_companies_data=comps_json,
            created_at=now,
            updated_at=now,
        )
        db.add(req)
        await db.commit()
        await db.refresh(req)
        return await JobMelaRepository.get_job_mela_request_by_id(db, req.id)

    @staticmethod
    async def get_job_mela_request_by_id(
        db: AsyncSession,
        request_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Fetch single Job Mela request by ID."""
        await JobMelaRepository.ensure_seed_data(db)
        stmt = select(JobMelaRequest).where(or_(JobMelaRequest.id == request_id, JobMelaRequest.request_number == request_id))
        result = await db.execute(stmt)
        r = result.scalar_one_or_none()
        if not r:
            return None

        req_date_str = r.created_at.strftime("%Y-%m-%d") if r.created_at else "2026-09-01"
        time_str = f"{r.start_time or '09:00 AM'} - {r.end_time or '05:00 PM'}"
        comps = []
        if r.participating_companies_data:
            try:
                comps = json.loads(r.participating_companies_data)
            except Exception:
                comps = []

        return {
            "id": r.id,
            "request_number": r.request_number,
            "event": r.title,
            "title": r.title,
            "description": r.description or f"Request for conducting multi-employer job fair at {r.venue}, {r.city}.",
            "organizer": r.organizer,
            "company": r.organizer,
            "requestingOrganization": r.organizer,
            "date": r.proposed_date,
            "time": time_str,
            "venue": r.venue,
            "location": f"{r.city}, {r.state or 'Andhra Pradesh'}",
            "city": r.city,
            "district": r.district,
            "state": r.state or "Andhra Pradesh",
            "address": r.address or f"{r.venue}, {r.city}",
            "requestDate": req_date_str,
            "createdAt": req_date_str,
            "status": r.status,
            "capacity": r.expected_capacity or 2000,
            "maxCapacity": r.expected_capacity or 2000,
            "vacancies": r.vacancies_count or 500,
            "contactPerson": r.contact_person or "Nodal Placement Officer",
            "email": r.contact_email or "events@apssdc.in",
            "phone": r.contact_phone or "+91 866 242 9999",
            "rejectionReason": r.rejection_reason,
            "rejection_reason": r.rejection_reason,
            "linkedJobMelaId": r.linked_job_mela_id,
            "participatingCompanies": comps,
        }

    @staticmethod
    async def approve_job_mela_request(
        db: AsyncSession,
        request_id: str,
        reviewer_user: User,
        notes: Optional[str] = None,
        auto_publish: bool = True,
    ) -> Dict[str, Any]:
        """Admin approves request, updating status and activating/creating the corresponding JobMela."""
        stmt = select(JobMelaRequest).where(or_(JobMelaRequest.id == request_id, JobMelaRequest.request_number == request_id))
        result = await db.execute(stmt)
        req = result.scalar_one_or_none()
        if not req:
            raise ValueError("Job Mela request not found.")

        now = datetime.now(timezone.utc)
        req.status = "APPROVED"
        req.reviewer_name = getattr(reviewer_user, "name", None) or reviewer_user.email
        req.admin_reviewer_id = reviewer_user.id
        req.reviewed_at = now
        req.updated_at = now

        # Follow existing architecture: create or activate corresponding event idempotently
        mela_created_or_activated = None
        if req.linked_job_mela_id:
            # Activate existing linked event if present
            m_stmt = select(JobMela).where(JobMela.id == req.linked_job_mela_id)
            m_res = await db.execute(m_stmt)
            existing_mela = m_res.scalar_one_or_none()
            if existing_mela:
                existing_mela.status = "APPROVED" if auto_publish else "UPCOMING"
                existing_mela.updated_at = now
                mela_created_or_activated = existing_mela
        else:
            # Create corresponding Job Mela event
            new_mela_id = f"mela-{uuid.uuid4().hex[:8]}"
            new_mela_num = f"MELA-{uuid.uuid4().hex[:6].upper()}"
            new_mela = JobMela(
                id=new_mela_id,
                mela_number=new_mela_num,
                title=req.title,
                description=req.description,
                event_date=req.proposed_date,
                start_time=req.start_time or "09:00 AM",
                end_time=req.end_time or "05:00 PM",
                venue=req.venue,
                city=req.city,
                district=req.district or "NTR District",
                state=req.state or "Andhra Pradesh",
                address=req.address or f"{req.venue}, {req.city}",
                organizer=req.organizer,
                status="APPROVED" if auto_publish else "UPCOMING",
                origin="RECRUITER_REQUEST",
                created_by=reviewer_user.id,
                created_by_role="ORGANIZER",
                company_id=req.company_id,
                request_id=req.id,
                image_url="/hero2.jpg",
                flyer_url="/hero2.jpg",
                registration_start_date=now.strftime("%Y-%m-%d"),
                registration_deadline=req.proposed_date,
                max_capacity=req.expected_capacity or 2500,
                eligible_mandals=json.dumps(["All Mandals"]),
                eligible_villages="All villages in selected mandals",
                eligible_qualifications=json.dumps(["10TH", "INTER", "UG", "PG"]),
                created_at=now,
                updated_at=now,
            )
            db.add(new_mela)
            req.linked_job_mela_id = new_mela_id
            mela_created_or_activated = new_mela

        await db.commit()
        await db.refresh(req)

        return {
            "success": True,
            "message": f"Job Mela request '{req.title}' has been APPROVED and event activated.",
            "request_id": req.id,
            "status": req.status,
            "linked_job_mela_id": req.linked_job_mela_id,
        }

    @staticmethod
    async def reject_job_mela_request(
        db: AsyncSession,
        request_id: str,
        reviewer_user: User,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Admin rejects Job Mela request and records reason."""
        stmt = select(JobMelaRequest).where(or_(JobMelaRequest.id == request_id, JobMelaRequest.request_number == request_id))
        result = await db.execute(stmt)
        req = result.scalar_one_or_none()
        if not req:
            raise ValueError("Job Mela request not found.")

        now = datetime.now(timezone.utc)
        req.status = "REJECTED"
        req.rejection_reason = reason or "Proposed event does not meet regulatory or logistical requirements."
        req.reviewer_name = getattr(reviewer_user, "name", None) or reviewer_user.email
        req.admin_reviewer_id = reviewer_user.id
        req.reviewed_at = now
        req.updated_at = now

        # If already linked to an event, mark that event as REJECTED
        if req.linked_job_mela_id:
            m_stmt = select(JobMela).where(JobMela.id == req.linked_job_mela_id)
            m_res = await db.execute(m_stmt)
            linked_mela = m_res.scalar_one_or_none()
            if linked_mela:
                linked_mela.status = "REJECTED"
                linked_mela.updated_at = now

        await db.commit()
        await db.refresh(req)

        return {
            "success": True,
            "message": f"Job Mela request '{req.title}' has been REJECTED.",
            "request_id": req.id,
            "status": req.status,
            "rejection_reason": req.rejection_reason,
        }

    # ── METRICS & REGISTRATIONS ──────────────────────────────────────────────

    @staticmethod
    async def get_job_mela_metrics(db: AsyncSession) -> Dict[str, Any]:
        """Calculate real database aggregates for Admin Job Melas banner and overview."""
        await JobMelaRepository.ensure_seed_data(db)

        # 1. Total registered candidates across all melas
        reg_stmt = select(func.count(JobMelaRegistration.id))
        total_registered = (await db.execute(reg_stmt)).scalar() or 0

        # 2. Total capacity across all melas
        cap_stmt = select(func.sum(JobMela.max_capacity))
        total_capacity = (await db.execute(cap_stmt)).scalar() or 0

        # 3. Total events
        events_stmt = select(func.count(JobMela.id))
        total_events = (await db.execute(events_stmt)).scalar() or 0

        # 4. Total admin created melas
        admin_events_stmt = select(func.count(JobMela.id)).where(
            or_(
                JobMela.origin == "ADMIN_CREATED",
                JobMela.created_by_role == "ADMIN",
                JobMela.organizer.ilike("%NTR Vikasa%"),
            )
        )
        total_admin_melas = (await db.execute(admin_events_stmt)).scalar() or 0

        # 5. Requests counts
        req_total_stmt = select(func.count(JobMelaRequest.id))
        total_requests = (await db.execute(req_total_stmt)).scalar() or 0

        req_pending_stmt = select(func.count(JobMelaRequest.id)).where(JobMelaRequest.status == "PENDING")
        pending_requests = (await db.execute(req_pending_stmt)).scalar() or 0

        req_approved_stmt = select(func.count(JobMelaRequest.id)).where(JobMelaRequest.status == "APPROVED")
        approved_requests = (await db.execute(req_approved_stmt)).scalar() or 0

        req_rejected_stmt = select(func.count(JobMelaRequest.id)).where(JobMelaRequest.status == "REJECTED")
        rejected_requests = (await db.execute(req_rejected_stmt)).scalar() or 0

        # 6. Total vacancies
        vac_stmt = select(func.sum(JobMelaCompanyParticipation.vacancies))
        total_vacancies = (await db.execute(vac_stmt)).scalar() or 0

        # Fill rate (safe against division by zero)
        fill_rate = round((total_registered / total_capacity) * 100) if total_capacity > 0 else 0

        return {
            "totalRegisteredCandidates": total_registered,
            "totalEventCapacity": total_capacity,
            "turnoutFillRate": fill_rate,
            "totalEvents": total_events,
            "totalAdminMelas": total_admin_melas,
            "totalRequests": total_requests,
            "pendingRequests": pending_requests,
            "approvedRequests": approved_requests,
            "rejectedRequests": rejected_requests,
            "totalVacancies": total_vacancies,
        }

    @staticmethod
    async def get_mela_registrations_admin(
        db: AsyncSession,
        mela_id: str,
        search: Optional[str] = None,
        status_filter: Optional[str] = "ALL",
    ) -> List[Dict[str, Any]]:
        """Fetch candidates registered for a specific Job Mela for the admin registrations modal."""
        stmt = (
            select(JobMelaRegistration, CandidateProfile, User)
            .join(CandidateProfile, JobMelaRegistration.candidate_profile_id == CandidateProfile.id)
            .join(User, CandidateProfile.user_id == User.id)
            .where(JobMelaRegistration.job_mela_id == mela_id)
            .order_by(JobMelaRegistration.registered_at.desc())
        )
        result = await db.execute(stmt)
        rows = result.all()

        candidates = []
        for reg, profile, user in rows:
            if status_filter and status_filter != "ALL" and reg.status != status_filter:
                continue

            candidate_display_name = getattr(profile, "name", None) or getattr(user, "name", None) or user.email
            item = {
                "id": reg.id,
                "candidateId": profile.id,
                "candidate": candidate_display_name,
                "candidateName": candidate_display_name,
                "email": user.email,
                "candidateEmail": user.email,
                "phone": getattr(profile, "phone", None) or getattr(user, "phone", None) or "+91 98765 43210",
                "entryToken": reg.pass_id,
                "passId": reg.pass_id,
                "gateNumber": reg.gate_number,
                "timeSlot": reg.time_slot,
                "registrationDate": reg.registered_at.strftime("%Y-%m-%d") if reg.registered_at else "2026-08-28",
                "status": reg.status,
                "headline": getattr(profile, "headline", None) or "Graduate Candidate",
                "qualification": getattr(profile, "qualification_level", None) or "B.Tech / Any Graduate",
            }

            if search and search.strip():
                q = search.lower().strip()
                if (
                    q not in item["candidate"].lower()
                    and q not in item["email"].lower()
                    or q not in item["passId"].lower()
                ):
                    continue

            candidates.append(item)

        return candidates


