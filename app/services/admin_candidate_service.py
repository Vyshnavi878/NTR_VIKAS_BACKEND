import uuid
import secrets
from typing import Optional, Dict, Any, List
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.candidate import CandidateProfile
from app.core.security import hash_password
from app.repositories.admin_candidate_repository import (
    AdminCandidateRepository,
    compute_aadhaar_hash,
    mask_aadhaar,
)
from app.repositories.audit_log_repository import AuditLogRepository
from app.schemas.admin_candidate import (
    AdminCreateCandidateRequest,
    AdminUpdateCandidatePlacementRequest,
    AdminUpdateCandidateStatusRequest,
    AdminCandidateItem,
    PaginatedAdminCandidateResponse,
)


class AdminCandidateService:
    """
    Business service layer for Administrator Candidate / Student Governance.
    """

    @classmethod
    async def list_candidates(
        cls,
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        placement_status: Optional[str] = None,
        qualification: Optional[str] = None,
        mandal: Optional[str] = None,
        reference: Optional[str] = None,
        account_status: Optional[str] = None,
    ) -> PaginatedAdminCandidateResponse:
        data = await AdminCandidateRepository.get_admin_candidates(
            db=db,
            page=page,
            page_size=page_size,
            search=search,
            placement_status=placement_status,
            qualification=qualification,
            mandal=mandal,
            reference=reference,
            account_status=account_status,
        )
        return PaginatedAdminCandidateResponse(**data)

    @classmethod
    async def get_candidate_details(
        cls,
        db: AsyncSession,
        candidate_id: str,
    ) -> AdminCandidateItem:
        row = await AdminCandidateRepository.get_candidate_by_id(db, candidate_id)
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Candidate with ID '{candidate_id}' not found.",
            )
        cand, user = row
        is_placed = cand.placement_status == "PLACED" or bool(cand.placed_company)
        return AdminCandidateItem(
            id=cand.id,
            user_id=user.id,
            name=cand.name,
            email=user.email,
            phone=cand.phone or user.phone,
            gender=cand.gender or "Male",
            aadhaar_masked=mask_aadhaar(cand.aadhaar_number),
            district=cand.district or "NTR District",
            mandal=cand.mandal,
            village=cand.village,
            location=cand.location or f"{cand.village + ', ' if cand.village else ''}{cand.mandal or 'Vijayawada Urban'}, {cand.district or 'NTR District'}",
            qualification_level=cand.qualification_level,
            education=(
                f"{cand.qualification_level} Class"
                if cand.qualification_level in ["10TH", "INTER"]
                else (cand.qualification_level or "Pending Profile Completion")
            ),
            headline=cand.headline or "Registered Candidate",
            profile_completion=cand.profile_completion or 35,
            profile_status="BASIC_REGISTERED" if (cand.profile_completion or 35) < 80 else "COMPLETE",
            placement_status="PLACED" if is_placed else "NOT_PLACED",
            placed_company=cand.placed_company or (cand.headline if is_placed else None),
            placed_role=cand.placed_role,
            placed_salary=cand.placed_salary,
            placed_date=cand.placed_date,
            reference_admin=cand.reference_admin or "Admin User (State Operations)",
            custom_referrer=cand.custom_referrer,
            account_status="ACTIVE" if user.is_active else "SUSPENDED",
            registration_date=cand.created_at.strftime("%Y-%m-%d") if cand.created_at else None,
            created_at=cand.created_at,
            applications_count=0,
        )

    @classmethod
    async def create_candidate(
        cls,
        db: AsyncSession,
        current_admin: User,
        payload: AdminCreateCandidateRequest,
    ) -> AdminCandidateItem:
        """
        Manually onboards and registers a student/candidate via administrator direct onboarding.
        """
        clean_email = payload.email.strip().lower()
        clean_phone = payload.mobile_number.strip()
        clean_aadhaar = payload.aadhaar_number.strip()
        fingerprint = compute_aadhaar_hash(clean_aadhaar)

        # 1. Reject duplicate email
        existing_email_user = await AdminCandidateRepository.get_user_by_email(db, clean_email)
        if existing_email_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Candidate email '{clean_email}' is already registered on the platform.",
            )

        # 2. Reject duplicate phone
        existing_phone_user = await AdminCandidateRepository.get_user_by_phone(db, clean_phone)
        if existing_phone_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Mobile phone number '{clean_phone}' is already associated with another account.",
            )

        # 3. Reject duplicate Aadhaar
        existing_aadhaar_cand = await AdminCandidateRepository.get_candidate_by_aadhaar(
            db, clean_aadhaar, fingerprint
        )
        if existing_aadhaar_cand:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Aadhaar Card Number is already linked to an existing candidate profile.",
            )

        # 4. Generate secure initial random password hash
        initial_secret = secrets.token_urlsafe(32)
        hashed_pwd = hash_password(initial_secret)

        user_id = str(uuid.uuid4())
        candidate_id = str(uuid.uuid4())

        new_user = User(
            id=user_id,
            email=clean_email,
            phone=clean_phone,
            hashed_password=hashed_pwd,
            role="CANDIDATE",
            is_active=True,
            is_verified=True,
        )

        # Determine reference admin & custom referrer
        is_other_ref = payload.referred_by.strip().lower() == "other"
        final_ref = payload.custom_referrer.strip() if is_other_ref and payload.custom_referrer else payload.referred_by.strip()
        custom_ref = payload.custom_referrer.strip() if payload.custom_referrer else None

        # Determine placement details
        is_placed = payload.placement_status == "PLACED"
        placed_company = payload.placed_company.strip() if (is_placed and payload.placed_company) else None
        placed_role = payload.placed_role.strip() if (is_placed and payload.placed_role) else None
        placed_salary = payload.placed_salary.strip() if (is_placed and payload.placed_salary) else None
        placed_date = payload.placed_date.strip() if (is_placed and payload.placed_date) else None

        new_cand = CandidateProfile(
            id=candidate_id,
            user_id=user_id,
            name=payload.full_name.strip(),
            phone=clean_phone,
            aadhaar_number=clean_aadhaar,
            aadhaar_hash=fingerprint,
            gender=payload.gender,
            district="NTR District",
            mandal=None,  # Not collected in manual form, left for student profile completion
            village=None,
            qualification_level=None,  # Not fabricated; completed by student
            reference_admin=final_ref,
            custom_referrer=custom_ref,
            onboarded_by_admin_id=current_admin.id,
            headline="Registered Student (KYC Onboarded)" if not is_placed else f"Placed at {placed_company}",
            bio=None,
            profile_completion=35,
            verified=True,
            placement_status="PLACED" if is_placed else "NOT_PLACED",
            placed_company=placed_company,
            placed_role=placed_role,
            placed_salary=placed_salary,
            placed_date=placed_date,
        )

        user_record, cand_record = await AdminCandidateRepository.create_candidate(
            db=db,
            user=new_user,
            candidate=new_cand,
        )

        # 5. Log audit event
        await AuditLogRepository.create_log(
            db=db,
            actor=current_admin.email,
            action="CANDIDATE_MANUALLY_ONBOARDED",
            entity="CANDIDATE",
            entity_id=cand_record.id,
            target_name=f"{cand_record.name} ({mask_aadhaar(clean_aadhaar)})",
            result="SUCCESS",
            metadata={
                "candidate_id": cand_record.id,
                "email": user_record.email,
                "referred_by": final_ref,
                "placement_status": cand_record.placement_status,
                "onboarded_by_admin_id": current_admin.id,
            },
        )

        return AdminCandidateItem(
            id=cand_record.id,
            user_id=user_record.id,
            name=cand_record.name,
            email=user_record.email,
            phone=cand_record.phone,
            gender=cand_record.gender or "Male",
            aadhaar_masked=mask_aadhaar(cand_record.aadhaar_number),
            district=cand_record.district or "NTR District",
            mandal=cand_record.mandal,
            village=cand_record.village,
            location="NTR District",
            qualification_level=cand_record.qualification_level,
            education="Pending Profile Completion",
            headline=cand_record.headline or "Registered Candidate",
            profile_completion=35,
            profile_status="BASIC_REGISTERED",
            placement_status=cand_record.placement_status or "NOT_PLACED",
            placed_company=cand_record.placed_company,
            placed_role=cand_record.placed_role,
            placed_salary=cand_record.placed_salary,
            placed_date=cand_record.placed_date,
            reference_admin=cand_record.reference_admin,
            custom_referrer=cand_record.custom_referrer,
            account_status="ACTIVE",
            registration_date=cand_record.created_at.strftime("%Y-%m-%d") if cand_record.created_at else None,
            created_at=cand_record.created_at,
            applications_count=0,
        )

    @classmethod
    async def update_candidate_placement(
        cls,
        db: AsyncSession,
        current_admin: User,
        candidate_id: str,
        payload: AdminUpdateCandidatePlacementRequest,
    ) -> AdminCandidateItem:
        """
        Updates student placement status and employment details.
        """
        cand = await AdminCandidateRepository.update_candidate_placement(
            db=db,
            candidate_id=candidate_id,
            placement_status=payload.placement_status,
            placed_company=payload.placed_company,
            placed_role=payload.placed_role,
            placed_salary=payload.placed_salary,
            placed_date=payload.placed_date,
        )
        if not cand:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Candidate with ID '{candidate_id}' not found.",
            )

        # Log audit trail
        await AuditLogRepository.create_log(
            db=db,
            actor=current_admin.email,
            action="CANDIDATE_PLACEMENT_UPDATED",
            entity="CANDIDATE",
            entity_id=cand.id,
            target_name=f"{cand.name}: {cand.placement_status} ({cand.placed_company or 'No Company'})",
            result="SUCCESS",
            metadata={
                "candidate_id": cand.id,
                "placement_status": cand.placement_status,
                "placed_company": cand.placed_company,
                "placed_role": cand.placed_role,
            },
        )

        return await cls.get_candidate_details(db, cand.id)

    @classmethod
    async def update_candidate_status(
        cls,
        db: AsyncSession,
        current_admin: User,
        candidate_id: str,
        payload: AdminUpdateCandidateStatusRequest,
    ) -> AdminCandidateItem:
        """
        Updates student account status (ACTIVE or SUSPENDED).
        """
        is_active = payload.status == "ACTIVE"
        row = await AdminCandidateRepository.update_candidate_status(
            db=db,
            candidate_id=candidate_id,
            is_active=is_active,
        )
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Candidate with ID '{candidate_id}' not found.",
            )
        cand, user = row

        action_name = "CANDIDATE_ACTIVATED" if is_active else "CANDIDATE_SUSPENDED"
        await AuditLogRepository.create_log(
            db=db,
            actor=current_admin.email,
            action=action_name,
            entity="CANDIDATE",
            entity_id=cand.id,
            target_name=f"{cand.name} ({user.email})",
            result="SUCCESS",
            metadata={"status": payload.status, "reason": payload.reason},
        )

        return await cls.get_candidate_details(db, cand.id)
