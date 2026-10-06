from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_database, get_current_admin
from app.models.user import User
from app.schemas.company import (
    AdminCompanyVerificationItem,
    CompanyVerificationDecision,
)
from app.services.company_service import CompanyService

router = APIRouter(
    prefix="/admin/companies",
    tags=["Admin Company Verification"],
)

verification_alias_router = APIRouter(
    prefix="/admin/company-verifications",
    tags=["Admin Company Verification"],
)


@router.get(
    "",
    response_model=List[AdminCompanyVerificationItem],
    status_code=status.HTTP_200_OK,
    summary="List company verifications for Admin review",
    description="Retrieve all registered companies with compliance documents, status filters, and recruiter details.",
)
async def list_admin_companies(
    status: Optional[str] = Query("ALL", description="Filter by status: ALL, PENDING, VERIFIED, REJECTED"),
    search: Optional[str] = Query(None, description="Search by company name, recruiter, email, location"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_database),
) -> List[AdminCompanyVerificationItem]:
    """GET /api/v1/admin/companies"""
    return await CompanyService.get_admin_companies(
        db=db,
        status_filter=status,
        search=search,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/{company_id}/approve",
    status_code=status.HTTP_200_OK,
    summary="Approve company verification",
    description="Admin approves company registration, granting recruitment privileges and publishing company.",
)
async def approve_company(
    company_id: str,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_database),
) -> Dict[str, Any]:
    """POST /api/v1/admin/companies/{company_id}/approve"""
    return await CompanyService.approve_company(
        db=db,
        current_admin=current_admin,
        company_id=company_id,
    )


@router.post(
    "/{company_id}/reject",
    status_code=status.HTTP_200_OK,
    summary="Reject company verification",
    description="Admin rejects company registration with a mandatory explanation.",
)
async def reject_company(
    company_id: str,
    payload: CompanyVerificationDecision,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_database),
) -> Dict[str, Any]:
    """POST /api/v1/admin/companies/{company_id}/reject"""
    return await CompanyService.reject_company(
        db=db,
        current_admin=current_admin,
        company_id=company_id,
        reason=payload.reason or "Verification criteria and documentation requirements not met.",
    )


# Attach aliases to verification_alias_router
verification_alias_router.add_api_route(
    "",
    list_admin_companies,
    methods=["GET"],
    response_model=List[AdminCompanyVerificationItem],
    status_code=status.HTTP_200_OK,
    summary="List company verifications (/admin/company-verifications)",
)
verification_alias_router.add_api_route(
    "/{company_id}/approve",
    approve_company,
    methods=["POST", "PATCH"],
    status_code=status.HTTP_200_OK,
    summary="Approve company verification (/admin/company-verifications/{id}/approve)",
)
verification_alias_router.add_api_route(
    "/{company_id}/reject",
    reject_company,
    methods=["POST", "PATCH"],
    status_code=status.HTTP_200_OK,
    summary="Reject company verification (/admin/company-verifications/{id}/reject)",
)

# Attach aliases to singular_verification_alias_router (/admin/company-verification)
singular_verification_alias_router = APIRouter(
    prefix="/admin/company-verification",
    tags=["Admin Company Verification"],
)
singular_verification_alias_router.add_api_route(
    "",
    list_admin_companies,
    methods=["GET"],
    response_model=List[AdminCompanyVerificationItem],
    status_code=status.HTTP_200_OK,
    summary="List company verifications (/admin/company-verification)",
)
singular_verification_alias_router.add_api_route(
    "/{company_id}/approve",
    approve_company,
    methods=["POST", "PATCH"],
    status_code=status.HTTP_200_OK,
    summary="Approve company verification (/admin/company-verification/{id}/approve)",
)
singular_verification_alias_router.add_api_route(
    "/{company_id}/reject",
    reject_company,
    methods=["POST", "PATCH"],
    status_code=status.HTTP_200_OK,
    summary="Reject company verification (/admin/company-verification/{id}/reject)",
)

