from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.schemas.support_ticket import (
    SupportTicketCreate,
    SupportTicketItem,
    SupportTicketCreateResponse,
    SupportTicketListResponse,
)
from app.repositories.support_ticket_repository import SupportTicketRepository


class SupportTicketService:
    """Service encapsulating business logic, candidate authorization, and ticket formatting."""

    @staticmethod
    async def _resolve_candidate(db: AsyncSession, current_user: User):
        """Verify role and resolve candidate profile."""
        if current_user.role.upper() != "CANDIDATE":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only authenticated candidates can access candidate support tickets.",
            )
        profile = await SupportTicketRepository.get_candidate_profile(db, current_user.id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Candidate profile not found for this account.",
            )
        return profile

    @staticmethod
    def _serialize_ticket(ticket) -> SupportTicketItem:
        """Map SQLAlchemy model to Pydantic schema."""
        return SupportTicketItem(
            id=ticket.id,
            ticket_number=ticket.ticket_number,
            candidate_id=ticket.candidate_id,
            candidate_name=ticket.candidate_name,
            registered_email=ticket.registered_email,
            issue_category=ticket.issue_category,
            subject=ticket.subject,
            description=ticket.description,
            status=ticket.status,
            priority=ticket.priority,
            created_at=ticket.created_at.isoformat() if ticket.created_at else "",
            updated_at=ticket.updated_at.isoformat() if ticket.updated_at else None,
            resolved_at=ticket.resolved_at.isoformat() if ticket.resolved_at else None,
            closed_at=ticket.closed_at.isoformat() if ticket.closed_at else None,
        )

    @classmethod
    async def create_ticket(
        cls, db: AsyncSession, current_user: User, ticket_in: SupportTicketCreate
    ) -> SupportTicketCreateResponse:
        """
        Create a new support ticket in MySQL.
        Candidate identity (name and email) is strictly derived from the authenticated account.
        """
        candidate_profile = await cls._resolve_candidate(db, current_user)

        candidate_name = candidate_profile.name or "Candidate"
        registered_email = current_user.email

        ticket = await SupportTicketRepository.create_ticket(
            db=db,
            candidate_id=candidate_profile.id,
            candidate_name=candidate_name,
            registered_email=registered_email,
            issue_category=ticket_in.issue_category,
            subject=ticket_in.subject,
            description=ticket_in.description,
            priority="NORMAL",
        )

        serialized = cls._serialize_ticket(ticket)
        return SupportTicketCreateResponse(
            message="Support request submitted successfully.",
            ticket=serialized,
        )

    @classmethod
    async def get_my_tickets(
        cls, db: AsyncSession, current_user: User
    ) -> SupportTicketListResponse:
        """Retrieve all tickets belonging to the authenticated candidate."""
        candidate_profile = await cls._resolve_candidate(db, current_user)
        tickets = await SupportTicketRepository.get_candidate_tickets(db, candidate_profile.id)
        items = [cls._serialize_ticket(t) for t in tickets]
        return SupportTicketListResponse(items=items, total=len(items))

    @classmethod
    async def get_ticket_details(
        cls, db: AsyncSession, current_user: User, ticket_number: str
    ) -> SupportTicketItem:
        """
        Retrieve ticket details by ticket number.
        Strictly verifies ownership: if ticket belongs to another candidate or does not exist,
        returns 404 to avoid leaking existence information.
        """
        candidate_profile = await cls._resolve_candidate(db, current_user)
        ticket = await SupportTicketRepository.get_ticket_by_number(db, ticket_number.strip())

        if not ticket or ticket.candidate_id != candidate_profile.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Support ticket '{ticket_number}' not found.",
            )

        return cls._serialize_ticket(ticket)
