import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple, Dict, Any
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.core.config import settings
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
)
from app.models.user import User
from app.models.recruiter import RecruiterProfile
from app.models.company_team import (
    CompanyMember,
    CompanyInvitation,
    RecruiterNotificationPreference,
)
from app.repositories.recruiter_settings_repository import RecruiterSettingsRepository
from app.repositories.recruiter_repository import RecruiterRepository
from app.repositories.user_repository import UserRepository
from app.services.email_service import EmailService
from app.schemas.recruiter_settings import (
    RecruiterProfileSettingsResponse,
    RecruiterProfileSettingsUpdate,
    TeamMemberResponse,
    TeamInvitationCreate,
    TeamInvitationResponse,
    ValidateInvitationResponse,
    AcceptInvitationRequest,
    AcceptInvitationResponse,
    RecruiterNotificationPreferencesResponse,
    RecruiterNotificationPreferencesUpdate,
    RecruiterChangePasswordRequest,
)

logger = logging.getLogger(__name__)

def is_past_datetime(dt: Optional[datetime]) -> bool:
    if not dt:
        return False
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt < now

# Roles mapping for clean human-readable displays
ROLE_DISPLAY_MAP = {
    "COMPANY_OWNER": "Company Owner",
    "TECHNICAL_RECRUITER": "Technical Recruiter",
    "HIRING_MANAGER": "Hiring Manager",
    "INTERVIEW_PANELIST": "Interview Panelist",
}


class RecruiterSettingsService:
    """Business service layer for Recruiter Settings & Hiring Team Collaboration."""

    @classmethod
    async def get_profile(
        cls, db: AsyncSession, current_recruiter: User
    ) -> RecruiterProfileSettingsResponse:
        """Fetch authenticated recruiter's personal profile and company metadata."""
        company, role = await RecruiterSettingsRepository.get_company_and_role_for_user(
            db, current_recruiter.id
        )
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recruiter company workspace not found for authenticated account.",
            )

        # Direct profile if user is company creator
        direct_profile = await RecruiterRepository.get_profile_by_user_id(db, current_recruiter.id)
        if direct_profile and direct_profile.user_id == current_recruiter.id:
            full_name = direct_profile.recruiter_name
            designation = direct_profile.designation
            phone = direct_profile.mobile_phone or current_recruiter.phone
        else:
            # Invited member: resolve membership
            full_name = getattr(current_recruiter, "name", None) or "Hiring Team Member"
            # Try to fetch invitation or member record
            m_stmt = select(CompanyMember).where(
                and_(
                    CompanyMember.user_id == current_recruiter.id,
                    CompanyMember.company_id == company.id,
                )
            )
            m_res = await db.execute(m_stmt)
            member = m_res.scalar_one_or_none()
            designation = ROLE_DISPLAY_MAP.get(role, role)
            phone = current_recruiter.phone

        email = current_recruiter.email

        return RecruiterProfileSettingsResponse(
            id=current_recruiter.id,
            full_name=full_name,
            name=full_name,
            designation=designation,
            work_email=email,
            email=email,
            phone=phone,
            mobile_phone=phone,
            company_id=company.id,
            company_name=company.company_name,
            companyName=company.company_name,
            role=ROLE_DISPLAY_MAP.get(role, role),
            status=company.status,
        )

    @classmethod
    async def update_profile(
        cls,
        db: AsyncSession,
        current_recruiter: User,
        payload: RecruiterProfileSettingsUpdate,
    ) -> RecruiterProfileSettingsResponse:
        """
        Update authenticated recruiter's personal profile.
        Allows full_name, designation, phone. Work email is read-only.
        """
        company, role = await RecruiterSettingsRepository.get_company_and_role_for_user(
            db, current_recruiter.id
        )
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recruiter company workspace not found for authenticated account.",
            )

        new_name = (payload.full_name or payload.name or "").strip()
        new_designation = (payload.designation or "").strip()
        new_phone = (payload.phone or payload.mobile_phone or "").strip()

        # Update RecruiterProfile if user is company creator
        direct_profile = await RecruiterRepository.get_profile_by_user_id(db, current_recruiter.id)
        if direct_profile and direct_profile.user_id == current_recruiter.id:
            if new_name:
                direct_profile.recruiter_name = new_name
            if new_designation:
                direct_profile.designation = new_designation
            if new_phone:
                direct_profile.mobile_phone = new_phone
                current_recruiter.phone = new_phone
            await db.commit()
            await db.refresh(direct_profile)
        else:
            if new_phone:
                current_recruiter.phone = new_phone
            await db.commit()

        return await cls.get_profile(db, current_recruiter)

    @classmethod
    async def get_team(
        cls, db: AsyncSession, current_recruiter: User
    ) -> List[TeamMemberResponse]:
        """Fetch all hiring team members and pending invitations for the company."""
        company, _ = await RecruiterSettingsRepository.get_company_and_role_for_user(
            db, current_recruiter.id
        )
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recruiter company workspace not found.",
            )

        # 1. Fetch active/deactivated CompanyMembers
        members = await RecruiterSettingsRepository.get_team_members(db, company.id)
        result: List[TeamMemberResponse] = []

        seen_emails = set()

        for m in members:
            u = m.user
            email = u.email if u else "unknown"
            seen_emails.add(email.lower().strip())

            # Determine name: if owner and direct profile exists, use recruiter_name
            name = "Team Member"
            if company.user_id == m.user_id:
                name = company.recruiter_name
            elif u:
                name = getattr(u, "name", None) or u.email.split("@")[0].title()

            joined_str = m.joined_at.strftime("%Y-%m-%d") if m.joined_at else (m.created_at.strftime("%Y-%m-%d") if m.created_at else None)

            result.append(
                TeamMemberResponse(
                    id=m.id,
                    user_id=m.user_id,
                    full_name=name,
                    name=name,
                    work_email=email,
                    email=email,
                    role=ROLE_DISPLAY_MAP.get(m.role, m.role),
                    status=m.status,
                    joined_at=joined_str,
                )
            )

        # 2. Fetch pending CompanyInvitations
        invitations = await RecruiterSettingsRepository.get_pending_invitations(db, company.id)
        now = datetime.now(timezone.utc)
        for inv in invitations:
            if inv.email.lower().strip() in seen_emails:
                continue
            if inv.expires_at and is_past_datetime(inv.expires_at):
                continue

            inv_created = inv.created_at.strftime("%Y-%m-%d") if inv.created_at else None

            result.append(
                TeamMemberResponse(
                    id=inv.id,
                    full_name=inv.full_name,
                    name=inv.full_name,
                    work_email=inv.email,
                    email=inv.email,
                    role=ROLE_DISPLAY_MAP.get(inv.role, inv.role),
                    status="INVITED",
                    joined_at=inv_created,
                )
            )

        return result

    @classmethod
    async def invite_team_member(
        cls,
        db: AsyncSession,
        current_recruiter: User,
        payload: TeamInvitationCreate,
    ) -> TeamInvitationResponse:
        """
        Invite a new team member to collaborate on company hiring.
        Enforces COMPANY_OWNER authorization and checks for duplicate active membership.
        """
        company, role = await RecruiterSettingsRepository.get_company_and_role_for_user(
            db, current_recruiter.id
        )
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recruiter company workspace not found.",
            )

        # Enforce permission: only COMPANY_OWNER or primary profile owner can invite
        is_owner = (role == "COMPANY_OWNER") or (company.user_id == current_recruiter.id)
        if not is_owner:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied. Only the Company Owner can invite hiring team members.",
            )

        email = payload.email.lower().strip()
        name = (payload.full_name or payload.name or "").strip()
        if not name:
            name = email.split("@")[0].title()

        # Check if already an active member of this company
        existing_active = await RecruiterSettingsRepository.get_active_member_by_email(
            db, company.id, email
        )
        if existing_active:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This email address is already an active member of your hiring team.",
            )

        # Generate cryptographically secure one-time token and hash
        raw_token = secrets.token_urlsafe(32)
        token_hash = RecruiterSettingsRepository.hash_token(raw_token)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=48)

        # Check if there is an existing pending invitation for this email; if so, update it
        stmt = select(CompanyInvitation).where(
            and_(
                CompanyInvitation.company_id == company.id,
                CompanyInvitation.email == email,
                CompanyInvitation.accepted_at.is_(None),
            )
        )
        res = await db.execute(stmt)
        invitation = res.scalar_one_or_none()

        if invitation:
            invitation.full_name = name
            invitation.role = payload.role
            invitation.token_hash = token_hash
            invitation.invited_by = current_recruiter.id
            invitation.expires_at = expires_at
        else:
            invitation = CompanyInvitation(
                company_id=company.id,
                email=email,
                full_name=name,
                role=payload.role,
                token_hash=token_hash,
                invited_by=current_recruiter.id,
                expires_at=expires_at,
            )
            db.add(invitation)

        await db.commit()
        await db.refresh(invitation)

        # Construct invitation accept URL
        invite_url = f"{settings.FRONTEND_URL}/accept-invitation/{raw_token}"

        # Send official invitation email
        inviter_name = company.recruiter_name if company.user_id == current_recruiter.id else "Hiring Team Lead"
        EmailService.send_team_invitation_email(
            to_email=email,
            full_name=name,
            company_name=company.company_name,
            role=ROLE_DISPLAY_MAP.get(payload.role, payload.role),
            inviter_name=inviter_name,
            invite_url=invite_url,
        )

        return TeamInvitationResponse(
            id=invitation.id,
            email=email,
            full_name=name,
            name=name,
            role=ROLE_DISPLAY_MAP.get(payload.role, payload.role),
            status="INVITED",
            invitation_token=raw_token,
            invitationToken=raw_token,
            invite_url=invite_url,
            expires_at=expires_at.strftime("%Y-%m-%d %H:%M:%S UTC"),
            message=f"Invitation sent successfully to {email}.",
        )

    @classmethod
    async def resend_invitation(
        cls,
        db: AsyncSession,
        current_recruiter: User,
        invitation_id: str,
    ) -> TeamInvitationResponse:
        """Resend an existing team invitation with a newly generated secure token."""
        company, role = await RecruiterSettingsRepository.get_company_and_role_for_user(
            db, current_recruiter.id
        )
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recruiter company workspace not found.",
            )

        is_owner = (role == "COMPANY_OWNER") or (company.user_id == current_recruiter.id)
        if not is_owner:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied. Only the Company Owner can resend invitations.",
            )

        invitation = await RecruiterSettingsRepository.get_invitation_by_id(db, invitation_id)
        if not invitation or invitation.company_id != company.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Team invitation not found.",
            )

        if invitation.accepted_at:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This invitation has already been accepted.",
            )

        raw_token = secrets.token_urlsafe(32)
        token_hash = RecruiterSettingsRepository.hash_token(raw_token)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=48)

        invitation.token_hash = token_hash
        invitation.expires_at = expires_at
        await db.commit()
        await db.refresh(invitation)

        invite_url = f"{settings.FRONTEND_URL}/accept-invitation/{raw_token}"
        inviter_name = company.recruiter_name if company.user_id == current_recruiter.id else "Hiring Team Lead"
        EmailService.send_team_invitation_email(
            to_email=invitation.email,
            full_name=invitation.full_name,
            company_name=company.company_name,
            role=ROLE_DISPLAY_MAP.get(invitation.role, invitation.role),
            inviter_name=inviter_name,
            invite_url=invite_url,
        )

        return TeamInvitationResponse(
            id=invitation.id,
            email=invitation.email,
            full_name=invitation.full_name,
            name=invitation.full_name,
            role=ROLE_DISPLAY_MAP.get(invitation.role, invitation.role),
            status="INVITED",
            invitation_token=raw_token,
            invitationToken=raw_token,
            invite_url=invite_url,
            expires_at=expires_at.strftime("%Y-%m-%d %H:%M:%S UTC"),
            message=f"Invitation resent successfully to {invitation.email}.",
        )

    @classmethod
    async def remove_or_deactivate_member(
        cls,
        db: AsyncSession,
        current_recruiter: User,
        member_id: str,
    ) -> Dict[str, Any]:
        """
        Deactivate team member or cancel pending invitation.
        Preserves historical jobs, interviews, applications, and activity records.
        """
        company, role = await RecruiterSettingsRepository.get_company_and_role_for_user(
            db, current_recruiter.id
        )
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recruiter company workspace not found.",
            )

        is_owner = (role == "COMPANY_OWNER") or (company.user_id == current_recruiter.id)
        if not is_owner:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied. Only Company Owner can manage team members.",
            )

        # 1. Check if ID matches a pending invitation
        inv = await RecruiterSettingsRepository.get_invitation_by_id(db, member_id)
        if inv and inv.company_id == company.id:
            await db.delete(inv)
            await db.commit()
            return {"status": "success", "message": f"Invitation for {inv.email} cancelled successfully."}

        # 2. Check if ID matches a CompanyMember
        member = await RecruiterSettingsRepository.get_member_by_id(db, member_id)
        if member and member.company_id == company.id:
            if member.user_id == company.user_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot deactivate the primary Company Owner account.",
                )
            # Deactivate membership (non-destructive)
            member.status = "DEACTIVATED"
            await db.commit()
            return {"status": "success", "message": "Team member has been deactivated from company workspace."}

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team member or invitation not found in your company.",
        )

    @classmethod
    async def validate_invitation_token(
        cls, db: AsyncSession, raw_token: str
    ) -> ValidateInvitationResponse:
        """Validate an invitation token for the invitation accept page."""
        if not raw_token or not raw_token.strip():
            return ValidateInvitationResponse(
                valid=False,
                message="Missing invitation token.",
            )

        token_hash = RecruiterSettingsRepository.hash_token(raw_token)
        invitation = await RecruiterSettingsRepository.get_invitation_by_token_hash(db, token_hash)
        if not invitation:
            return ValidateInvitationResponse(
                valid=False,
                message="This invitation token is invalid or does not exist.",
            )

        if invitation.accepted_at:
            return ValidateInvitationResponse(
                valid=False,
                email=invitation.email,
                full_name=invitation.full_name,
                name=invitation.full_name,
                role=ROLE_DISPLAY_MAP.get(invitation.role, invitation.role),
                message="This invitation has already been accepted.",
            )

        if invitation.expires_at and is_past_datetime(invitation.expires_at):
            return ValidateInvitationResponse(
                valid=False,
                email=invitation.email,
                full_name=invitation.full_name,
                name=invitation.full_name,
                role=ROLE_DISPLAY_MAP.get(invitation.role, invitation.role),
                message="This invitation has expired. Please ask your administrator to send a new invitation.",
            )

        company = invitation.company
        c_name = company.company_name if company else "Company"
        c_logo = company.company_logo_path if company else None

        return ValidateInvitationResponse(
            valid=True,
            email=invitation.email,
            full_name=invitation.full_name,
            name=invitation.full_name,
            role=ROLE_DISPLAY_MAP.get(invitation.role, invitation.role),
            company_id=invitation.company_id,
            company_name=c_name,
            companyName=c_name,
            company_logo=c_logo,
            expires_at=invitation.expires_at.strftime("%Y-%m-%d %H:%M:%S UTC"),
            message="Invitation is valid.",
        )

    @classmethod
    async def accept_invitation(
        cls,
        db: AsyncSession,
        payload: AcceptInvitationRequest,
    ) -> AcceptInvitationResponse:
        """
        Accept invitation, set up password, and create/link recruiter user to the existing company.
        DOES NOT create a duplicate company.
        """
        token_hash = RecruiterSettingsRepository.hash_token(payload.token)
        invitation = await RecruiterSettingsRepository.get_invitation_by_token_hash(db, token_hash)
        if not invitation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invalid or expired invitation token.",
            )

        if invitation.accepted_at:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This invitation has already been accepted.",
            )

        if invitation.expires_at and is_past_datetime(invitation.expires_at):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This invitation link has expired. Please request a new invitation.",
            )

        confirm_pwd = payload.confirm_password or payload.confirmPassword
        if confirm_pwd and payload.password != confirm_pwd:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Password and confirm password do not match.",
            )

        if len(payload.password) < 6:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Password must be at least 6 characters long.",
            )

        clean_email = invitation.email.lower().strip()
        now = datetime.now(timezone.utc)

        # Check if user already exists
        user = await UserRepository.get_by_email(db, clean_email)
        if not user:
            # Create new user account for invited recruiter
            user = User(
                email=clean_email,
                hashed_password=hash_password(payload.password),
                role="RECRUITER",
                is_active=True,
                is_verified=True,
            )
            db.add(user)
            await db.flush()
        else:
            # Update password
            user.hashed_password = hash_password(payload.password)
            user.role = "RECRUITER"
            user.is_active = True
            user.is_verified = True

        # Create or update CompanyMember record
        m_stmt = select(CompanyMember).where(
            and_(
                CompanyMember.company_id == invitation.company_id,
                CompanyMember.user_id == user.id,
            )
        )
        m_res = await db.execute(m_stmt)
        member = m_res.scalar_one_or_none()
        if member:
            member.role = invitation.role
            member.status = "ACTIVE"
            member.joined_at = now
        else:
            member = CompanyMember(
                company_id=invitation.company_id,
                user_id=user.id,
                role=invitation.role,
                status="ACTIVE",
                invited_by=invitation.invited_by,
                joined_at=now,
            )
            db.add(member)

        # Mark invitation as accepted
        invitation.accepted_at = now

        # Ensure default notification preferences exist
        await RecruiterSettingsRepository.get_notification_preferences(db, user.id)

        await db.commit()
        await db.refresh(user)

        # Generate authentication tokens
        access_token = create_access_token(
            subject=user.id,
            role="RECRUITER",
            email=user.email,
        )
        refresh_token = create_refresh_token(subject=user.id, role="RECRUITER")

        company = invitation.company
        c_name = company.company_name if company else "Company"

        user_summary = {
            "id": user.id,
            "email": user.email,
            "name": invitation.full_name,
            "role": "RECRUITER",
            "team_role": invitation.role,
            "company_id": invitation.company_id,
            "company_name": c_name,
        }

        return AcceptInvitationResponse(
            status="success",
            message=f"Welcome to {c_name}! Your account is now active.",
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            user=user_summary,
        )

    @classmethod
    async def get_notification_preferences(
        cls, db: AsyncSession, current_recruiter: User
    ) -> RecruiterNotificationPreferencesResponse:
        """Fetch notification preferences for authenticated recruiter."""
        prefs = await RecruiterSettingsRepository.get_notification_preferences(
            db, current_recruiter.id
        )
        updated_str = prefs.updated_at.strftime("%Y-%m-%d %H:%M:%S") if prefs.updated_at else None

        return RecruiterNotificationPreferencesResponse(
            instant_new_applicant_alerts=prefs.instant_new_applicant_alerts,
            interview_confirmation_reminders=prefs.interview_confirmation_reminders,
            weekly_hiring_digest=prefs.weekly_hiring_digest,
            job_mela_alerts=prefs.job_mela_alerts,
            applicant_alerts=prefs.instant_new_applicant_alerts,
            interview_alerts=prefs.interview_confirmation_reminders,
            weekly_digest=prefs.weekly_hiring_digest,
            applicantAlerts=prefs.instant_new_applicant_alerts,
            interviewAlerts=prefs.interview_confirmation_reminders,
            weeklyDigest=prefs.weekly_hiring_digest,
            jobMelaAlerts=prefs.job_mela_alerts,
            updated_at=updated_str,
        )

    @classmethod
    async def update_notification_preferences(
        cls,
        db: AsyncSession,
        current_recruiter: User,
        payload: RecruiterNotificationPreferencesUpdate,
    ) -> RecruiterNotificationPreferencesResponse:
        """Update notification preferences for authenticated recruiter."""
        prefs = await RecruiterSettingsRepository.get_notification_preferences(
            db, current_recruiter.id
        )

        app_alerts = payload.instant_new_applicant_alerts
        if app_alerts is None:
            app_alerts = payload.applicantAlerts

        int_alerts = payload.interview_confirmation_reminders
        if int_alerts is None:
            int_alerts = payload.interviewAlerts

        wk_digest = payload.weekly_hiring_digest
        if wk_digest is None:
            wk_digest = payload.weeklyDigest

        jm_alerts = payload.job_mela_alerts
        if jm_alerts is None:
            jm_alerts = payload.jobMelaAlerts

        if app_alerts is not None:
            prefs.instant_new_applicant_alerts = app_alerts
        if int_alerts is not None:
            prefs.interview_confirmation_reminders = int_alerts
        if wk_digest is not None:
            prefs.weekly_hiring_digest = wk_digest
        if jm_alerts is not None:
            prefs.job_mela_alerts = jm_alerts

        prefs.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(prefs)

        return await cls.get_notification_preferences(db, current_recruiter)

    @classmethod
    async def change_password(
        cls,
        db: AsyncSession,
        current_user: User,
        payload: RecruiterChangePasswordRequest,
    ) -> Dict[str, str]:
        """Securely verify current password and update to new bcrypt hashed password."""
        curr_pwd = payload.current_password or payload.currentPassword
        new_pwd = payload.new_password or payload.newPassword
        conf_pwd = payload.confirm_password or payload.confirmPassword

        if not curr_pwd:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is required.",
            )

        if not new_pwd:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password is required.",
            )

        # Load user in current db session
        db_user = await db.get(User, current_user.id)
        if not db_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User account not found.",
            )

        # 1. Verify current password
        if not verify_password(curr_pwd, db_user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Current password is incorrect.",
            )

        # 2. Minimum length validation
        if len(new_pwd) < 8:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="New password must be at least 8 characters long.",
            )

        # 3. Confirm password matches
        if conf_pwd and new_pwd != conf_pwd:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="New password and confirmation password do not match.",
            )

        # 4. Reject same password
        if verify_password(new_pwd, db_user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password must be different from current password.",
            )

        # 5. Hash and update
        db_user.hashed_password = hash_password(new_pwd)
        await db.commit()

        return {
            "status": "success",
            "message": "Account password updated successfully.",
        }
