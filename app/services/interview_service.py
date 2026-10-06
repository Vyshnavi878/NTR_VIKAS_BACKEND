import json
import uuid
import re
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Union, Tuple
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User
from app.models.interview import Interview
from app.models.recruiter import RecruiterProfile
from app.models.application import CandidateApplication
from app.models.job import Job
from app.repositories.interview_repository import (
    InterviewRepository,
    time_to_minutes,
    times_overlap,
)
from app.schemas.interview import (
    InterviewCreate,
    InterviewUpdate,
    InterviewCancel,
    InterviewComplete,
    InterviewResponse,
    InterviewListResponse,
    CandidateInterviewCounts,
    CandidateInterviewListResponse,
    CandidateSummary,
    JobSummary,
)
from app.services.notification_service import NotificationService
from app.services.email_service import EmailService


def format_time_display(start_time: Optional[str], end_time: Optional[str], timezone_str: str = "Asia/Kolkata") -> str:
    """Format clean time display like '11:00 AM - 12:00 PM IST'."""
    if not start_time:
        return "11:00 AM - 12:00 PM IST"

    def clean_t(t: str) -> str:
        s = t.strip()
        if "AM" in s.upper() or "PM" in s.upper():
            return s
        parts = s.split(":")
        try:
            h = int(parts[0])
            m = int(parts[1]) if len(parts) > 1 else 0
            period = "PM" if h >= 12 else "AM"
            h_12 = h % 12
            if h_12 == 0:
                h_12 = 12
            return f"{h_12:02d}:{m:02d} {period}"
        except Exception:
            return s

    s_clean = clean_t(start_time)
    if end_time:
        e_clean = clean_t(end_time)
        return f"{s_clean} - {e_clean} IST"
    return f"{s_clean} IST"


def parse_panel(panel_val: Optional[Union[List[str], str]]) -> Tuple[List[str], str]:
    """Parse interviewer panel into (list_of_names, combined_display_string)."""
    if not panel_val:
        return ([], "")
    if isinstance(panel_val, list):
        cleaned = [str(p).strip() for p in panel_val if str(p).strip()]
        return (cleaned, " & ".join(cleaned))
    if isinstance(panel_val, str):
        try:
            loaded = json.loads(panel_val)
            if isinstance(loaded, list):
                cleaned = [str(p).strip() for p in loaded if str(p).strip()]
                return (cleaned, " & ".join(cleaned))
        except Exception:
            pass
        # Comma or ampersand separated
        items = [p.strip() for p in re.split(r"[,&]", panel_val) if p.strip()]
        return (items, panel_val.strip())
    return ([], "")


class InterviewService:
    """
    Business service layer for Recruiter Interview Management.
    Enforces recruiter ownership, conflict verification, application state transitions,
    candidate notifications, and transactional email invitations.
    """

    @classmethod
    async def get_recruiter_profile(cls, db: AsyncSession, user_id: str) -> RecruiterProfile:
        """Fetch the authenticated recruiter's organization profile."""
        stmt = select(RecruiterProfile).where(RecruiterProfile.user_id == user_id)
        result = await db.execute(stmt)
        profile = result.scalar_one_or_none()
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recruiter profile not found. Please complete organization onboarding.",
            )
        return profile

    @classmethod
    async def get_candidate_profile(cls, db: AsyncSession, user_id: str):
        """Fetch the authenticated candidate profile."""
        from app.models.candidate import CandidateProfile
        stmt = select(CandidateProfile).where(CandidateProfile.user_id == user_id)
        result = await db.execute(stmt)
        profile = result.scalar_one_or_none()
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Candidate profile not found. Please complete candidate profile onboarding.",
            )
        return profile

    @classmethod
    def serialize_interview(cls, item: Interview) -> InterviewResponse:
        """Serialize Interview model to unified InterviewResponse schema."""
        panel_list, panel_display = parse_panel(item.interviewer_panel or item.interviewer)
        time_display = item.time or format_time_display(item.start_time, item.end_time, item.timezone or "Asia/Kolkata")
        date_display = item.scheduled_date or item.date or "2026-09-10"

        # Determine type string for UI
        format_type = item.format or "ONLINE"
        type_str = item.interview_type or ("Online (Google Meet)" if format_type == "ONLINE" else "In-Person (Office Round)")
        mode_str = "Online Interview" if format_type == "ONLINE" else "In-Person Interview"

        cand_id = item.candidate_profile_id or (item.candidate.id if item.candidate else None)
        cand_name = item.candidate_name or (item.candidate.name if item.candidate else "Candidate")
        cand_email = item.candidate_email or (item.candidate.user.email if item.candidate and hasattr(item.candidate, "user") and item.candidate.user else None)

        job_id_val = item.job_id or (item.application.job_id if item.application else None)
        job_title_val = item.job_title or (item.application.job_title if item.application else "Job Role")

        company_name_val = item.company_name or (
            item.application.company_name if item.application and getattr(item.application, "company_name", None)
            else (item.recruiter.company_name if item.recruiter and getattr(item.recruiter, "company_name", None) else "Hiring Organization")
        )
        round_title = item.round_name or "Technical Round 1"

        return InterviewResponse(
            id=str(item.id),
            application_id=str(item.application_id) if item.application_id else None,
            candidate=CandidateSummary(
                id=str(cand_id) if cand_id else None,
                name=cand_name,
                email=cand_email,
            ),
            job=JobSummary(
                id=str(job_id_val) if job_id_val else None,
                title=job_title_val,
            ),
            candidate_name=cand_name,
            candidate_email=cand_email,
            candidateName=cand_name,
            candidateEmail=cand_email,
            job_title=job_title_val,
            jobTitle=job_title_val,
            role=job_title_val,
            company_name=company_name_val,
            companyName=company_name_val,
            company=company_name_val,
            title=round_title,
            interview_title=round_title,
            status=item.status,
            scheduled_date=date_display,
            date=date_display,
            start_time=item.start_time or "11:00",
            end_time=item.end_time or "12:00",
            time=time_display,
            timezone=item.timezone or "Asia/Kolkata",
            format=format_type,
            type=type_str,
            mode=mode_str,
            meeting_platform=item.meeting_platform or "Google Meet",
            meetingPlatform=item.meeting_platform or "Google Meet",
            meeting_link=item.meeting_link,
            meetingLink=item.meeting_link,
            meetingUrl=item.meeting_link,
            venue=item.venue,
            interviewer_panel=panel_list,
            interviewer=panel_display or item.interviewer or "Recruiter Panel",
            panel=panel_display or item.interviewer or "Recruiter Panel",
            agenda_notes=item.agenda_notes or item.notes,
            notes=item.agenda_notes or item.notes,
            instructions=item.agenda_notes or item.notes or "Please be ready with your code IDE and a working camera/microphone 10 minutes prior.",
            preparation_note=item.agenda_notes or item.notes or "Please be ready with your code IDE and a working camera/microphone 10 minutes prior.",
            result=item.result,
            completed_at=item.completed_at,
            cancelled_at=item.cancelled_at,
            cancellation_reason=item.cancellation_reason,
            rescheduled_from_id=item.rescheduled_from_id,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )

    @classmethod
    async def get_candidate_interviews(
        cls,
        db: AsyncSession,
        current_user: User,
        status_filter: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 9,
    ) -> CandidateInterviewListResponse:
        """Fetch interviews for authenticated candidate with dynamic category counts and pagination."""
        profile = await cls.get_candidate_profile(db, current_user.id)
        items, total, counts = await InterviewRepository.get_candidate_interviews(
            db=db,
            candidate_profile_id=str(profile.id),
            candidate_email=current_user.email,
            status_filter=status_filter,
            search=search,
            page=page,
            page_size=page_size,
        )
        serialized = [cls.serialize_interview(i) for i in items]
        total_pages = max(1, (total + page_size - 1) // page_size)
        return CandidateInterviewListResponse(
            items=serialized,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            counts=CandidateInterviewCounts(**counts),
        )

    @classmethod
    async def get_candidate_interview_detail(
        cls,
        db: AsyncSession,
        current_user: User,
        interview_id: str,
    ) -> InterviewResponse:
        """Fetch single interview detail for candidate, enforcing strict candidate authorization."""
        profile = await cls.get_candidate_profile(db, current_user.id)
        interview = await InterviewRepository.get_candidate_interview_by_id(
            db=db,
            interview_id=interview_id,
            candidate_profile_id=str(profile.id),
            candidate_email=current_user.email,
        )
        if not interview:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Interview not found or you do not have permission to view it.",
            )
        return cls.serialize_interview(interview)

    @classmethod
    async def get_recruiter_interviews(
        cls,
        db: AsyncSession,
        current_user: User,
        status_filter: Optional[str] = None,
        job_id: Optional[str] = None,
        application_id: Optional[str] = None,
        candidate_id: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> InterviewListResponse:
        """Fetch interviews for the authenticated recruiter with filters and tab counts."""
        profile = await cls.get_recruiter_profile(db, current_user.id)

        records, total, tab_counts = await InterviewRepository.get_interviews(
            db=db,
            recruiter_id=profile.id,
            status=status_filter,
            job_id=job_id,
            application_id=application_id,
            candidate_id=candidate_id,
            date_from=date_from,
            date_to=date_to,
            search=search,
            page=page,
            page_size=page_size,
        )

        serialized_items = [cls.serialize_interview(r) for r in records]

        return InterviewListResponse(
            items=serialized_items,
            total=total,
            page=page,
            page_size=page_size,
            tab_counts=tab_counts,
        )

    @classmethod
    async def get_interview_detail(
        cls,
        db: AsyncSession,
        current_user: User,
        interview_id: str,
    ) -> InterviewResponse:
        """Fetch interview details ensuring strict recruiter ownership."""
        profile = await cls.get_recruiter_profile(db, current_user.id)

        interview = await InterviewRepository.get_by_id(
            db=db,
            interview_id=interview_id,
            recruiter_id=profile.id,
        )
        if not interview:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Interview not found or unauthorized access.",
            )

        return cls.serialize_interview(interview)

    @classmethod
    async def schedule_interview(
        cls,
        db: AsyncSession,
        current_user: User,
        data: InterviewCreate,
    ) -> InterviewResponse:
        """
        Schedule a new interview for a candidate application.
        Validates application, candidate, job, date/time, and scheduling conflicts.
        Dispatches candidate notification and email invitation.
        """
        profile = await cls.get_recruiter_profile(db, current_user.id)

        # 1. Resolve Application
        application: Optional[CandidateApplication] = None
        if data.application_id is not None:
            application = await InterviewRepository.get_application_for_recruiter(
                db=db,
                application_identifier=data.application_id,
                recruiter_id=profile.id,
            )

        # Fallback resolution via candidate name / job title if application_id wasn't directly supplied
        if not application and (data.candidate_name or data.candidate_email) and data.job_title:
            application = await InterviewRepository.find_application_by_candidate_and_job(
                db=db,
                candidate_name=data.candidate_name or "",
                job_title=data.job_title,
                recruiter_id=profile.id,
                candidate_email=data.candidate_email,
            )

        if not application:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Candidate application '{data.application_id or data.candidate_name}' not found or not accessible.",
            )

        # Validate application status (e.g. not rejected)
        if application.status == "REJECTED":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Cannot schedule an interview for a rejected application.",
            )

        # 2. Extract verified Candidate & Job data from database
        candidate_profile = application.candidate_profile
        candidate_name = candidate_profile.name if candidate_profile else application.candidate_name or "Candidate"
        candidate_email = (
            candidate_profile.user.email
            if candidate_profile and candidate_profile.user
            else (application.candidate_email or data.candidate_email or "candidate@example.com")
        )
        job_title = application.job_title

        # 3. Validate Date & Time
        sched_date = (data.scheduled_date or data.date or "").strip()
        if not sched_date:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Interview date is required.",
            )

        start_time = (data.start_time or data.time or "").strip()
        if not start_time:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Interview start time is required.",
            )

        end_time = (data.end_time or "").strip()
        if not end_time:
            # Default to 1 hour after start
            m_s = time_to_minutes(start_time)
            if m_s is not None:
                m_e = m_s + 60
                end_time = f"{m_e // 60:02d}:{m_e % 60:02d}"
            else:
                end_time = "12:00"

        # Validate time range: start_time < end_time
        m_start = time_to_minutes(start_time)
        m_end = time_to_minutes(end_time)
        if m_start is not None and m_end is not None and m_start >= m_end:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Interview end time must be after the start time.",
            )

        # 4. Validate Format requirements
        format_type = data.format.upper()
        if format_type == "ONLINE" and not data.meeting_link:
            data.meeting_link = "https://meet.google.com/ntr-round"
        if format_type == "OFFLINE" and not data.venue:
            data.venue = profile.registered_office_address or "NTR District Employment Exchange"

        # 5. Parse Panel
        panel_list, panel_display = parse_panel(data.interviewer_panel or data.interviewer or profile.recruiter_name)
        if not panel_display:
            panel_display = profile.recruiter_name

        # 6. Check Scheduling Conflicts (409 Conflict)
        conflict_err = await InterviewRepository.find_conflicts(
            db=db,
            scheduled_date=sched_date,
            start_time=start_time,
            end_time=end_time,
            candidate_profile_id=application.candidate_profile_id,
            candidate_email=candidate_email,
            recruiter_id=profile.id,
            interviewer_panel=panel_list,
        )
        if conflict_err:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=conflict_err,
            )

        # 7. Create Interview Record
        interview_id = str(uuid.uuid4())
        time_str = format_time_display(start_time, end_time, data.timezone)
        type_display = "Online (Google Meet)" if format_type == "ONLINE" else "In-Person (Office Round)"
        notes_content = data.agenda_notes or data.notes

        new_interview = Interview(
            id=interview_id,
            interview_number=f"INT-{uuid.uuid4().hex[:8].upper()}",
            recruiter_id=profile.id,
            candidate_profile_id=application.candidate_profile_id,
            application_id=application.id,
            job_id=application.job_id,
            candidate_name=candidate_name,
            candidate_email=candidate_email,
            job_title=job_title,
            round_name="Technical Round 1",
            interview_type=type_display,
            date=sched_date,
            time=time_str,
            scheduled_date=sched_date,
            start_time=start_time,
            end_time=end_time,
            timezone=data.timezone,
            format=format_type,
            meeting_platform="Google Meet" if format_type == "ONLINE" else "In-Person",
            meeting_link=data.meeting_link if format_type == "ONLINE" else None,
            venue=data.venue if format_type == "OFFLINE" else None,
            interviewer_panel=json.dumps(panel_list) if panel_list else None,
            interviewer=panel_display,
            status="SCHEDULED",
            notes=notes_content,
            agenda_notes=notes_content,
            created_by=profile.recruiter_name,
        )

        created_interview = await InterviewRepository.create(db, new_interview)

        # 8. Update Application Status & Timeline
        application.status = "INTERVIEW"
        if application.timeline_events:
            for ev in application.timeline_events:
                if ev.stage == "Interview":
                    ev.current = True
                    ev.date = f"{sched_date} ({start_time})"

        await db.commit()

        # 9. Trigger Candidate Notification
        if application.candidate_profile_id:
            try:
                notif_msg = (
                    f"Your interview for {job_title} has been scheduled for {sched_date}, "
                    f"{time_str}. Format: {format_type}."
                )
                await NotificationService.create_notification(
                    db=db,
                    candidate_id=application.candidate_profile_id,
                    category="INTERVIEW",
                    title=f"Interview Scheduled: {job_title}",
                    message=notif_msg,
                    link="/candidate/applications",
                    application_id=application.id,
                    interview_id=created_interview.id,
                    job_id=application.job_id,
                )
            except Exception:
                pass

        # 10. Send Email Invite (asynchronous/non-blocking)
        try:
            EmailService.send_interview_invitation_email(
                to_email=candidate_email,
                candidate_name=candidate_name,
                job_title=job_title,
                scheduled_date=sched_date,
                start_time=start_time,
                end_time=end_time,
                timezone=data.timezone,
                format_type=format_type,
                meeting_link=data.meeting_link,
                venue=data.venue,
                interviewer_panel=panel_list,
                agenda_notes=notes_content,
            )
        except Exception:
            pass

        return cls.serialize_interview(created_interview)

    @classmethod
    async def reschedule_interview(
        cls,
        db: AsyncSession,
        current_user: User,
        interview_id: str,
        data: InterviewUpdate,
    ) -> InterviewResponse:
        """Reschedule an existing interview to a new date and time slot."""
        profile = await cls.get_recruiter_profile(db, current_user.id)

        interview = await InterviewRepository.get_by_id(
            db=db,
            interview_id=interview_id,
            recruiter_id=profile.id,
        )
        if not interview:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Interview not found or unauthorized access.",
            )

        if interview.status == "CANCELLED":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Cannot reschedule a cancelled interview.",
            )

        new_date = (data.scheduled_date or data.date or interview.scheduled_date or interview.date).strip()
        new_start = (data.start_time or data.time or interview.start_time or "14:00").strip()
        new_end = (data.end_time or interview.end_time or "").strip()
        if not new_end:
            m_s = time_to_minutes(new_start)
            if m_s is not None:
                new_end = f"{(m_s + 60) // 60:02d}:{(m_s + 60) % 60:02d}"
            else:
                new_end = "15:00"

        # Validate time range
        m_start = time_to_minutes(new_start)
        m_end = time_to_minutes(new_end)
        if m_start is not None and m_end is not None and m_start >= m_end:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Interview end time must be after the start time.",
            )

        panel_list, panel_display = parse_panel(data.interviewer_panel or data.interviewer or interview.interviewer_panel)

        # Check Conflict excluding this interview
        conflict_err = await InterviewRepository.find_conflicts(
            db=db,
            scheduled_date=new_date,
            start_time=new_start,
            end_time=new_end,
            candidate_profile_id=interview.candidate_profile_id,
            candidate_email=interview.candidate_email,
            recruiter_id=profile.id,
            interviewer_panel=panel_list,
            exclude_interview_id=interview.id,
        )
        if conflict_err:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=conflict_err,
            )

        # Update interview
        time_str = format_time_display(new_start, new_end, data.timezone or interview.timezone or "Asia/Kolkata")
        interview.scheduled_date = new_date
        interview.date = new_date
        interview.start_time = new_start
        interview.end_time = new_end
        interview.time = time_str
        interview.status = "RESCHEDULED"
        if data.format:
            interview.format = data.format.upper()
        if data.meeting_link:
            interview.meeting_link = data.meeting_link
        if data.venue:
            interview.venue = data.venue
        if panel_list:
            interview.interviewer_panel = json.dumps(panel_list)
            interview.interviewer = panel_display
        if data.agenda_notes or data.notes:
            interview.agenda_notes = data.agenda_notes or data.notes
            interview.notes = data.agenda_notes or data.notes

        updated = await InterviewRepository.update(db, interview)

        # Candidate Notification
        if interview.candidate_profile_id:
            try:
                await NotificationService.create_notification(
                    db=db,
                    candidate_id=interview.candidate_profile_id,
                    category="INTERVIEW",
                    title=f"Interview Rescheduled: {interview.job_title}",
                    message=f"Your interview has been rescheduled to {new_date} at {time_str}.",
                    link="/candidate/applications",
                    application_id=interview.application_id,
                    interview_id=interview.id,
                    job_id=interview.job_id,
                )
            except Exception:
                pass

        return cls.serialize_interview(updated)

    @classmethod
    async def cancel_interview(
        cls,
        db: AsyncSession,
        current_user: User,
        interview_id: str,
        data: InterviewCancel,
    ) -> InterviewResponse:
        """Cancel an interview, preserving the record and recording reason and timestamp."""
        profile = await cls.get_recruiter_profile(db, current_user.id)

        interview = await InterviewRepository.get_by_id(
            db=db,
            interview_id=interview_id,
            recruiter_id=profile.id,
        )
        if not interview:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Interview not found or unauthorized access.",
            )

        interview.status = "CANCELLED"
        interview.cancelled_at = datetime.now(timezone.utc)
        interview.cancellation_reason = data.reason

        updated = await InterviewRepository.update(db, interview)

        # Candidate Notification
        if interview.candidate_profile_id:
            try:
                await NotificationService.create_notification(
                    db=db,
                    candidate_id=interview.candidate_profile_id,
                    category="INTERVIEW",
                    title=f"Interview Cancelled: {interview.job_title}",
                    message=f"Your interview for {interview.job_title} has been cancelled. Reason: {data.reason}",
                    link="/candidate/applications",
                    application_id=interview.application_id,
                    interview_id=interview.id,
                    job_id=interview.job_id,
                )
            except Exception:
                pass

        return cls.serialize_interview(updated)

    @classmethod
    async def complete_interview(
        cls,
        db: AsyncSession,
        current_user: User,
        interview_id: str,
        data: InterviewComplete,
    ) -> InterviewResponse:
        """Mark an interview as completed, recording evaluation notes and timestamp."""
        profile = await cls.get_recruiter_profile(db, current_user.id)

        interview = await InterviewRepository.get_by_id(
            db=db,
            interview_id=interview_id,
            recruiter_id=profile.id,
        )
        if not interview:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Interview not found or unauthorized access.",
            )

        if interview.status == "CANCELLED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot complete a cancelled interview.",
            )

        interview.status = "COMPLETED"
        interview.completed_at = datetime.now(timezone.utc)
        if data.notes:
            interview.notes = data.notes
            existing = interview.agenda_notes or ""
            interview.agenda_notes = f"{existing}\n\n[Completion Notes]: {data.notes}".strip()

        updated = await InterviewRepository.update(db, interview)
        return cls.serialize_interview(updated)
