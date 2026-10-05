import uuid
from typing import Dict, Any
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.candidate import CandidateProfile
from app.repositories.candidate_repository import CandidateRepository
from app.schemas.auth import (
    CandidateRegisterRequest,
    CandidateRegisterResponse,
    UserSummary,
    CandidateSummary,
)
from app.core.security import hash_password, create_access_token
from app.core.constants import NTR_MANDALS, REFERENCE_ADMINS, DISTRICT_LOCATIONS


class CandidateService:
    @staticmethod
    def validate_dropdown_choices(payload: CandidateRegisterRequest) -> Dict[str, Any]:
        """
        Service-level validation and normalization of frontend dropdown selections:
        - Qualification category (10TH, INTER, UG, PG, etc.)
        - Mandal (checked against official NTR District mandals)
        - Referring Officer / Authority
        - District / City Location
        """
        # 1. Validate & Normalize Mandal Dropdown
        selected_mandal = payload.mandal.strip()
        matched_mandal = next(
            (m for m in NTR_MANDALS if m.lower() == selected_mandal.lower()),
            None,
        )
        if not matched_mandal:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid mandal selected: '{selected_mandal}'. Must be an approved Mandal of NTR District.",
            )

        # 2. Validate & Normalize Reference Admin Dropdown
        selected_ref = (payload.reference_admin or "").strip()
        matched_ref = next(
            (r for r in REFERENCE_ADMINS if r.lower() == selected_ref.lower()),
            None,
        )
        final_ref = matched_ref if matched_ref else "Direct Student Self-Registration"

        # 3. Clean and validate district location string
        selected_district = (payload.district or "NTR District").strip()
        matched_district = next(
            (d for d in DISTRICT_LOCATIONS if d.lower() == selected_district.lower()),
            None,
        )
        if not matched_district:
            matched_district = next(
                (d for d in DISTRICT_LOCATIONS if d.lower() in selected_district.lower()),
                None,
            )
        final_district = (matched_district or selected_district).replace("(Vijayawada)", "").strip() or "NTR District"

        return {
            "mandal": matched_mandal,
            "reference_admin": final_ref,
            "district": final_district,
            "qualification_level": payload.qualification_level,
        }

    @classmethod
    async def register_candidate(
        cls,
        payload: CandidateRegisterRequest,
        db: AsyncSession,
    ) -> CandidateRegisterResponse:
        """
        Direct Candidate Registration Workflow:
        1. Validate terms acceptance
        2. Validate selected dropdown values (Mandal, Qualification, Reference, District)
        3. Verify duplicates in MySQL (Email, Mobile, Aadhaar)
        4. Persist User and CandidateProfile records directly to MySQL via CandidateRepository
        5. Return HTTP 201 response with JWT access token (Aadhaar omitted for security)
        """
        if not payload.terms_accepted:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You must accept the Terms & Conditions and Privacy Policy to register.",
            )

        # Validate dropdown choices
        dropdown_data = cls.validate_dropdown_choices(payload)

        clean_email = payload.email.lower().strip()
        clean_phone = payload.phone.strip()
        clean_aadhaar = payload.aadhaar_number.strip()

        # Check duplicate Email
        existing_email_user = await CandidateRepository.get_user_by_email(db, clean_email)
        if existing_email_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email is already registered. Please login to your account.",
            )

        # Check duplicate Mobile
        existing_phone_user = await CandidateRepository.get_user_by_phone(db, clean_phone)
        if existing_phone_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Mobile number is already registered with another account.",
            )

        # Check duplicate Aadhaar
        existing_candidate = await CandidateRepository.get_candidate_by_aadhaar(db, clean_aadhaar)
        if existing_candidate:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Aadhaar number is already linked to an existing candidate profile.",
            )

        # Hash password
        hashed_pwd = hash_password(payload.password)
        user_id = str(uuid.uuid4())

        new_user = User(
            id=user_id,
            email=clean_email,
            phone=clean_phone,
            hashed_password=hashed_pwd,
            role="CANDIDATE",
            is_active=True,
            is_verified=True,
        )

        candidate_id = str(uuid.uuid4())
        new_candidate = CandidateProfile(
            id=candidate_id,
            user_id=user_id,
            name=payload.name.strip(),
            phone=clean_phone,
            aadhaar_number=clean_aadhaar,
            district=dropdown_data["district"],
            mandal=dropdown_data["mandal"],
            village=payload.village.strip() if payload.village else None,
            qualification_level=dropdown_data["qualification_level"],
            reference_admin=dropdown_data["reference_admin"],
            profile_completion=35,
            verified=True,
        )

        # Direct persistence to MySQL via repository
        user_record, candidate_record = await CandidateRepository.create_candidate(
            db=db,
            user=new_user,
            candidate_profile=new_candidate,
        )

        # Generate authentication token
        token = create_access_token(subject=user_record.id, role="CANDIDATE")

        # Security: Aadhaar number is strictly omitted from the response
        return CandidateRegisterResponse(
            status="success",
            message="Candidate account created successfully. Welcome to NTR VIKASA!",
            access_token=token,
            token_type="bearer",
            user=UserSummary(
                id=user_record.id,
                email=user_record.email,
                phone=user_record.phone,
                role=user_record.role,
                is_active=user_record.is_active,
                is_verified=user_record.is_verified,
            ),
            candidate=CandidateSummary(
                id=candidate_record.id,
                user_id=candidate_record.user_id,
                name=candidate_record.name,
                phone=candidate_record.phone,
                district=candidate_record.district,
                mandal=candidate_record.mandal,
                village=candidate_record.village,
                qualification_level=candidate_record.qualification_level,
                reference_admin=candidate_record.reference_admin,
                profile_completion=candidate_record.profile_completion,
                verified=candidate_record.verified,
            ),
        )
