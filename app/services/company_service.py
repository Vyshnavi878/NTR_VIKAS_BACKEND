import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from fastapi import HTTPException, status, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.notification import Notification
from app.repositories.company_repository import CompanyRepository
from app.repositories.recruiter_repository import RecruiterRepository
from app.schemas.company import (
    PublicCompanyItem,
    PaginatedCompanyResponse,
    AdminCompanyVerificationItem,
    AdminCreateCompanyRequest,
    AdminCompanyVerificationUpdate,
    PaginatedAdminCompanyResponse,
    RecruiterCompanyProfileResponse,
    RecruiterCompanyProfileUpdate,
    CompanyLogoUploadResponse,
)


class CompanyService:
    """
    Business service layer for verified public companies and admin company verification.
    """

    @classmethod
    async def get_public_companies(
        cls,
        db: AsyncSession,
        search: Optional[str] = None,
        industry: Optional[str] = None,
        location: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedCompanyResponse:
        """Fetch verified companies for public website."""
        items_data, total = await CompanyRepository.get_verified_companies(
            db=db,
            search=search,
            industry=industry,
            location=location,
            page=page,
            page_size=page_size,
        )

        items = [PublicCompanyItem(**i) for i in items_data]
        total_pages = (total + page_size - 1) // page_size if total > 0 else 1

        return PaginatedCompanyResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    @classmethod
    async def get_public_company_detail(
        cls, db: AsyncSession, company_id: str
    ) -> PublicCompanyItem:
        """Get details for a single verified company."""
        from sqlalchemy import select, func, and_, or_
        from app.models.job import Job, JobSkill
        from app.models.internship import Internship

        profile = await CompanyRepository.get_company_by_id(db, company_id)
        if not profile or profile.status not in ("APPROVED", "VERIFIED"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Company not found or has not been verified.",
            )

        # Count active published jobs
        job_cnt_stmt = select(func.count(Job.id)).where(
            and_(
                or_(Job.recruiter_id == profile.id, Job.company_id == profile.id),
                Job.status == "PUBLISHED",
                Job.closed_at.is_(None),
            )
        )
        open_jobs = (await db.execute(job_cnt_stmt)).scalar() or 0

        # Count active published internships
        intern_cnt_stmt = select(func.count(Internship.id)).where(
            and_(
                Internship.company_id == profile.id,
                Internship.status == "PUBLISHED",
                Internship.closed_at.is_(None),
            )
        )
        open_internships = (await db.execute(intern_cnt_stmt)).scalar() or 0

        # Fetch skills for tech stack
        skills_stmt = (
            select(JobSkill.skill_name)
            .join(Job, Job.id == JobSkill.job_id)
            .where(
                and_(
                    or_(Job.recruiter_id == profile.id, Job.company_id == profile.id),
                    Job.status == "PUBLISHED",
                )
            )
            .distinct()
            .limit(10)
        )
        skills_res = await db.execute(skills_stmt)
        tech_stack = [s for s in skills_res.scalars().all() if s]

        logo_url = None
        if profile.company_logo_path:
            logo_url = profile.company_logo_path if profile.company_logo_path.startswith("http") else f"/{profile.company_logo_path.lstrip('/')}"

        return PublicCompanyItem(
            id=profile.id,
            name=profile.company_name,
            company_name=profile.company_name,
            logo=logo_url or profile.company_logo_path,
            logo_url=logo_url or profile.company_logo_path,
            company_logo_path=profile.company_logo_path,
            industry=profile.primary_industry,
            location=profile.headquarters_city_state,
            tagline=profile.tagline or (profile.company_description[:100] if profile.company_description else None),
            description=profile.company_description,
            website=profile.company_website,
            size=profile.company_size,
            employees=profile.company_size,
            company_size=profile.company_size,
            openJobs=open_jobs,
            open_jobs=open_jobs,
            open_jobs_count=open_jobs,
            openInternships=open_internships,
            open_internships=open_internships,
            open_internships_count=open_internships,
            rating=None,
            tech_stack=tech_stack if tech_stack else None,
            verified=True,
        )


    @classmethod
    async def get_admin_companies(
        cls,
        db: AsyncSession,
        status_filter: Optional[str] = "ALL",
        search: Optional[str] = None,
        industry_filter: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> PaginatedAdminCompanyResponse:
        """Admin list company verification requests with pagination, search, and metrics."""
        items_data, total, verified_count = await CompanyRepository.get_admin_companies(
            db=db,
            status_filter=status_filter,
            search=search,
            industry_filter=industry_filter,
            page=page,
            page_size=page_size,
        )
        items = [AdminCompanyVerificationItem(**i) for i in items_data]
        total_pages = (total + page_size - 1) // page_size if total > 0 else 1

        return PaginatedAdminCompanyResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            verified_count=verified_count,
        )

    @classmethod
    async def get_admin_company_by_id(
        cls, db: AsyncSession, company_id: str
    ) -> AdminCompanyVerificationItem:
        """Fetch full company information for Admin View."""
        data = await CompanyRepository.get_company_full_details(db, company_id)
        if not data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Company with ID '{company_id}' not found.",
            )
        return AdminCompanyVerificationItem(**data)

    @classmethod
    async def create_admin_company(
        cls, db: AsyncSession, current_admin: User, payload: AdminCreateCompanyRequest
    ) -> AdminCompanyVerificationItem:
        """Directly onboard and verify a company through Admin."""
        created_data = await CompanyRepository.create_admin_company(
            db=db,
            admin_user=current_admin,
            payload=payload,
        )
        return AdminCompanyVerificationItem(**created_data)

    @classmethod
    async def update_company_verification(
        cls,
        db: AsyncSession,
        current_admin: User,
        company_id: str,
        payload: AdminCompanyVerificationUpdate,
    ) -> AdminCompanyVerificationItem:
        """Update company verification status (approve, reject, suspend, pending)."""
        updated_data = await CompanyRepository.update_company_verification(
            db=db,
            admin_user=current_admin,
            company_id=company_id,
            target_status=payload.status,
            reason=payload.reason,
        )
        return AdminCompanyVerificationItem(**updated_data)

    @classmethod
    async def approve_company(
        cls, db: AsyncSession, current_admin: User, company_id: str
    ) -> Dict[str, Any]:
        """Admin approves company verification request."""
        updated = await CompanyRepository.update_company_verification(
            db=db,
            admin_user=current_admin,
            company_id=company_id,
            target_status="APPROVED",
        )
        return {
            "id": updated["id"],
            "company_name": updated["company_name"],
            "status": "APPROVED",
            "verification_status": "VERIFIED",
            "reviewed_at": updated.get("reviewed_at"),
            "reviewed_by": updated.get("reviewed_by"),
            "message": f"Company '{updated['company_name']}' has been verified and approved successfully.",
        }

    @classmethod
    async def reject_company(
        cls, db: AsyncSession, current_admin: User, company_id: str, reason: str
    ) -> Dict[str, Any]:
        """Admin rejects company verification request with mandatory reason."""
        updated = await CompanyRepository.update_company_verification(
            db=db,
            admin_user=current_admin,
            company_id=company_id,
            target_status="REJECTED",
            reason=reason,
        )
        return {
            "id": updated["id"],
            "company_name": updated["company_name"],
            "status": "REJECTED",
            "verification_status": "REJECTED",
            "rejection_reason": updated.get("rejection_reason"),
            "reviewed_at": updated.get("reviewed_at"),
            "reviewed_by": updated.get("reviewed_by"),
            "message": f"Company '{updated['company_name']}' verification has been rejected.",
        }

    @classmethod
    async def suspend_company(
        cls, db: AsyncSession, current_admin: User, company_id: str, reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """Admin suspends company account and recruitment privileges."""
        updated = await CompanyRepository.update_company_verification(
            db=db,
            admin_user=current_admin,
            company_id=company_id,
            target_status="SUSPENDED",
            reason=reason or "Company account suspended by state administrator.",
        )
        return {
            "id": updated["id"],
            "company_name": updated["company_name"],
            "status": "SUSPENDED",
            "verification_status": "SUSPENDED",
            "accountStatus": "SUSPENDED",
            "message": f"Company '{updated['company_name']}' has been suspended.",
        }

    @classmethod
    async def get_company_documents(
        cls, db: AsyncSession, company_id: str
    ) -> List[Dict[str, Any]]:
        """Retrieve verification compliance documents for a company."""
        return await CompanyRepository.get_company_documents(db, company_id)

    @classmethod
    async def export_company_dossier(
        cls, db: AsyncSession, company_id: str
    ) -> Dict[str, Any]:
        """Export comprehensive dossier data for a single company."""
        data = await CompanyRepository.get_company_full_details(db, company_id)
        if not data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Company with ID '{company_id}' not found.",
            )
        return data


    @classmethod
    def _build_profile_response(cls, profile) -> RecruiterCompanyProfileResponse:
        v_status = (
            "VERIFIED"
            if profile.status in ("APPROVED", "VERIFIED")
            else ("REJECTED" if profile.status == "REJECTED" else "PENDING_VERIFICATION")
        )
        logo_url = profile.company_logo_path
        if logo_url and not logo_url.startswith("/") and not logo_url.startswith("http"):
            logo_url = f"/{logo_url}"

        return RecruiterCompanyProfileResponse(
            id=profile.id,
            company_name=profile.company_name,
            name=profile.company_name,
            industry=profile.primary_industry,
            primary_industry=profile.primary_industry,
            tagline=profile.tagline,
            official_website=profile.company_website,
            website=profile.company_website,
            careers_email=profile.corporate_email or profile.work_email,
            email=profile.corporate_email or profile.work_email,
            corporate_email=profile.corporate_email or profile.work_email,
            contact_phone=profile.company_phone or profile.mobile_phone,
            phone=profile.company_phone or profile.mobile_phone,
            company_phone=profile.company_phone or profile.mobile_phone,
            company_size=profile.company_size,
            size=profile.company_size,
            location=profile.headquarters_city_state,
            headquarters_city_state=profile.headquarters_city_state,
            registered_office_address=profile.registered_office_address,
            address=profile.registered_office_address,
            about_company=profile.company_description,
            description=profile.company_description,
            company_description=profile.company_description,
            logo_url=logo_url,
            logo=logo_url,
            company_logo_path=profile.company_logo_path,
            verification_status=v_status,
            status=profile.status,
            verified=profile.status in ("APPROVED", "VERIFIED"),
            cin_number=profile.cin_number,
            cinNumber=profile.cin_number,
            gst_number=profile.gst_number,
            gstNumber=profile.gst_number,
            rejection_reason=profile.rejection_reason,
        )

    @classmethod
    async def get_recruiter_company_profile(
        cls, db: AsyncSession, current_recruiter: User
    ) -> RecruiterCompanyProfileResponse:
        """Fetch the authenticated recruiter's associated company profile."""
        profile = await RecruiterRepository.get_profile_by_user_id(db, current_recruiter.id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Company profile not found for authenticated recruiter account.",
            )

        return cls._build_profile_response(profile)

    @classmethod
    async def update_recruiter_company_profile(
        cls,
        db: AsyncSession,
        current_recruiter: User,
        payload: RecruiterCompanyProfileUpdate,
    ) -> RecruiterCompanyProfileResponse:
        """Update editable profile fields for the authenticated recruiter's company."""
        profile = await RecruiterRepository.get_profile_by_user_id(db, current_recruiter.id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Company profile not found for authenticated recruiter account.",
            )

        # Company legal name
        company_name = payload.company_name or payload.name
        if company_name is not None and company_name.strip():
            profile.company_name = company_name.strip()

        # Industry
        industry = payload.industry or payload.primary_industry
        if industry is not None and industry.strip():
            profile.primary_industry = industry.strip()

        # Tagline
        if payload.tagline is not None:
            profile.tagline = payload.tagline.strip()

        # Official Website
        website = payload.official_website or payload.website
        if website is not None:
            profile.company_website = website.strip()

        # Careers Email
        careers_email = payload.careers_email or payload.email
        if careers_email is not None:
            profile.corporate_email = careers_email.strip()

        # Contact Phone
        phone = payload.contact_phone or payload.phone
        if phone is not None:
            profile.company_phone = phone.strip()

        # Company Size
        size = payload.company_size or payload.size
        if size is not None and size.strip():
            profile.company_size = size.strip()

        # Registered Office Address
        address = payload.registered_office_address or payload.address
        if address is not None and address.strip():
            profile.registered_office_address = address.strip()

        # About Company (Overview)
        description = payload.about_company or payload.description
        if description is not None and description.strip():
            profile.company_description = description.strip()

        # Location
        if payload.location is not None and payload.location.strip():
            profile.headquarters_city_state = payload.location.strip()

        # CIN & GST
        cin = payload.cin_number or payload.cinNumber
        if cin is not None:
            profile.cin_number = cin.strip()

        gst = payload.gst_number or payload.gstNumber
        if gst is not None:
            profile.gst_number = gst.strip()

        profile.updated_at = datetime.now(timezone.utc)
        await RecruiterRepository.update_profile(db, profile)

        return cls._build_profile_response(profile)

    @classmethod
    async def upload_recruiter_company_logo(
        cls,
        db: AsyncSession,
        current_recruiter: User,
        upload_file: UploadFile,
    ) -> CompanyLogoUploadResponse:
        """Upload and associate a company logo with the authenticated recruiter's organization."""
        from app.services.recruiter_service import RecruiterService

        profile = await RecruiterRepository.get_profile_by_user_id(db, current_recruiter.id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Company profile not found for authenticated recruiter account.",
            )

        saved_path = await RecruiterService.save_uploaded_file(
            upload_file=upload_file,
            is_logo=True,
            required=True,
        )

        profile.company_logo_path = saved_path
        profile.updated_at = datetime.now(timezone.utc)
        await RecruiterRepository.update_profile(db, profile)

        logo_url = f"/{saved_path}" if saved_path and not saved_path.startswith("/") else saved_path
        return CompanyLogoUploadResponse(
            logo_url=logo_url,
            message="Company logo uploaded successfully.",
        )
