from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_database, get_current_candidate
from app.models.user import User
from app.schemas.notification import (
    NotificationItem,
    NotificationListResponse,
    UnreadCountResponse,
    MarkNotificationsRequest,
    DismissNotificationsRequest,
    NotificationActionResponse,
)
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/candidate/notifications", tags=["Candidate Notifications"])


@router.get(
    "",
    response_model=NotificationListResponse,
    summary="Get candidate notifications",
    description="Retrieve all notifications for the authenticated candidate with search, category, and unread filters.",
)
async def get_notifications(
    search: Optional[str] = Query(None, description="Search query matching notification title or message"),
    category: Optional[str] = Query(None, description="Filter by category (shortlisted, interview, application, etc.)"),
    is_read: Optional[bool] = Query(None, description="Filter by read status (true for read, false for unread)"),
    include_dismissed: bool = Query(False, description="Whether to include dismissed notifications"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_database),
) -> NotificationListResponse:
    return await NotificationService.get_notifications(
        db=db,
        current_user=current_user,
        search=search,
        category=category,
        is_read=is_read,
        include_dismissed=include_dismissed,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/unread-count",
    response_model=UnreadCountResponse,
    summary="Get candidate unread notification count",
    description="Retrieve count of active unread notifications for the header bell badge.",
)
async def get_unread_count(
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_database),
) -> UnreadCountResponse:
    return await NotificationService.get_unread_count(db=db, current_user=current_user)


@router.post(
    "/mark-read",
    response_model=NotificationActionResponse,
    summary="Mark multiple notifications as read",
    description="Mark multiple notifications or all unread notifications as read.",
)
async def mark_multiple_read(
    payload: MarkNotificationsRequest,
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_database),
) -> NotificationActionResponse:
    return await NotificationService.mark_multiple_as_read(
        db=db, current_user=current_user, payload=payload
    )


@router.post(
    "/dismiss",
    response_model=NotificationActionResponse,
    summary="Dismiss multiple notifications",
    description="Bulk dismiss specified notification IDs for the authenticated candidate.",
)
async def dismiss_multiple(
    payload: DismissNotificationsRequest,
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_database),
) -> NotificationActionResponse:
    return await NotificationService.dismiss_multiple(
        db=db, current_user=current_user, payload=payload
    )


@router.get(
    "/{notification_id}",
    response_model=NotificationItem,
    summary="Get single notification",
    description="Retrieve details of a specific notification owned by the candidate.",
)
async def get_notification(
    notification_id: str,
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_database),
) -> NotificationItem:
    return await NotificationService.get_notification_by_id(
        db=db, current_user=current_user, notification_id=notification_id
    )


@router.patch(
    "/{notification_id}/read",
    response_model=NotificationActionResponse,
    summary="Mark notification as read",
    description="Mark a specific notification as read.",
)
async def mark_read(
    notification_id: str,
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_database),
) -> NotificationActionResponse:
    return await NotificationService.mark_as_read(
        db=db, current_user=current_user, notification_id=notification_id
    )


@router.patch(
    "/{notification_id}/dismiss",
    response_model=NotificationActionResponse,
    summary="Dismiss notification",
    description="Soft-dismiss a specific notification so it no longer appears in normal lists.",
)
async def dismiss(
    notification_id: str,
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_database),
) -> NotificationActionResponse:
    return await NotificationService.dismiss(
        db=db, current_user=current_user, notification_id=notification_id
    )
