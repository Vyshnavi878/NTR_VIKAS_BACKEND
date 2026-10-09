from typing import Optional, Dict, Any, List
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.admin_recruiter_repository import AdminRecruiterRepository
from app.schemas.admin_recruiter import (
    AdminRecruiterItem,
    PaginatedAdminRecruiterResponse,
    AdminCreateRecruiterRequest,
    AdminRecruiterVerificationUpdate,
    AdminRecruiterAccountStatusUpdate,
    AdminRecruiterDetail,
)


class AdminRecruiterService:
    """
    Business service layer for Admin Recruiter management.
    """

    @classmethod
    async def get_admin_recruiters(
        cls,
        db: AsyncSession,
        status_filter: Optional[str] = "ALL",
        company_filter: Optional[str] = "ALL",
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> PaginatedAdminRecruiterResponse:
        """Fetch paginated recruiters for the Admin Recruiters Management table."""
        items_data, total, verified_cnt, pending_cnt, suspended_cnt = (
            await AdminRecruiterRepository.get_admin_recruiters(
                db=db,
                status_filter=status_filter,
                company_filter=company_filter,
                search=search,
                page=page,
                page_size=page_size,
            )
        )

        items = [AdminRecruiterItem(**i) for i in items_data]
        total_pages = (total + page_size - 1) // page_size if total > 0 else 1

        return PaginatedAdminRecruiterResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            verified_count=verified_cnt,
            pending_count=pending_cnt,
            suspended_count=suspended_cnt,
        )

    @classmethod
    async def get_admin_recruiter_detail(
        cls, db: AsyncSession, recruiter_id: str
    ) -> AdminRecruiterDetail:
        """Fetch complete recruiter dossier by ID."""
        data = await AdminRecruiterRepository.get_recruiter_by_id(db, recruiter_id)
        if not data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Recruiter with ID '{recruiter_id}' not found.",
            )
        return AdminRecruiterDetail(**data)

    @classmethod
    async def create_admin_recruiter(
        cls, db: AsyncSession, current_admin: User, payload: AdminCreateRecruiterRequest
    ) -> AdminRecruiterItem:
        """Directly onboard and verify recruiter account through Admin."""
        created_data = await AdminRecruiterRepository.create_admin_recruiter(
            db=db,
            admin_user=current_admin,
            payload=payload,
        )
        return AdminRecruiterItem(**created_data)

    @classmethod
    async def update_verification(
        cls,
        db: AsyncSession,
        current_admin: User,
        recruiter_id: str,
        payload: AdminRecruiterVerificationUpdate,
    ) -> AdminRecruiterItem:
        """Update recruiter verification status (VERIFIED, REJECTED, PENDING)."""
        updated_data = await AdminRecruiterRepository.update_recruiter_verification(
            db=db,
            admin_user=current_admin,
            recruiter_id=recruiter_id,
            target_status=payload.status,
            notes=payload.notes,
            reason=payload.reason,
        )
        return AdminRecruiterItem(**updated_data)

    @classmethod
    async def update_account_status(
        cls,
        db: AsyncSession,
        current_admin: User,
        recruiter_id: str,
        payload: AdminRecruiterAccountStatusUpdate,
    ) -> AdminRecruiterItem:
        """Suspend or activate a recruiter account."""
        updated_data = await AdminRecruiterRepository.update_recruiter_account_status(
            db=db,
            admin_user=current_admin,
            recruiter_id=recruiter_id,
            target_status=payload.status,
            reason=payload.reason,
        )
        return AdminRecruiterItem(**updated_data)

    @classmethod
    async def export_recruiter_dossier(
        cls, db: AsyncSession, recruiter_id: str
    ) -> Dict[str, Any]:
        """Generate comprehensive dossier export data for recruiter report download."""
        detail = await cls.get_admin_recruiter_detail(db, recruiter_id)
        return {
            "title": f"Recruiter Dossier - {detail.name}",
            "generated_at": detail.registration_date,
            "recruiter": detail.model_dump(),
            "export_type": "PDF_DOSSIER",
        }
