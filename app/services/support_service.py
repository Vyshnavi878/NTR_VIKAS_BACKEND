import logging
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.recruiter_support import (
    RecruiterSupportRequestCreate,
    RecruiterSupportRequestResponse,
    RecruiterSupportRequestItem,
    RecruiterSupportRequestListResponse,
)
from app.repositories.support_repository import SupportRepository
from app.services.email_service import EmailService

logger = logging.getLogger(__name__)


class SupportService:
    """
    Service layer handling business rules and orchestration for Recruiter Support requests.
    """

    @classmethod
    async def get_recruiter_profile(cls, db: AsyncSession, user_id: str):
        """Fetch and validate that the user has an associated recruiter profile."""
        profile = await SupportRepository.get_recruiter_profile_by_user_id(db, user_id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recruiter profile not found. Please complete company registration.",
            )
        return profile

    @classmethod
    async def create_support_request(
        cls,
        db: AsyncSession,
        current_user: User,
        data: RecruiterSupportRequestCreate,
    ) -> RecruiterSupportRequestResponse:
        """
        Create a new recruiter support request in MySQL.
        1. Resolve authenticated recruiter profile.
        2. Prevent rapid duplicate submissions.
        3. Persist support request to MySQL.
        4. Optionally dispatch email acknowledgement.
        5. Return safe 201 response.
        """
        profile = await cls.get_recruiter_profile(db, current_user.id)

        clean_category = data.issue_category.strip()
        clean_subject = data.subject.strip()
        clean_description = data.description.strip()

        # Check for rapid duplicate submission from the same recruiter (within 30s)
        duplicate = await SupportRepository.get_recent_duplicate(
            db=db,
            recruiter_id=profile.id,
            issue_category=clean_category,
            subject=clean_subject,
            description=clean_description,
            seconds=30,
        )
        if duplicate:
            logger.info(
                f"Returning existing support ticket {duplicate.ticket_number} for duplicate request by recruiter {profile.id}"
            )
            return RecruiterSupportRequestResponse(
                message="Support request submitted successfully.",
                ticket_number=duplicate.ticket_number,
                status=duplicate.status,
            )

        registered_email = profile.work_email or current_user.email

        # Create support request in MySQL
        ticket = await SupportRepository.create_support_request(
            db=db,
            recruiter_id=profile.id,
            company_name=profile.company_name,
            recruiter_name=profile.recruiter_name,
            registered_email=registered_email,
            issue_category=clean_category,
            subject=clean_subject,
            description=clean_description,
            priority="NORMAL",
        )

        # Optional email notification (non-blocking, failures safely swallowed)
        try:
            logger.info(
                f"Support ticket {ticket.ticket_number} created for {registered_email} ({profile.company_name})"
            )
        except Exception as e:
            logger.warning(f"Could not send email notification for ticket {ticket.ticket_number}: {e}")

        return RecruiterSupportRequestResponse(
            message="Support request submitted successfully.",
            ticket_number=ticket.ticket_number,
            status=ticket.status,
        )

    @classmethod
    async def get_recruiter_support_requests(
        cls,
        db: AsyncSession,
        current_user: User,
    ) -> RecruiterSupportRequestListResponse:
        """Fetch all support tickets belonging to the authenticated recruiter."""
        profile = await cls.get_recruiter_profile(db, current_user.id)
        tickets = await SupportRepository.get_recruiter_support_requests(db, profile.id)

        items = [
            RecruiterSupportRequestItem(
                id=t.id,
                ticket_number=t.ticket_number,
                recruiter_id=t.recruiter_id,
                company_name=t.company_name,
                recruiter_name=t.recruiter_name,
                registered_email=t.registered_email,
                issue_category=t.issue_category,
                subject=t.subject,
                description=t.description,
                status=t.status,
                priority=t.priority,
                created_at=t.created_at,
                updated_at=t.updated_at,
            )
            for t in tickets
        ]
        return RecruiterSupportRequestListResponse(items=items, total=len(items))
