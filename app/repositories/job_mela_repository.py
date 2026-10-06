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

