import uuid
from typing import List, Optional, Tuple
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_, or_

from app.models.notification import Notification


class NotificationRepository:
    """
    Async repository layer for Candidate Notifications.
    Direct MySQL persistence via AsyncSession and asyncmy.
    All operations strictly scoped to the authenticated candidate.
    """

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
        notif = Notification(
            id=str(uuid.uuid4()),
            candidate_id=candidate_id,
            category=category.lower().strip(),
            title=title.strip(),
            message=message.strip(),
            link=link,
            application_id=application_id,
            interview_id=interview_id,
            job_id=job_id,
            job_mela_id=job_mela_id,
            is_read=False,
            is_dismissed=False,
            created_at=datetime.now(timezone.utc),
        )
        db.add(notif)
        await db.commit()
        await db.refresh(notif)
        return notif

    @staticmethod
    async def get_candidate_notifications(
        db: AsyncSession,
        candidate_id: str,
        search: Optional[str] = None,
        category: Optional[str] = None,
        is_read: Optional[bool] = None,
        include_dismissed: bool = False,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[List[Notification], int, int]:
        """
        Fetch filtered notifications for candidate along with total and unread counts.
        """
        # Base filter: candidate ownership
        conditions = [Notification.candidate_id == candidate_id]

        if not include_dismissed:
            conditions.append(Notification.is_dismissed == False)

        if category and category.upper() != "ALL":
            # Normalize shortlist/shortlisted, etc.
            cat_clean = category.lower().strip()
            if cat_clean == "shortlist":
                cat_clean = "shortlisted"
            conditions.append(Notification.category.ilike(f"%{cat_clean}%"))

        if is_read is not None:
            conditions.append(Notification.is_read == is_read)

        if search and search.strip():
            term = f"%{search.strip()}%"
            conditions.append(
                or_(
                    Notification.title.ilike(term),
                    Notification.message.ilike(term),
                )
            )

        # Count total matching
        count_stmt = select(func.count(Notification.id)).where(and_(*conditions))
        total_result = await db.execute(count_stmt)
        total = total_result.scalar_one()

        # Count overall active unread for candidate (not dismissed)
        unread_stmt = select(func.count(Notification.id)).where(
            and_(
                Notification.candidate_id == candidate_id,
                Notification.is_read == False,
                Notification.is_dismissed == False,
            )
        )
        unread_result = await db.execute(unread_stmt)
        unread_count = unread_result.scalar_one()

        # Fetch paginated items
        stmt = (
            select(Notification)
            .where(and_(*conditions))
            .order_by(Notification.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await db.execute(stmt)
        items = list(result.scalars().all())

        return items, total, unread_count

    @staticmethod
    async def get_by_id_and_candidate(
        db: AsyncSession,
        notification_id: str,
        candidate_id: str,
    ) -> Optional[Notification]:
        stmt = select(Notification).where(
            and_(
                Notification.id == notification_id,
                Notification.candidate_id == candidate_id,
            )
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def count_unread(
        db: AsyncSession,
        candidate_id: str,
    ) -> int:
        stmt = select(func.count(Notification.id)).where(
            and_(
                Notification.candidate_id == candidate_id,
                Notification.is_read == False,
                Notification.is_dismissed == False,
            )
        )
        result = await db.execute(stmt)
        return result.scalar_one()

    @staticmethod
    async def mark_as_read(
        db: AsyncSession,
        notification_id: str,
        candidate_id: str,
    ) -> Optional[Notification]:
        notif = await NotificationRepository.get_by_id_and_candidate(db, notification_id, candidate_id)
        if not notif:
            return None
        if not notif.is_read:
            notif.is_read = True
            notif.read_at = datetime.now(timezone.utc)
            await db.commit()
            await db.refresh(notif)
        return notif

    @staticmethod
    async def mark_multiple_as_read(
        db: AsyncSession,
        candidate_id: str,
        notification_ids: Optional[List[str]] = None,
    ) -> int:
        conditions = [
            Notification.candidate_id == candidate_id,
            Notification.is_read == False,
        ]
        if notification_ids:
            conditions.append(Notification.id.in_(notification_ids))

        now = datetime.now(timezone.utc)
        stmt = (
            update(Notification)
            .where(and_(*conditions))
            .values(is_read=True, read_at=now)
        )
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount

    @staticmethod
    async def dismiss(
        db: AsyncSession,
        notification_id: str,
        candidate_id: str,
    ) -> Optional[Notification]:
        notif = await NotificationRepository.get_by_id_and_candidate(db, notification_id, candidate_id)
        if not notif:
            return None
        if not notif.is_dismissed:
            notif.is_dismissed = True
            notif.dismissed_at = datetime.now(timezone.utc)
            await db.commit()
            await db.refresh(notif)
        return notif

    @staticmethod
    async def dismiss_multiple(
        db: AsyncSession,
        candidate_id: str,
        notification_ids: List[str],
    ) -> int:
        if not notification_ids:
            return 0
        now = datetime.now(timezone.utc)
        stmt = (
            update(Notification)
            .where(
                and_(
                    Notification.candidate_id == candidate_id,
                    Notification.id.in_(notification_ids),
                    Notification.is_dismissed == False,
                )
            )
            .values(is_dismissed=True, dismissed_at=now)
        )
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount

    @staticmethod
    async def delete_notification(
        db: AsyncSession,
        notification_id: str,
        candidate_id: str,
    ) -> bool:
        """
        Permanently delete a single notification from MySQL.
        Strictly enforces candidate ownership.
        Returns True if deleted, False if not found or unauthorized.
        """
        stmt = (
            delete(Notification)
            .where(
                and_(
                    Notification.id == notification_id,
                    Notification.candidate_id == candidate_id,
                )
            )
        )
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount > 0

    @staticmethod
    async def get_owned_notification_ids(
        db: AsyncSession,
        notification_ids: List[str],
        candidate_id: str,
    ) -> List[str]:
        """Fetch IDs from the requested list that actually belong to the candidate."""
        if not notification_ids:
            return []
        stmt = select(Notification.id).where(
            and_(
                Notification.id.in_(notification_ids),
                Notification.candidate_id == candidate_id,
            )
        )
        res = await db.execute(stmt)
        return [row[0] for row in res.all()]

    @staticmethod
    async def delete_notifications(
        db: AsyncSession,
        notification_ids: List[str],
        candidate_id: str,
    ) -> int:
        """
        Permanently delete multiple notifications belonging to candidate in one query.
        Returns count of deleted rows.
        """
        if not notification_ids:
            return 0
        stmt = (
            delete(Notification)
            .where(
                and_(
                    Notification.id.in_(notification_ids),
                    Notification.candidate_id == candidate_id,
                )
            )
        )
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount

