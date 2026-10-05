from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_database, get_current_candidate
from app.models.user import User
from app.schemas.support_ticket import (
    SupportTicketCreate,
    SupportTicketItem,
    SupportTicketCreateResponse,
    SupportTicketListResponse,
)
from app.services.support_ticket_service import SupportTicketService

router = APIRouter(
    prefix="/candidate/support",
    tags=["Candidate Support"],
)


@router.post(
    "/tickets",
    response_model=SupportTicketCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a new support ticket",
    description="Creates a new support ticket for the authenticated candidate and persists it in MySQL.",
)
async def create_support_ticket(
    ticket_in: SupportTicketCreate,
    db: AsyncSession = Depends(get_database),
    current_user: User = Depends(get_current_candidate),
):
    return await SupportTicketService.create_ticket(
        db=db, current_user=current_user, ticket_in=ticket_in
    )


@router.get(
    "/tickets",
    response_model=SupportTicketListResponse,
    status_code=status.HTTP_200_OK,
    summary="List candidate's support tickets",
    description="Returns all support tickets submitted by the authenticated candidate.",
)
async def list_candidate_tickets(
    db: AsyncSession = Depends(get_database),
    current_user: User = Depends(get_current_candidate),
):
    return await SupportTicketService.get_my_tickets(db=db, current_user=current_user)


@router.get(
    "/tickets/{ticket_number}",
    response_model=SupportTicketItem,
    status_code=status.HTTP_200_OK,
    summary="Get candidate support ticket details",
    description="Returns details for a specific support ticket belonging to the authenticated candidate.",
)
async def get_candidate_ticket_details(
    ticket_number: str,
    db: AsyncSession = Depends(get_database),
    current_user: User = Depends(get_current_candidate),
):
    return await SupportTicketService.get_ticket_details(
        db=db, current_user=current_user, ticket_number=ticket_number
    )
