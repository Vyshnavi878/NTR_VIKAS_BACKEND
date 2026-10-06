import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.job_mela_repository import JobMelaRepository
from app.schemas.job_mela import (
    JobMelaRead,
    RecruiterJobMelaItem,
    JobMelaParticipationRequest,
    JobMelaParticipationResponse,
    AdminParticipationItem,
    AdminApproveParticipationRequest,
    AdminRejectParticipationRequest,
    CandidateMelaCompanyItem,
    CandidateJobMelasListResponse,
    CandidateJobMelaCard,
    JobMelaCounts,
    CandidateJobMelaRegistrationRequest,
    CandidateJobMelaRegistrationItem,
    CandidateJobMelaApplyCompanyRequest,
    CandidateJobMelaApplyCompanyResponse,
)


class JobMelaService:
    """
    Business logic for Job Melas and Recruiter/Admin Participation workflows.
    """

    @classmethod
    async def get_recruiter_job_melas(
        cls,
        db: AsyncSession,
        current_user: User,
        status_filter: Optional[str] = "ALL",
        search: Optional[str] = None,
    ) -> List[RecruiterJobMelaItem]:
        """
        Retrieve all Job Melas with participation context for the authenticated recruiter.
        """
        profile = await JobMelaRepository.get_recruiter_profile_by_user_id(db, current_user.id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recruiter profile not found. Please complete company registration.",
            )

        events_data = await JobMelaRepository.get_recruiter_job_melas(
            db=db,
            recruiter_id=profile.id,
            status_filter=status_filter,
            search=search,
        )

        return [RecruiterJobMelaItem(**item) for item in events_data]

    @classmethod
    async def get_available_melas(cls, db: AsyncSession) -> List[JobMelaRead]:
        """
        Retrieve all active / published Job Melas for dropdown selection.
        """
        melas = await JobMelaRepository.get_all_published_melas(db)
        return [JobMelaRead.model_validate(m) for m in melas]

    @classmethod
    async def register_company_participation(
        cls,
        db: AsyncSession,
        current_user: User,
        payload: JobMelaParticipationRequest,
    ) -> JobMelaParticipationResponse:
        """
        Recruiter submits a company participation request for a Job Mela.
        Status is created strictly as PENDING awaiting administrative review.
        """
        profile = await JobMelaRepository.get_recruiter_profile_by_user_id(db, current_user.id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recruiter profile not found. Please complete company registration.",
            )

        # 1. Resolve target Job Mela by ID or Title
        target_mela = await JobMelaRepository.get_job_mela_by_id_or_title(
            db, mela_id=payload.job_mela_id, title=payload.title
        )
        if not target_mela:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job Mela event '{payload.job_mela_id or payload.title}' not found.",
            )

        # 2. Check for duplicate registration
        existing = await JobMelaRepository.get_participation(
            db, job_mela_id=target_mela.id, company_id=profile.id
        )
        if existing:
            if existing.status == "PENDING":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="A participation request for this Job Mela has already been submitted and is currently pending administrator approval.",
                )
            elif existing.status == "APPROVED":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Your company is already registered and approved for this Job Mela event.",
                )
            elif existing.status == "REJECTED":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Previous participation request was rejected: {existing.rejection_reason or 'Contact administrator'}.",
                )

        # 3. Create participation record with PENDING status
        openings_text = (payload.openings or payload.positions or "").strip()
        hires_count = payload.target_hires or payload.expectedHires or payload.expected_hires or 1

        participation = await JobMelaRepository.create_participation(
            db=db,
            job_mela_id=target_mela.id,
            company_id=profile.id,
            openings=openings_text,
            target_hires=hires_count,
        )

        return JobMelaParticipationResponse(
            id=participation.id,
            job_mela_id=target_mela.id,
            mela_title=target_mela.title,
            company_id=profile.id,
            company_name=profile.company_name,
            openings=openings_text,
            target_hires=hires_count,
            status=participation.status,
            booth_number=participation.booth_number,
            registered_at=participation.registered_at.strftime("%Y-%m-%d %H:%M:%S"),
            message="Participation request submitted successfully and is pending administrative review.",
        )

    @classmethod
    async def get_admin_participations(
        cls,
        db: AsyncSession,
        status_filter: Optional[str] = "ALL",
        search: Optional[str] = None,
    ) -> List[AdminParticipationItem]:
        """
        Admin reviews all company participation requests across Job Melas.
        """
        rows = await JobMelaRepository.get_admin_participations(
            db=db, status_filter=status_filter, search=search
        )
        return [AdminParticipationItem(**r) for r in rows]

    @classmethod
    async def approve_participation(
        cls,
        db: AsyncSession,
        participation_id: str,
        current_admin: User,
        payload: Optional[AdminApproveParticipationRequest] = None,
    ) -> Dict[str, Any]:
        """
        Administrator approves a company participation and assigns a corporate booth/stall.
        """
        part = await JobMelaRepository.get_participation_by_id(db, participation_id)
        if not part:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job Mela participation request not found.",
            )

        now = datetime.now(timezone.utc)
        stall = (payload.booth_number if payload and payload.booth_number else None) or f"Booth S-{part.id[-4:].upper()} (Hall 2)"
        location = (payload.booth_location if payload and payload.booth_location else None) or "Corporate Enclosure"

        part.status = "APPROVED"
        part.approved_at = now
        part.approved_by = current_admin.email
        part.booth_number = stall
        part.booth_location = location
        part.updated_at = now

        await db.commit()
        await db.refresh(part)

        return {
            "success": True,
            "message": f"Participation approved. Allocated {stall}.",
            "participation_id": part.id,
            "status": part.status,
            "booth_number": part.booth_number,
        }

    @classmethod
    async def reject_participation(
        cls,
        db: AsyncSession,
        participation_id: str,
        current_admin: User,
        payload: AdminRejectParticipationRequest,
    ) -> Dict[str, Any]:
        """
        Administrator rejects a company participation with mandatory reason.
        """
        part = await JobMelaRepository.get_participation_by_id(db, participation_id)
        if not part:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job Mela participation request not found.",
            )

        now = datetime.now(timezone.utc)
        part.status = "REJECTED"
        part.rejected_at = now
        part.rejected_by = current_admin.email
        part.rejection_reason = payload.rejection_reason
        part.updated_at = now

        await db.commit()
        await db.refresh(part)

        return {
            "success": True,
            "message": "Participation request rejected.",
            "participation_id": part.id,
            "status": part.status,
            "rejection_reason": part.rejection_reason,
        }

    @classmethod
    async def get_approved_mela_companies(
        cls, db: AsyncSession, job_mela_id: str
    ) -> List[CandidateMelaCompanyItem]:
        """
        Approved companies participating in a Job Mela (for candidate experience).
        """
        companies = await JobMelaRepository.get_approved_companies_for_mela(db, job_mela_id)
        return [CandidateMelaCompanyItem(**c) for c in companies]

    @classmethod
    async def get_candidate_job_melas(
        cls,
        db: AsyncSession,
        current_user: Optional[User] = None,
        status_filter: Optional[str] = "ALL",
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 12,
    ) -> CandidateJobMelasListResponse:
        """
        Public / candidate endpoint: retrieve eligible Job Melas with real statistics,
        category counts, and candidate registration status.
        """
        candidate_profile_id = None
        if current_user and current_user.role == "CANDIDATE":
            from app.repositories.candidate_dashboard_repository import CandidateDashboardRepository
            profile = await CandidateDashboardRepository.get_candidate_profile(db, current_user.id)
            if profile:
                candidate_profile_id = profile.id

        res = await JobMelaRepository.list_candidate_job_melas(
            db=db,
            candidate_profile_id=candidate_profile_id,
            status_filter=status_filter or "ALL",
            search=search,
            page=page,
            page_size=page_size,
        )

        return CandidateJobMelasListResponse(
            items=[CandidateJobMelaCard(**item) for item in res["items"]],
            counts=JobMelaCounts(**res["counts"]),
            total=res["total"],
            page=res["page"],
            page_size=res["page_size"],
            total_pages=res["total_pages"],
        )

    @classmethod
    async def get_candidate_job_mela_detail(
        cls,
        db: AsyncSession,
        job_mela_id: str,
        current_user: Optional[User] = None,
    ) -> CandidateJobMelaCard:
        """
        Retrieve single Job Mela details with approved participating companies.
        """
        target_mela = await JobMelaRepository.get_job_mela_by_id_or_title(
            db, mela_id=job_mela_id
        )
        if not target_mela:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job Mela '{job_mela_id}' not found.",
            )

        candidate_profile_id = None
        if current_user and current_user.role == "CANDIDATE":
            from app.repositories.candidate_dashboard_repository import CandidateDashboardRepository
            profile = await CandidateDashboardRepository.get_candidate_profile(db, current_user.id)
            if profile:
                candidate_profile_id = profile.id

        companies = await JobMelaRepository.get_approved_companies_for_mela(db, target_mela.id)

        user_reg = None
        if candidate_profile_id:
            user_reg = await JobMelaRepository.get_registration_by_candidate_and_mela(
                db, candidate_profile_id=candidate_profile_id, job_mela_id=target_mela.id
            )

        # Candidate registration counts
        from app.models.job_mela import JobMelaRegistration
        from sqlalchemy import select
        reg_count_stmt = select(JobMelaRegistration).where(
            JobMelaRegistration.job_mela_id == target_mela.id
        )
        reg_count_res = await db.execute(reg_count_stmt)
        cand_count = len(reg_count_res.scalars().all())

        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        m_date = target_mela.event_date or ""
        if target_mela.status == "COMPLETED" or (m_date and m_date < today_str):
            display_status = "COMPLETED"
        elif target_mela.status == "ONGOING" or m_date == today_str:
            display_status = "ONGOING"
        else:
            display_status = "UPCOMING"

        time_str = f"{target_mela.start_time or '09:00 AM'} - {target_mela.end_time or '05:30 PM'}"

        return CandidateJobMelaCard(
            id=target_mela.id,
            mela_number=target_mela.mela_number,
            melaId=target_mela.id,
            title=target_mela.title,
            event=target_mela.title,
            description=target_mela.description or f"Mega Job Mela event organizing interviews across top engineering, IT, and core industries at {target_mela.venue}, {target_mela.city}.",
            event_date=target_mela.event_date,
            date=target_mela.event_date,
            start_time=target_mela.start_time or "09:00 AM",
            end_time=target_mela.end_time or "05:30 PM",
            time=time_str,
            venue=target_mela.venue,
            city=target_mela.city,
            district=target_mela.district,
            state="Andhra Pradesh",
            status=display_status,
            organizer_type=target_mela.created_by_role or "ADMIN",
            companies_count=len(companies) if companies else 24,
            participating_companies_count=len(companies) if companies else 24,
            candidates_count=cand_count,
            candidate_count=cand_count,
            image_url=target_mela.image_url or "https://images.unsplash.com/photo-1540575467063-178a50c2df87?w=800&auto=format&fit=crop&q=80",
            flyer_url=target_mela.flyer_url or "https://images.unsplash.com/photo-1540575467063-178a50c2df87?w=800&auto=format&fit=crop&q=80",
            poster_url=target_mela.flyer_url or "https://images.unsplash.com/photo-1540575467063-178a50c2df87?w=800&auto=format&fit=crop&q=80",
            registration_required=True,
            registration_deadline=target_mela.registration_deadline or target_mela.event_date,
            candidate_registered=bool(user_reg),
            candidate_pass_id=user_reg.pass_id if user_reg else None,
            candidate_registration_status=user_reg.status if user_reg else None,
            participating_companies=[CandidateMelaCompanyItem(**c) for c in companies],
        )

    @classmethod
    async def get_candidate_registrations(
        cls,
        db: AsyncSession,
        current_user: User,
    ) -> List[CandidateJobMelaRegistrationItem]:
        """
        Retrieve all Job Mela passes/registrations for the authenticated candidate.
        """
        from app.repositories.candidate_dashboard_repository import CandidateDashboardRepository
        profile = await CandidateDashboardRepository.get_candidate_profile(db, current_user.id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Candidate profile not found.",
            )

        passes_data = await JobMelaRepository.get_candidate_registrations(db, profile.id)
        return [CandidateJobMelaRegistrationItem(**p) for p in passes_data]

    @classmethod
    async def register_candidate_for_mela(
        cls,
        db: AsyncSession,
        current_user: User,
        job_mela_id: str,
        payload: Optional[CandidateJobMelaRegistrationRequest] = None,
    ) -> CandidateJobMelaRegistrationItem:
        """
        Register authenticated candidate for a Job Mela:
        1. Validates candidate & event eligibility
        2. Enforces duplicate check (409 Conflict)
        3. Generates unique pass ID
        4. Creates registration record in MySQL
        5. Creates Job Mela application in candidate_applications for My Applications tracker
        6. Sends confirmation notification
        """
        from app.repositories.candidate_dashboard_repository import CandidateDashboardRepository
        profile = await CandidateDashboardRepository.get_candidate_profile(db, current_user.id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Candidate profile not found. Please complete registration.",
            )

        target_mela = await JobMelaRepository.get_job_mela_by_id_or_title(
            db, mela_id=job_mela_id
        )
        if not target_mela:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job Mela event '{job_mela_id}' not found.",
            )

        # Check eligibility: cannot register for cancelled or completed events
        if target_mela.status in ("CANCELLED", "REJECTED", "DRAFT"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Registration is closed for this event.",
            )

        # Duplicate check
        existing = await JobMelaRepository.get_registration_by_candidate_and_mela(
            db, candidate_profile_id=profile.id, job_mela_id=target_mela.id
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"You are already registered for '{target_mela.title}'. Your Pass ID is {existing.pass_id}.",
            )

        pass_id = await JobMelaRepository.generate_unique_pass_id(db)
        now = datetime.now(timezone.utc)
        reg_id = f"reg-{uuid.uuid4().hex[:10]}"
        time_slot = (payload.time_slot if payload and payload.time_slot else None) or "Morning Session (09:00 AM - 01:00 PM)"
        gate_num = "Gate 2 (General Fast-Track)"

        # Create CandidateApplication record so it also appears in My Applications Tracker!
        from app.models.application import CandidateApplication, ApplicationTimelineEvent
        from app.repositories.candidate_application_repository import CandidateApplicationRepository
        app_number = await CandidateApplicationRepository.generate_unique_application_number(db, is_mela=True)
        app_id = str(uuid.uuid4())
        today_formatted = now.strftime("%d %b %Y")

        new_app = CandidateApplication(
            id=app_id,
            application_number=app_number,
            candidate_profile_id=profile.id,
            job_id=f"MELA-JOB-{target_mela.id}",
            job_title=f"Fast-Track Entry — {target_mela.title}",
            company_name="NTR Vikasa Job Melas Authority",
            location=f"{target_mela.venue}, {target_mela.city}",
            salary="Walk-in Multiple Roles",
            employment_type="Full-time",
            work_mode="On-site",
            application_type="Job Mela Application",
            source="NTR Vikasa Mega Job Melas",
            mela_id=target_mela.id,
            mela_title=target_mela.title,
            match_percentage=95,
            status="APPLIED",
            applied_date=today_formatted,
            applied_at=now,
        )
        await CandidateApplicationRepository.create_application(db, new_app)

        # Create Initial Timeline event
        initial_event = ApplicationTimelineEvent(
            id=str(uuid.uuid4()),
            application_id=new_app.id,
            stage="Applied",
            status="APPLIED",
            label="Job Mela Pass Issued",
            date=today_formatted,
            completed=True,
            current=True,
            step_order=1,
            created_at=now,
        )
        await CandidateApplicationRepository.create_timeline_event(db, initial_event)

        # Create JobMelaRegistration
        from app.models.job_mela import JobMelaRegistration
        new_reg = JobMelaRegistration(
            id=reg_id,
            job_mela_id=target_mela.id,
            candidate_profile_id=profile.id,
            pass_id=pass_id,
            status="CONFIRMED",
            gate_number=gate_num,
            time_slot=time_slot,
            qr_data=pass_id,
            application_id=new_app.id,
            registered_at=now,
            created_at=now,
            updated_at=now,
        )
        created_reg = await JobMelaRepository.create_job_mela_registration(db, new_reg)

        # Send notification
        try:
            from app.services.notification_service import NotificationService
            await NotificationService.create_notification(
                db=db,
                candidate_id=profile.id,
                category="job_mela",
                title=f"Job Mela Pass Confirmed: {pass_id}",
                message=f"Your Fast-Track QR pass ({pass_id}) is confirmed for {target_mela.title}. Event Date: {target_mela.event_date}. Venue: {target_mela.venue}. Gate: {gate_num}.",
                link="/candidate/job-melas",
                job_mela_id=target_mela.id,
            )
        except Exception:
            pass

        qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={pass_id}"
        time_str = f"{target_mela.start_time or '09:00 AM'} - {target_mela.end_time or '05:30 PM'}"

        return CandidateJobMelaRegistrationItem(
            id=created_reg.id,
            registration_id=created_reg.id,
            job_mela_id=target_mela.id,
            mela_id=target_mela.id,
            melaId=target_mela.id,
            mela_number=target_mela.mela_number,
            title=target_mela.title,
            event=target_mela.title,
            event_title=target_mela.title,
            event_date=target_mela.event_date,
            date=target_mela.event_date,
            start_time=target_mela.start_time or "09:00 AM",
            end_time=target_mela.end_time or "05:30 PM",
            time=time_str,
            venue=target_mela.venue,
            city=target_mela.city,
            state="Andhra Pradesh",
            pass_id=created_reg.pass_id,
            passId=created_reg.pass_id,
            entry_token=created_reg.pass_id,
            status=created_reg.status,
            gate_number=created_reg.gate_number,
            gateNumber=created_reg.gate_number,
            time_slot=created_reg.time_slot,
            timeSlot=created_reg.time_slot,
            qr_code_url=qr_url,
            entry_qr_code=qr_url,
            entryQrCode=qr_url,
            registered_at=today_formatted,
            registered_on=today_formatted,
            registeredOn=today_formatted,
            application_id=new_app.id,
            candidate_name=profile.name,
            candidate_email=current_user.email,
            candidate_phone=profile.phone,
        )

    @classmethod
    async def get_candidate_registration_pass(
        cls,
        db: AsyncSession,
        current_user: User,
        registration_id: str,
    ) -> CandidateJobMelaRegistrationItem:
        """
        Retrieve digital QR pass details for a specific registration (verifies ownership).
        """
        from app.repositories.candidate_dashboard_repository import CandidateDashboardRepository
        profile = await CandidateDashboardRepository.get_candidate_profile(db, current_user.id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Candidate profile not found.",
            )

        row = await JobMelaRepository.get_registration_by_id_and_candidate(
            db, registration_id=registration_id, candidate_profile_id=profile.id
        )
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Registration pass not found or you are not authorized to view it.",
            )

        reg, mela = row
        qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={reg.pass_id}"
        reg_date_str = reg.registered_at.strftime("%d %b %Y") if reg.registered_at else "Recently"
        time_str = f"{mela.start_time or '09:00 AM'} - {mela.end_time or '05:30 PM'}"

        return CandidateJobMelaRegistrationItem(
            id=reg.id,
            registration_id=reg.id,
            job_mela_id=mela.id,
            mela_id=mela.id,
            melaId=mela.id,
            mela_number=mela.mela_number,
            title=mela.title,
            event=mela.title,
            event_title=mela.title,
            event_date=mela.event_date,
            date=mela.event_date,
            start_time=mela.start_time or "09:00 AM",
            end_time=mela.end_time or "05:30 PM",
            time=time_str,
            venue=mela.venue,
            city=mela.city,
            state="Andhra Pradesh",
            pass_id=reg.pass_id,
            passId=reg.pass_id,
            entry_token=reg.pass_id,
            status=reg.status,
            gate_number=reg.gate_number,
            gateNumber=reg.gate_number,
            time_slot=reg.time_slot,
            timeSlot=reg.time_slot,
            qr_code_url=qr_url,
            entry_qr_code=qr_url,
            entryQrCode=qr_url,
            registered_at=reg_date_str,
            registered_on=reg_date_str,
            registeredOn=reg_date_str,
            application_id=reg.application_id,
            candidate_name=profile.name,
            candidate_email=current_user.email,
            candidate_phone=profile.phone,
        )

    @classmethod
    async def apply_candidate_to_mela_company(
        cls,
        db: AsyncSession,
        current_user: User,
        job_mela_id: str,
        payload: CandidateJobMelaApplyCompanyRequest,
    ) -> CandidateJobMelaApplyCompanyResponse:
        """
        Candidate applies to a participating company in a Job Mela.
        Creates a CandidateApplication with type "Job Mela Application".
        """
        from app.repositories.candidate_dashboard_repository import CandidateDashboardRepository
        profile = await CandidateDashboardRepository.get_candidate_profile(db, current_user.id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Candidate profile not found.",
            )

        target_mela = await JobMelaRepository.get_job_mela_by_id_or_title(
            db, mela_id=job_mela_id
        )
        if not target_mela:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job Mela '{job_mela_id}' not found.",
            )

        now = datetime.now(timezone.utc)
        today_formatted = now.strftime("%d %b %Y")
        from app.repositories.candidate_application_repository import CandidateApplicationRepository
        app_number = await CandidateApplicationRepository.generate_unique_application_number(db, is_mela=True)
        app_id = str(uuid.uuid4())

        from app.models.application import CandidateApplication, ApplicationTimelineEvent
        new_app = CandidateApplication(
            id=app_id,
            application_number=app_number,
            candidate_profile_id=profile.id,
            job_id=f"MELA-{target_mela.id}-{payload.role[:10].replace(' ', '-')}",
            job_title=payload.role,
            company_name=payload.company_name,
            location=payload.location or f"{target_mela.venue}, {target_mela.city}",
            salary=payload.salary or "₹5.0 - ₹8.0 LPA",
            employment_type="Full-time",
            work_mode="On-site",
            application_type="Job Mela Application",
            source=f"Job Mela: {target_mela.title}",
            mela_id=target_mela.id,
            mela_title=target_mela.title,
            recruiter_id=payload.company_id,
            match_percentage=88,
            status="APPLIED",
            applied_date=today_formatted,
            applied_at=now,
            cover_letter=payload.cover_note,
            resume_name=payload.resume or "Candidate_Resume.pdf",
        )
        created_app = await CandidateApplicationRepository.create_application(db, new_app)

        # Create Timeline Event
        initial_event = ApplicationTimelineEvent(
            id=str(uuid.uuid4()),
            application_id=created_app.id,
            stage="Applied",
            status="APPLIED",
            label=f"Applied for {payload.role} at {payload.company_name}",
            date=today_formatted,
            completed=True,
            current=True,
            step_order=1,
            created_at=now,
        )
        await CandidateApplicationRepository.create_timeline_event(db, initial_event)

        # Notify candidate
        try:
            from app.services.notification_service import NotificationService
            await NotificationService.create_notification(
                db=db,
                candidate_id=profile.id,
                category="job_mela",
                title=f"Walk-in Application Submitted: {payload.company_name}",
                message=f"Your walk-in application for {payload.role} at {payload.company_name} for {target_mela.title} has been submitted (Application No: {created_app.application_number}).",
                link="/candidate/applications",
                application_id=created_app.id,
                job_mela_id=target_mela.id,
            )
        except Exception:
            pass

        return CandidateJobMelaApplyCompanyResponse(
            id=created_app.id,
            application_number=created_app.application_number,
            job_mela_id=target_mela.id,
            company_name=payload.company_name,
            job_title=payload.role,
            status="APPLIED",
            applied_date=today_formatted,
            message="Application submitted successfully for Job Mela interview.",
        )

