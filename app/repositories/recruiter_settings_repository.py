import hashlib
from datetime import datetime, timezone
from typing import Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from app.models.user import User
from app.models.recruiter import RecruiterProfile
from app.models.company_team import (
    CompanyMember,
    CompanyInvitation,
    RecruiterNotificationPreference,
)


class RecruiterSettingsRepository:
    """Async repository layer for Recruiter Settings & Team Management."""

    @staticmethod
    def hash_token(raw_token: str) -> str:
        """Hash token using SHA-256 for secure storage."""
        return hashlib.sha256(raw_token.strip().encode("utf-8")).hexdigest()

    @classmethod
    async def get_company_and_role_for_user(
        cls, db: AsyncSession, user_id: str
    ) -> Tuple[Optional[RecruiterProfile], Optional[str]]:
        """
        Resolve the company profile and user's role:
        1. If user is direct creator of RecruiterProfile -> COMPANY_OWNER.
        2. Else if user is member in CompanyMember -> member.role.
        """
        # 1. Check if user is primary owner of RecruiterProfile
        stmt = select(RecruiterProfile).where(RecruiterProfile.user_id == user_id)
        res = await db.execute(stmt)
        profile = res.scalar_one_or_none()
        if profile:
            # Ensure owner has a CompanyMember entry
            await cls.ensure_owner_company_member(db, company_id=profile.id, user_id=user_id)
            return profile, "COMPANY_OWNER"

        # 2. Check if user is in CompanyMember
        m_stmt = (
            select(CompanyMember)
            .where(
                and_(
                    CompanyMember.user_id == user_id,
                    CompanyMember.status != "DEACTIVATED",
                )
            )
        )
        m_res = await db.execute(m_stmt)
        member = m_res.scalar_one_or_none()
        if member:
            c_stmt = select(RecruiterProfile).where(RecruiterProfile.id == member.company_id)
            c_res = await db.execute(c_stmt)
            company = c_res.scalar_one_or_none()
            return company, member.role

        return None, None

    @classmethod
    async def ensure_owner_company_member(
        cls, db: AsyncSession, company_id: str, user_id: str
    ) -> CompanyMember:
        """Ensure the company owner has an active CompanyMember record."""
        stmt = select(CompanyMember).where(
            and_(
                CompanyMember.company_id == company_id,
                CompanyMember.user_id == user_id,
            )
        )
        res = await db.execute(stmt)
        existing = res.scalar_one_or_none()
        if existing:
            return existing

        owner_member = CompanyMember(
            company_id=company_id,
            user_id=user_id,
            role="COMPANY_OWNER",
            status="ACTIVE",
            joined_at=datetime.now(timezone.utc),
        )
        db.add(owner_member)
        await db.commit()
        await db.refresh(owner_member)
        return owner_member

    @classmethod
    async def get_team_members(
        cls, db: AsyncSession, company_id: str
    ) -> List[CompanyMember]:
        """Fetch all CompanyMember records with user details for a given company."""
        stmt = (
            select(CompanyMember)
            .where(CompanyMember.company_id == company_id)
            .options(selectinload(CompanyMember.user))
            .order_by(CompanyMember.created_at.asc())
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())

    @classmethod
    async def get_pending_invitations(
        cls, db: AsyncSession, company_id: str
    ) -> List[CompanyInvitation]:
        """Fetch all pending (unaccepted) invitations for a company."""
        now = datetime.now(timezone.utc)
        stmt = (
            select(CompanyInvitation)
            .where(
                and_(
                    CompanyInvitation.company_id == company_id,
                    CompanyInvitation.accepted_at.is_(None),
                )
            )
            .order_by(CompanyInvitation.created_at.desc())
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())

    @classmethod
    async def get_active_member_by_email(
        cls, db: AsyncSession, company_id: str, email: str
    ) -> Optional[CompanyMember]:
        """Check if an email already belongs to an active member in this company."""
        clean_email = email.lower().strip()
        stmt = (
            select(CompanyMember)
            .join(User, CompanyMember.user_id == User.id)
            .where(
                and_(
                    CompanyMember.company_id == company_id,
                    User.email == clean_email,
                    CompanyMember.status == "ACTIVE",
                )
            )
        )
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    @classmethod
    async def get_invitation_by_id(
        cls, db: AsyncSession, invitation_id: str
    ) -> Optional[CompanyInvitation]:
        """Fetch invitation by ID."""
        stmt = select(CompanyInvitation).where(CompanyInvitation.id == invitation_id)
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    @classmethod
    async def get_invitation_by_token_hash(
        cls, db: AsyncSession, token_hash: str
    ) -> Optional[CompanyInvitation]:
        """Fetch invitation by token hash with company relationship loaded."""
        stmt = (
            select(CompanyInvitation)
            .where(CompanyInvitation.token_hash == token_hash)
            .options(selectinload(CompanyInvitation.company))
        )
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    @classmethod
    async def get_member_by_id(
        cls, db: AsyncSession, member_id: str
    ) -> Optional[CompanyMember]:
        """Fetch company member by ID."""
        stmt = (
            select(CompanyMember)
            .where(CompanyMember.id == member_id)
            .options(selectinload(CompanyMember.user))
        )
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    @classmethod
    async def get_notification_preferences(
        cls, db: AsyncSession, user_id: str
    ) -> RecruiterNotificationPreference:
        """Fetch or initialize notification preferences for a recruiter user."""
        stmt = select(RecruiterNotificationPreference).where(
            RecruiterNotificationPreference.user_id == user_id
        )
        res = await db.execute(stmt)
        pref = res.scalar_one_or_none()
        if not pref:
            pref = RecruiterNotificationPreference(
                user_id=user_id,
                instant_new_applicant_alerts=True,
                interview_confirmation_reminders=True,
                weekly_hiring_digest=True,
                job_mela_alerts=True,
            )
            db.add(pref)
            await db.commit()
            await db.refresh(pref)
        return pref
