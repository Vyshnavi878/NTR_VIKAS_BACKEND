from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User
from app.models.candidate import CandidateProfile
from app.models.notification import Notification
from app.repositories.notification_repository import NotificationRepository
from app.schemas.notification import (
    NotificationItem,
    NotificationListResponse,
    UnreadCountResponse,
    MarkNotificationsRequest,
    DismissNotificationsRequest,
    NotificationActionResponse,
    BulkNotificationDeleteRequest,
    NotificationDeleteResponse,
    BulkNotificationDeleteResponse,
)


class NotificationService:
    """
    Business service layer for Candidate Notifications.
    Enforces candidate identity, ownership validation, and event dispatch.
    """

    @staticmethod
    async def get_candidate_profile(
        db: AsyncSession,
        user_id: str,
    ) -> CandidateProfile:
        stmt = select(CandidateProfile).where(CandidateProfile.user_id == user_id)
        result = await db.execute(stmt)
        profile = result.scalar_one_or_none()
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Candidate profile not found.",
            )
        return profile

    @classmethod
    async def get_notifications(
        cls,
        db: AsyncSession,
        current_user: User,
        search: Optional[str] = None,
        category: Optional[str] = None,
        is_read: Optional[bool] = None,
        include_dismissed: bool = False,
        page: int = 1,
        page_size: int = 50,
    ) -> NotificationListResponse:
        profile = await cls.get_candidate_profile(db, current_user.id)
        items, total, unread_count = await NotificationRepository.get_candidate_notifications(
            db=db,
            candidate_id=profile.id,
            search=search,
            category=category,
            is_read=is_read,
            include_dismissed=include_dismissed,
            page=page,
            page_size=page_size,
        )
        serialized_items = [NotificationItem.model_validate(n) for n in items]
        return NotificationListResponse(
            items=serialized_items,
            total=total,
            unread_count=unread_count,
        )

    @classmethod
    async def get_notification_by_id(
        cls,
        db: AsyncSession,
        current_user: User,
        notification_id: str,
    ) -> NotificationItem:
        profile = await cls.get_candidate_profile(db, current_user.id)
        notif = await NotificationRepository.get_by_id_and_candidate(
            db, notification_id=notification_id, candidate_id=profile.id
        )
        if not notif:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found.",
            )
        return NotificationItem.model_validate(notif)

    @classmethod
    async def get_unread_count(
        cls,
        db: AsyncSession,
        current_user: User,
    ) -> UnreadCountResponse:
        profile = await cls.get_candidate_profile(db, current_user.id)
        count = await NotificationRepository.count_unread(db, candidate_id=profile.id)
        return UnreadCountResponse(unread_count=count)

    @classmethod
    async def mark_as_read(
        cls,
        db: AsyncSession,
        current_user: User,
        notification_id: str,
    ) -> NotificationActionResponse:
        profile = await cls.get_candidate_profile(db, current_user.id)
        notif = await NotificationRepository.mark_as_read(
            db, notification_id=notification_id, candidate_id=profile.id
        )
        if not notif:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found.",
            )
        return NotificationActionResponse(
            status="success",
            message="Notification marked as read.",
            notification=NotificationItem.model_validate(notif),
        )

    @classmethod
    async def mark_multiple_as_read(
        cls,
        db: AsyncSession,
        current_user: User,
        payload: MarkNotificationsRequest,
    ) -> NotificationActionResponse:
        profile = await cls.get_candidate_profile(db, current_user.id)
        count = await NotificationRepository.mark_multiple_as_read(
            db,
            candidate_id=profile.id,
            notification_ids=payload.notification_ids,
        )
        return NotificationActionResponse(
            status="success",
            message="Notifications marked as read.",
            updated_count=count,
        )

    @classmethod
    async def dismiss(
        cls,
        db: AsyncSession,
        current_user: User,
        notification_id: str,
    ) -> NotificationActionResponse:
        profile = await cls.get_candidate_profile(db, current_user.id)
        notif = await NotificationRepository.dismiss(
            db, notification_id=notification_id, candidate_id=profile.id
        )
        if not notif:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found.",
            )
        return NotificationActionResponse(
            status="success",
            message="Notification dismissed.",
            notification=NotificationItem.model_validate(notif),
        )

    @classmethod
    async def dismiss_multiple(
        cls,
        db: AsyncSession,
        current_user: User,
        payload: DismissNotificationsRequest,
    ) -> NotificationActionResponse:
        profile = await cls.get_candidate_profile(db, current_user.id)
        if not payload.notification_ids:
            return NotificationActionResponse(
                status="success",
                message="No notifications specified.",
                updated_count=0,
            )
        count = await NotificationRepository.dismiss_multiple(
            db,
            candidate_id=profile.id,
            notification_ids=payload.notification_ids,
        )
        return NotificationActionResponse(
            status="success",
            message="Notifications dismissed.",
            updated_count=count,
        )

    @classmethod
    async def delete_notification(
        cls,
        db: AsyncSession,
        current_user: User,
        notification_id: str,
    ) -> NotificationDeleteResponse:
        """
        Permanently delete a single notification.
        Enforces candidate authentication and resource ownership.
        """
        profile = await cls.get_candidate_profile(db, current_user.id)
        deleted = await NotificationRepository.delete_notification(
            db=db,
            notification_id=str(notification_id).strip(),
            candidate_id=profile.id,
        )
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found.",
            )
        return NotificationDeleteResponse(message="Notification deleted successfully.")

    @classmethod
    async def delete_notifications_bulk(
        cls,
        db: AsyncSession,
        current_user: User,
        payload: BulkNotificationDeleteRequest,
    ) -> BulkNotificationDeleteResponse:
        """
        Permanently delete multiple notifications in one operation.
        Verifies all IDs belong to the authenticated candidate.
        If foreign or non-existent IDs are included, safely rejects.
        """
        profile = await cls.get_candidate_profile(db, current_user.id)
        requested_ids = [str(i).strip() for i in payload.notification_ids if str(i).strip()]

        if not requested_ids:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="No notification IDs provided.",
            )

        owned_ids = await NotificationRepository.get_owned_notification_ids(
            db=db,
            notification_ids=requested_ids,
            candidate_id=profile.id,
        )

        if not owned_ids:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No matching notifications found to delete.",
            )

        # Enforce that all requested IDs belong to the candidate
        if len(owned_ids) != len(requested_ids):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="One or more notifications not found.",
            )

        deleted_count = await NotificationRepository.delete_notifications(
            db=db,
            notification_ids=owned_ids,
            candidate_id=profile.id,
        )

        return BulkNotificationDeleteResponse(
            message="Notifications deleted successfully.",
            deleted_count=deleted_count,
        )


    @staticmethod
    async def create_notification(
        db: AsyncSession,
        candidate_id: str,
        category: str,
        title: str,
        message: str,
        link: Optional[str] = None,
        application_id: Optional[str] = None,
        interview_id: Optional[str] = None,
        job_id: Optional[str] = None,
        job_mela_id: Optional[str] = None,
    ) -> Notification:
        """
        Reusable notification creator for backend business events.
        """
        return await NotificationRepository.create_notification(
            db=db,
            candidate_id=candidate_id,
            category=category,
            title=title,
            message=message,
            link=link,
            application_id=application_id,
            interview_id=interview_id,
            job_id=job_id,
            job_mela_id=job_mela_id,
        )
