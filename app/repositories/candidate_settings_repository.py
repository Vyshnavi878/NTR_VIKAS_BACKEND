import uuid
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.candidate_settings import CandidateSettings
from app.schemas.candidate_settings import NotificationSettingsUpdate, PrivacySettingsUpdate


class CandidateSettingsRepository:
    """
    Async repository for candidate settings & preferences.
    Direct MySQL persistence via AsyncSession and asyncmy.
    """

    @staticmethod
    async def get_by_candidate_id(
        db: AsyncSession,
        candidate_id: str,
    ) -> Optional[CandidateSettings]:
        stmt = select(CandidateSettings).where(CandidateSettings.candidate_id == candidate_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @classmethod
    async def get_or_create_by_candidate_id(
        cls,
        db: AsyncSession,
        candidate_id: str,
    ) -> CandidateSettings:
        settings = await cls.get_by_candidate_id(db, candidate_id)
        if not settings:
            settings = CandidateSettings(
                id=str(uuid.uuid4()),
                candidate_id=candidate_id,
                email_job_application_alerts=True,
                sms_whatsapp_notifications=True,
                upcoming_interview_reminders=True,
                weekly_job_recommendation_digest=False,
                visible_in_recruiter_talent_search=True,
                direct_recruiter_messages=True,
            )
            db.add(settings)
            await db.commit()
            await db.refresh(settings)
        return settings

    @classmethod
    async def update_notifications(
        cls,
        db: AsyncSession,
        candidate_id: str,
        payload: NotificationSettingsUpdate,
    ) -> CandidateSettings:
        settings = await cls.get_or_create_by_candidate_id(db, candidate_id)
        update_data = payload.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if value is not None:
                setattr(settings, key, value)
        await db.commit()
        await db.refresh(settings)
        return settings

    @classmethod
    async def update_privacy(
        cls,
        db: AsyncSession,
        candidate_id: str,
        payload: PrivacySettingsUpdate,
    ) -> CandidateSettings:
        settings = await cls.get_or_create_by_candidate_id(db, candidate_id)
        update_data = payload.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if value is not None:
                setattr(settings, key, value)
        await db.commit()
        await db.refresh(settings)
        return settings
