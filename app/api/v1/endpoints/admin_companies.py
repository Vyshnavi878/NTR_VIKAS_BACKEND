from typing import Optional, List, Dict, Any, Union
from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_database, get_current_admin
from app.models.user import User
from app.schemas.company import (
    AdminCompanyVerificationItem,
    AdminCreateCompanyRequest,
    AdminCompanyVerificationUpdate,
    PaginatedAdminCompanyResponse,
    CompanyVerificationDecision,
)
from app.services.company_service import CompanyService

router = APIRouter(
    prefix="/admin/companies",
    tags=["Admin Company Governance"],
)

verification_alias_router = APIRouter(
    prefix="/admin/company-verifications",
    tags=["Admin Company Verification"],
)

singular_verification_alias_router = APIRouter(
    prefix="/admin/company-verification",
    tags=["Admin Company Verification"],
)


@router.get(
    "",
    response_model=Union[PaginatedAdminCompanyResponse, List[AdminCompanyVerificationItem]],
    status_code=status.HTTP_200_OK,
    summary="List company verifications for Admin review",
    description="Retrieve all registered companies with pagination, search, status and industry filters, and metrics.",
)
async def list_admin_companies(
    status: Optional[str] = Query("ALL", description="Filter by status: ALL, PENDING, VERIFIED, REJECTED, SUSPENDED"),
    search: Optional[str] = Query(None, description="Search by company name, recruiter lead, email, location"),
    industry: Optional[str] = Query(None, description="Filter by industry domain"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Records per page"),
    raw_list: bool = Query(False, description="Set true to return a flat list instead of paginated object"),
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_database),
) -> Union[PaginatedAdminCompanyResponse, List[AdminCompanyVerificationItem]]:
    """GET /api/v1/admin/companies"""
    res = await CompanyService.get_admin_companies(
        db=db,
        status_filter=status,
        search=search,
        industry_filter=industry,
        page=page,
        page_size=page_size,
    )
    if raw_list:
        return res.items
    return res


@router.post(
    "",
    response_model=AdminCompanyVerificationItem,
    status_code=status.HTTP_201_CREATED,
    summary="Direct Onboard Corporate Employer / Enterprise",
    description="Directly register and verify an enterprise partner by Administrator in MySQL.",
)
async def create_admin_company(
    payload: AdminCreateCompanyRequest,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_database),
) -> AdminCompanyVerificationItem:
    """POST /api/v1/admin/companies"""
    return await CompanyService.create_admin_company(
        db=db,
        current_admin=current_admin,
        payload=payload,
    )


@router.get(
    "/{company_id}",
    response_model=AdminCompanyVerificationItem,
    status_code=status.HTTP_200_OK,
    summary="Get single company profile details",
    description="Retrieve comprehensive registration, contact, and audit information for a company.",
)
async def get_admin_company(
    company_id: str,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_database),
) -> AdminCompanyVerificationItem:
    """GET /api/v1/admin/companies/{company_id}"""
    return await CompanyService.get_admin_company_by_id(
        db=db,
        company_id=company_id,
    )


@router.patch(
    "/{company_id}/verification",
    response_model=AdminCompanyVerificationItem,
    status_code=status.HTTP_200_OK,
    summary="Update company verification governance status",
    description="Approve, reject, or suspend company verification status.",
)
async def update_company_verification(
    company_id: str,
    payload: AdminCompanyVerificationUpdate,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_database),
) -> AdminCompanyVerificationItem:
    """PATCH /api/v1/admin/companies/{company_id}/verification"""
    return await CompanyService.update_company_verification(
        db=db,
        current_admin=current_admin,
        company_id=company_id,
        payload=payload,
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


@router.post(
    "/{company_id}/suspend",
    status_code=status.HTTP_200_OK,
    summary="Suspend company recruitment privileges",
    description="Admin suspends company account and recruitment privileges.",
)
async def suspend_company(
    company_id: str,
    payload: Optional[CompanyVerificationDecision] = None,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_database),
) -> Dict[str, Any]:
    """POST /api/v1/admin/companies/{company_id}/suspend"""
    reason = payload.reason if payload else "Company account suspended by administrator."
    return await CompanyService.suspend_company(
        db=db,
        current_admin=current_admin,
        company_id=company_id,
        reason=reason,
    )


@router.get(
    "/{company_id}/documents",
    response_model=List[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="Get verification documents for a company",
    description="Retrieve stored corporate compliance documents if they exist.",
)
async def get_company_documents(
    company_id: str,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_database),
) -> List[Dict[str, Any]]:
    """GET /api/v1/admin/companies/{company_id}/documents"""
    return await CompanyService.get_company_documents(
        db=db,
        company_id=company_id,
    )


@router.get(
    "/{company_id}/export",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Export individual company registration dossier",
    description="Export comprehensive company details for dossier or PDF generation.",
)
async def export_company_dossier(
    company_id: str,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_database),
) -> Dict[str, Any]:
    """GET /api/v1/admin/companies/{company_id}/export"""
    return await CompanyService.export_company_dossier(
        db=db,
        company_id=company_id,
    )


# Attach backward-compatible aliases to verification_alias_router (/admin/company-verifications)
verification_alias_router.add_api_route(
    "",
    list_admin_companies,
    methods=["GET"],
    response_model=Union[PaginatedAdminCompanyResponse, List[AdminCompanyVerificationItem]],
    status_code=status.HTTP_200_OK,
    summary="List company verifications (/admin/company-verifications)",
    include_in_schema=False,
)
verification_alias_router.add_api_route(
    "/{company_id}/approve",
    approve_company,
    methods=["POST", "PATCH"],
    status_code=status.HTTP_200_OK,
    summary="Approve company verification (/admin/company-verifications/{id}/approve)",
    include_in_schema=False,
)
verification_alias_router.add_api_route(
    "/{company_id}/reject",
    reject_company,
    methods=["POST", "PATCH"],
    status_code=status.HTTP_200_OK,
    summary="Reject company verification (/admin/company-verifications/{id}/reject)",
    include_in_schema=False,
)

# Attach aliases to singular_verification_alias_router (/admin/company-verification)
singular_verification_alias_router.add_api_route(
    "",
    list_admin_companies,
    methods=["GET"],
    response_model=Union[PaginatedAdminCompanyResponse, List[AdminCompanyVerificationItem]],
    status_code=status.HTTP_200_OK,
    summary="List company verifications (/admin/company-verification)",
    include_in_schema=False,
)
singular_verification_alias_router.add_api_route(
    "/{company_id}/approve",
    approve_company,
    methods=["POST", "PATCH"],
    status_code=status.HTTP_200_OK,
    summary="Approve company verification (/admin/company-verification/{id}/approve)",
    include_in_schema=False,
)
singular_verification_alias_router.add_api_route(
    "/{company_id}/reject",
    reject_company,
    methods=["POST", "PATCH"],
    status_code=status.HTTP_200_OK,
    summary="Reject company verification (/admin/company-verification/{id}/reject)",
    include_in_schema=False,
)
