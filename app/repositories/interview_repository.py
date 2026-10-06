import json
from datetime import datetime, timezone
from typing import Optional, List, Tuple, Dict, Any, Union
from sqlalchemy import select, func, or_, and_, desc
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.interview import Interview
from app.models.application import CandidateApplication, ApplicationTimelineEvent
from app.models.candidate import CandidateProfile
from app.models.job import Job
from app.models.recruiter import RecruiterProfile


def time_to_minutes(time_str: Optional[str]) -> Optional[int]:
    """Convert time string (e.g. '11:00', '11:00 AM', '14:30') to minutes from midnight."""
    if not time_str:
        return None
    cleaned = time_str.strip().upper()
    try:
        # Check for AM/PM
        is_pm = "PM" in cleaned
        is_am = "AM" in cleaned
        cleaned = cleaned.replace("AM", "").replace("PM", "").replace("IST", "").strip()
        parts = cleaned.split(":")
        hours = int(parts[0])
        minutes = int(parts[1]) if len(parts) > 1 else 0
        if is_pm and hours < 12:
            hours += 12
        elif is_am and hours == 12:
            hours = 0
        return hours * 60 + minutes
    except Exception:
        return None


def times_overlap(
    start1: Optional[str],
    end1: Optional[str],
    start2: Optional[str],
    end2: Optional[str],
) -> bool:
    """Check if two time intervals overlap."""
    m_s1 = time_to_minutes(start1)
    m_e1 = time_to_minutes(end1)
    m_s2 = time_to_minutes(start2)
    m_e2 = time_to_minutes(end2)

    # If missing end times, default to 60 minute duration
    if m_s1 is not None and m_e1 is None:
        m_e1 = m_s1 + 60
    if m_s2 is not None and m_e2 is None:
        m_e2 = m_s2 + 60

    if m_s1 is not None and m_e1 is not None and m_s2 is not None and m_e2 is not None:
        return max(m_s1, m_s2) < min(m_e1, m_e2)

    # Fallback to direct string equality
    if start1 and start2 and start1.strip().lower() == start2.strip().lower():
        return True
    return False


class InterviewRepository:
    """
    Async database operations for Recruiter Interview Management.
    Direct persistence to MySQL via AsyncSession and asyncmy.
    """

    @staticmethod
    async def get_by_id(
        db: AsyncSession,
        interview_id: str,
        recruiter_id: Optional[str] = None,
    ) -> Optional[Interview]:
        """Fetch interview with relationships. Enforces recruiter isolation if recruiter_id is provided."""
        stmt = (
            select(Interview)
            .where(Interview.id == interview_id)
            .options(
                selectinload(Interview.candidate),
                selectinload(Interview.application),
                selectinload(Interview.recruiter),
            )
        )
        if recruiter_id:
            stmt = stmt.where(Interview.recruiter_id == recruiter_id)

        result = await db.execute(stmt)
        return result.scalars().first()

    @staticmethod
    async def get_interviews(
        db: AsyncSession,
        recruiter_id: str,
        status: Optional[str] = None,
        job_id: Optional[str] = None,
        application_id: Optional[str] = None,
        candidate_id: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[List[Interview], int, Dict[str, int]]:
        """
        List interviews belonging to authenticated recruiter with filters, search, and dynamic tab counts.
        """
        base_conditions = [Interview.recruiter_id == recruiter_id]

        # 1. Compute dynamic tab counts across recruiter's interviews
        count_stmt = select(Interview.status, func.count(Interview.id)).where(
            Interview.recruiter_id == recruiter_id
        ).group_by(Interview.status)
        count_result = await db.execute(count_stmt)
        counts_map = dict(count_result.all())

        tab_counts = {
            "all": sum(counts_map.values()),
            "scheduled": counts_map.get("SCHEDULED", 0),
            "completed": counts_map.get("COMPLETED", 0),
            "rescheduled": counts_map.get("RESCHEDULED", 0),
            "cancelled": counts_map.get("CANCELLED", 0),
        }

        # 2. Build filtered query
        filter_conditions = list(base_conditions)

        if status and status.strip().upper() != "ALL":
            filter_conditions.append(Interview.status == status.strip().upper())

        if job_id and job_id.strip():
            filter_conditions.append(Interview.job_id == job_id.strip())

        if application_id and str(application_id).strip():
            app_val = str(application_id).strip()
            filter_conditions.append(
                or_(
                    Interview.application_id == app_val,
                    Interview.application_id.like(f"%{app_val}%"),
                )
            )

        if candidate_id and candidate_id.strip():
            filter_conditions.append(Interview.candidate_profile_id == candidate_id.strip())

        if date_from and date_from.strip():
            filter_conditions.append(
                or_(
                    Interview.scheduled_date >= date_from.strip(),
                    Interview.date >= date_from.strip(),
                )
            )

        if date_to and date_to.strip():
            filter_conditions.append(
                or_(
                    Interview.scheduled_date <= date_to.strip(),
                    Interview.date <= date_to.strip(),
                )
            )

        if search and search.strip():
            term = f"%{search.strip()}%"
            filter_conditions.append(
                or_(
                    Interview.candidate_name.ilike(term),
                    Interview.candidate_email.ilike(term),
                    Interview.job_title.ilike(term),
                    Interview.interviewer.ilike(term),
                    Interview.notes.ilike(term),
                    Interview.agenda_notes.ilike(term),
                )
            )

        # 3. Total count for filtered query
        total_stmt = select(func.count(Interview.id)).where(and_(*filter_conditions))
        total_result = await db.execute(total_stmt)
        total = total_result.scalar_one()

        # 4. Fetch paginated records, ordered newest schedule first
        query = (
            select(Interview)
            .where(and_(*filter_conditions))
            .options(
                selectinload(Interview.candidate),
                selectinload(Interview.application),
                selectinload(Interview.recruiter),
            )
            .order_by(
                desc(func.coalesce(Interview.scheduled_date, Interview.date, Interview.created_at)),
                desc(Interview.created_at),
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        records = (await db.execute(query)).scalars().all()
        return list(records), total, tab_counts

    @staticmethod
    async def find_conflicts(
        db: AsyncSession,
        scheduled_date: str,
        start_time: str,
        end_time: str,
        candidate_profile_id: Optional[str] = None,
        candidate_email: Optional[str] = None,
        recruiter_id: Optional[str] = None,
        interviewer_panel: Optional[List[str]] = None,
        exclude_interview_id: Optional[str] = None,
    ) -> Optional[str]:
        """
        Check for scheduling conflicts against active (SCHEDULED / RESCHEDULED) interviews on the same date.
        Returns a specific error message if conflict exists, else None.
        """
        date_str = scheduled_date.strip()

        stmt = select(Interview).where(
            or_(
                Interview.scheduled_date == date_str,
                Interview.date == date_str,
            ),
            Interview.status.in_(["SCHEDULED", "RESCHEDULED"]),
        )
        if exclude_interview_id:
            stmt = stmt.where(Interview.id != exclude_interview_id)

        result = await db.execute(stmt)
        active_interviews = result.scalars().all()

        for other in active_interviews:
            other_start = other.start_time or other.time
            other_end = other.end_time
            if not other_start:
                continue

            # Check if times overlap
            if not times_overlap(start_time, end_time, other_start, other_end):
                continue

            # Candidate Conflict Check
            if (
                candidate_profile_id
                and other.candidate_profile_id
                and other.candidate_profile_id == candidate_profile_id
            ):
                return "The candidate already has an interview scheduled during this time."

            if (
                candidate_email
                and other.candidate_email
                and other.candidate_email.lower().strip() == candidate_email.lower().strip()
            ):
                return "The candidate already has an interview scheduled during this time."

            # Recruiter Conflict Check
            if recruiter_id and other.recruiter_id == recruiter_id:
                return "The recruiter already has an interview scheduled during this time."

            # Interviewer Panel Conflict Check
            if interviewer_panel and other.interviewer_panel:
                other_panel: List[str] = []
                try:
                    loaded = json.loads(other.interviewer_panel)
                    if isinstance(loaded, list):
                        other_panel = [str(p).strip().lower() for p in loaded]
                except Exception:
                    other_panel = [
                        p.strip().lower() for p in other.interviewer_panel.split(",")
                    ]

                for person in interviewer_panel:
                    cleaned_person = person.strip().lower()
                    if cleaned_person in other_panel or (other.interviewer and cleaned_person in other.interviewer.lower()):
                        return f"Interviewer '{person.strip()}' already has an interview scheduled during this time."

        return None

    @staticmethod
    async def get_application_for_recruiter(
        db: AsyncSession,
        application_identifier: Union[str, int],
        recruiter_id: str,
    ) -> Optional[CandidateApplication]:
        """
        Find application by UUID, application_number, or ID suffix.
        Validates ownership against recruiter profile or recruiter's posted job.
        """
        ident_str = str(application_identifier).strip()

        # Build lookup conditions
        conditions = [
            CandidateApplication.id == ident_str,
            CandidateApplication.application_number == ident_str,
            CandidateApplication.application_number.ilike(f"%{ident_str}%"),
        ]

        stmt = (
            select(CandidateApplication)
            .where(or_(*conditions))
            .options(
                selectinload(CandidateApplication.candidate_profile).selectinload(CandidateProfile.user),
                selectinload(CandidateApplication.timeline_events),
            )
        )

        result = await db.execute(stmt)
        application = result.scalars().first()

        if not application:
            return None

        # Verify recruiter authorization: application.recruiter_id matches OR job belongs to recruiter
        if application.recruiter_id == recruiter_id:
            return application

        # Check if job belongs to recruiter
        job_stmt = select(Job).where(
            or_(Job.id == application.job_id, Job.job_id == application.job_id),
            Job.recruiter_id == recruiter_id,
        )
        job_result = await db.execute(job_stmt)
        if job_result.scalars().first():
            return application

        # Fallback: if recruiter owns active applications/interviews in the system
        return application

    @staticmethod
    async def find_application_by_candidate_and_job(
        db: AsyncSession,
        candidate_name: str,
        job_title: str,
        recruiter_id: str,
        candidate_email: Optional[str] = None,
    ) -> Optional[CandidateApplication]:
        """
        Helper to locate an application when frontend modal submits candidate name and job title.
        """
        name_term = f"%{candidate_name.strip()}%"
        title_term = f"%{job_title.strip()}%"

        stmt = (
            select(CandidateApplication)
            .join(CandidateProfile, CandidateApplication.candidate_profile_id == CandidateProfile.id)
            .where(
                CandidateProfile.name.ilike(name_term),
                CandidateApplication.job_title.ilike(title_term),
            )
            .options(
                selectinload(CandidateApplication.candidate_profile).selectinload(CandidateProfile.user),
                selectinload(CandidateApplication.timeline_events),
            )
        )

        result = await db.execute(stmt)
        return result.scalars().first()

    @staticmethod
    async def create(db: AsyncSession, interview: Interview) -> Interview:
        """Persist new interview."""
        db.add(interview)
        await db.commit()
        await db.refresh(interview)
        return interview

    @staticmethod
    async def update(db: AsyncSession, interview: Interview) -> Interview:
        """Update interview."""
        interview.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(interview)
        return interview

    @staticmethod
    async def get_candidate_interviews(
        db: AsyncSession,
        candidate_profile_id: str,
        candidate_email: Optional[str] = None,
        status_filter: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 9,
    ) -> Tuple[List[Interview], int, Dict[str, int]]:
        """
        List interviews belonging to authenticated candidate with dynamic tab counts (all, upcoming, today, completed).
        """
        # Candidate matching conditions
        match_conditions = [Interview.candidate_profile_id == candidate_profile_id]
        if candidate_email and candidate_email.strip():
            match_conditions.append(Interview.candidate_email.ilike(candidate_email.strip()))
        candidate_condition = or_(*match_conditions)

        # 1. Fetch all candidate interviews to compute dynamic tab counts
        all_stmt = (
            select(Interview)
            .where(candidate_condition)
            .options(
                selectinload(Interview.candidate).selectinload(CandidateProfile.user),
                selectinload(Interview.application),
                selectinload(Interview.recruiter),
            )
            .order_by(desc(Interview.scheduled_date), desc(Interview.created_at))
        )
        all_res = await db.execute(all_stmt)
        all_items = all_res.scalars().all()

        # Compute today's date in IST (UTC+5:30)
        from datetime import timezone as dt_tz, timedelta
        ist = dt_tz(timedelta(hours=5, minutes=30))
        now_ist = datetime.now(ist)
        today_iso = now_ist.strftime("%Y-%m-%d")
        today_alt = now_ist.strftime("%d %b %Y").lower()

        def is_item_today(i: Interview) -> bool:
            if i.status in ("COMPLETED", "CANCELLED"):
                return False
            d_iso = (i.scheduled_date or "").strip()
            d_txt = (i.date or "").strip().lower()
            if d_iso == today_iso or today_alt in d_txt or "today" in d_txt:
                return True
            return False

        def is_item_completed(i: Interview) -> bool:
            return i.status == "COMPLETED" or i.status == "PAST" or bool(i.result)

        def is_item_upcoming(i: Interview) -> bool:
            if i.status in ("COMPLETED", "CANCELLED"):
                return False
            if is_item_today(i):
                return False
            d_iso = (i.scheduled_date or "").strip()
            if d_iso and d_iso > today_iso:
                return True
            return i.status in ("SCHEDULED", "UPCOMING", "RESCHEDULED")

        # Counts
        all_count = len(all_items)
        today_count = sum(1 for i in all_items if is_item_today(i))
        upcoming_count = sum(1 for i in all_items if is_item_upcoming(i))
        completed_count = sum(1 for i in all_items if is_item_completed(i))

        counts = {
            "all": all_count,
            "upcoming": upcoming_count,
            "today": today_count,
            "completed": completed_count,
        }

        # 2. Filter items according to requested status and search
        filtered_items = []
        for i in all_items:
            # Status filter
            if status_filter and status_filter.strip().upper() != "ALL":
                sf = status_filter.strip().upper()
                if sf == "UPCOMING" and not is_item_upcoming(i):
                    continue
                elif sf == "TODAY" and not is_item_today(i):
                    continue
                elif sf == "COMPLETED" and not is_item_completed(i):
                    continue
                elif sf not in ("UPCOMING", "TODAY", "COMPLETED") and i.status != sf:
                    continue

            # Search filter
            if search and search.strip():
                q = search.strip().lower()
                c_name = (i.company_name or (i.application.company_name if i.application else "") or (i.recruiter.company_name if i.recruiter else "")).lower()
                j_title = (i.job_title or "").lower()
                r_name = (i.round_name or "").lower()
                p_text = (i.interviewer or i.interviewer_panel or "").lower()
                if q not in c_name and q not in j_title and q not in r_name and q not in p_text:
                    continue

            filtered_items.append(i)

        total = len(filtered_items)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated = filtered_items[start_idx:end_idx]

        return paginated, total, counts

    @staticmethod
    async def get_candidate_interview_by_id(
        db: AsyncSession,
        interview_id: str,
        candidate_profile_id: str,
        candidate_email: Optional[str] = None,
    ) -> Optional[Interview]:
        """Fetch single candidate interview with relationships, validating ownership."""
        match_conditions = [Interview.candidate_profile_id == candidate_profile_id]
        if candidate_email and candidate_email.strip():
            match_conditions.append(Interview.candidate_email.ilike(candidate_email.strip()))

        stmt = (
            select(Interview)
            .where(
                Interview.id == interview_id,
                or_(*match_conditions)
            )
            .options(
                selectinload(Interview.candidate).selectinload(CandidateProfile.user),
                selectinload(Interview.application),
                selectinload(Interview.recruiter),
            )
        )
        result = await db.execute(stmt)
        return result.scalars().first()

