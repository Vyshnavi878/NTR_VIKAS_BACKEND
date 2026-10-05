import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.recruiter import RecruiterProfile
from app.models.recruiter_support import RecruiterSupportRequest

logger = logging.getLogger(__name__)


class SupportRepository:
    """
    Async repository layer for Recruiter Support operations.
    Handles persistence and queries to MySQL via SQLAlchemy 2.0 AsyncIO and asyncmy.
    """

    @staticmethod
    async def get_recruiter_profile_by_user_id(
        db: AsyncSession, user_id: str
    ) -> Optional[RecruiterProfile]:
        """Fetch recruiter profile by authenticated user's ID."""
        stmt = select(RecruiterProfile).where(RecruiterProfile.user_id == user_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_next_ticket_number(db: AsyncSession) -> str:
        """
        Derive the next ticket number in SUP-XXXXXX format by finding the highest ticket number.
        Zero-padded 6 digits ensures lexicographical sorting matches numerical sorting.
        """
        stmt = (
            select(RecruiterSupportRequest.ticket_number)
            .where(RecruiterSupportRequest.ticket_number.like("SUP-%"))
            .order_by(RecruiterSupportRequest.ticket_number.desc())
            .limit(1)
        )
        result = await db.execute(stmt)
        last_ticket = result.scalar_one_or_none()

        next_num = 1
        if last_ticket and last_ticket.startswith("SUP-"):
            try:
                suffix = last_ticket.replace("SUP-", "").strip()
                next_num = int(suffix) + 1
            except (ValueError, TypeError):
                next_num = 1

        return f"SUP-{next_num:06d}"

    @staticmethod
    async def get_recent_duplicate(
        db: AsyncSession,
        recruiter_id: str,
        issue_category: str,
        subject: str,
        description: str,
        seconds: int = 30,
    ) -> Optional[RecruiterSupportRequest]:
        """Check for rapid duplicate submission from the same recruiter."""
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=seconds)
        stmt = (
            select(RecruiterSupportRequest)
            .where(
                and_(
                    RecruiterSupportRequest.recruiter_id == recruiter_id,
                    RecruiterSupportRequest.issue_category == issue_category,
                    RecruiterSupportRequest.subject == subject,
                    RecruiterSupportRequest.description == description,
                    RecruiterSupportRequest.created_at >= cutoff,
                )
            )
            .order_by(RecruiterSupportRequest.created_at.desc())
            .limit(1)
        )
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    @staticmethod
    async def create_support_request(
        db: AsyncSession,
        recruiter_id: str,
        company_name: str,
        recruiter_name: str,
        registered_email: str,
        issue_category: str,
        subject: str,
        description: str,
        priority: str = "NORMAL",
    ) -> RecruiterSupportRequest:
        """Create and persist a new recruiter support request in MySQL."""
        ticket_number = await SupportRepository.get_next_ticket_number(db)
        support_request = RecruiterSupportRequest(
            ticket_number=ticket_number,
            recruiter_id=recruiter_id,
            company_name=company_name,
            recruiter_name=recruiter_name,
            registered_email=registered_email,
            issue_category=issue_category,
            subject=subject,
            description=description,
            status="OPEN",
            priority=priority,
        )
        db.add(support_request)
        await db.commit()
        await db.refresh(support_request)
        return support_request

    @staticmethod
    async def get_recruiter_support_requests(
        db: AsyncSession, recruiter_id: str
    ) -> List[RecruiterSupportRequest]:
        """Fetch all support requests submitted by a specific recruiter, newest first."""
        stmt = (
            select(RecruiterSupportRequest)
            .where(RecruiterSupportRequest.recruiter_id == recruiter_id)
            .order_by(
                RecruiterSupportRequest.created_at.desc(),
                RecruiterSupportRequest.id.desc(),
            )
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_support_request_by_id(
        db: AsyncSession, request_id: str, recruiter_id: str
    ) -> Optional[RecruiterSupportRequest]:
        """Fetch a specific support request ensuring ownership check."""
        stmt = select(RecruiterSupportRequest).where(
            and_(
                RecruiterSupportRequest.id == request_id,
                RecruiterSupportRequest.recruiter_id == recruiter_id,
            )
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
