import uuid
from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.support_ticket import SupportTicket
from app.models.candidate import CandidateProfile


class SupportTicketRepository:
    """Repository handling MySQL queries and persistence for candidate support tickets."""

    @staticmethod
    async def get_candidate_profile(db: AsyncSession, user_id: str) -> Optional[CandidateProfile]:
        """Fetch candidate profile by user ID."""
        stmt = (
            select(CandidateProfile)
            .where(CandidateProfile.user_id == user_id)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_next_ticket_number(db: AsyncSession) -> str:
        """
        Derive next ticket number in NTR-SUP-XXXXXX format by querying the highest ticket_number.
        Since numbers are zero-padded (6 digits), lexicographical order matches numerical order.
        """
        stmt = (
            select(SupportTicket.ticket_number)
            .where(SupportTicket.ticket_number.like("NTR-SUP-%"))
            .order_by(SupportTicket.ticket_number.desc())
            .limit(1)
        )
        result = await db.execute(stmt)
        last_ticket = result.scalar_one_or_none()

        next_num = 1
        if last_ticket and last_ticket.startswith("NTR-SUP-"):
            try:
                suffix = last_ticket.replace("NTR-SUP-", "").strip()
                next_num = int(suffix) + 1
            except (ValueError, TypeError):
                next_num = 1

        return f"NTR-SUP-{next_num:06d}"

    @staticmethod
    async def create_ticket(
        db: AsyncSession,
        candidate_id: str,
        candidate_name: str,
        registered_email: str,
        issue_category: str,
        subject: str,
        description: str,
        priority: str = "NORMAL",
    ) -> SupportTicket:
        """
        Create and persist a new support ticket with status=OPEN.
        Includes a concurrency retry loop in case of racing ticket numbers.
        """
        for attempt in range(5):
            ticket_number = await SupportTicketRepository.get_next_ticket_number(db)

            new_ticket = SupportTicket(
                id=str(uuid.uuid4()),
                ticket_number=ticket_number,
                candidate_id=candidate_id,
                candidate_name=candidate_name,
                registered_email=registered_email,
                issue_category=issue_category,
                subject=subject,
                description=description,
                status="OPEN",
                priority=priority,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            try:
                db.add(new_ticket)
                await db.commit()
                await db.refresh(new_ticket)
                return new_ticket
            except IntegrityError:
                await db.rollback()
                if attempt == 4:
                    raise

    @staticmethod
    async def get_candidate_tickets(db: AsyncSession, candidate_id: str) -> List[SupportTicket]:
        """Fetch all support tickets submitted by a candidate ordered newest first."""
        stmt = (
            select(SupportTicket)
            .where(SupportTicket.candidate_id == candidate_id)
            .order_by(SupportTicket.created_at.desc(), SupportTicket.id.desc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_ticket_by_number(db: AsyncSession, ticket_number: str) -> Optional[SupportTicket]:
        """Fetch support ticket by ticket number."""
        stmt = select(SupportTicket).where(SupportTicket.ticket_number == ticket_number)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
