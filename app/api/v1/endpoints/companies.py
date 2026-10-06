from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_database
from app.schemas.company import (
    PublicCompanyItem,
    PaginatedCompanyResponse,
)
from app.services.company_service import CompanyService

router = APIRouter(
    prefix="/companies",
    tags=["Companies (Public)"],
)

public_alias_router = APIRouter(
    prefix="/public/companies",
    tags=["Companies (Public)"],
)


@router.get(
    "",
    response_model=PaginatedCompanyResponse,
    status_code=status.HTTP_200_OK,
    summary="List verified public companies",
    description="Retrieve verified and approved companies with active job and internship counts. Excludes pending or rejected organizations.",
)
async def list_public_companies(
    search: Optional[str] = Query(None, description="Search term for company name, industry, or location"),
    industry: Optional[str] = Query(None, description="Industry filter"),
    location: Optional[str] = Query(None, description="Location filter"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_database),
) -> PaginatedCompanyResponse:
    """GET /api/v1/companies"""
    return await CompanyService.get_public_companies(
        db=db,
        search=search,
        industry=industry,
        location=location,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{company_id}",
    response_model=PublicCompanyItem,
    status_code=status.HTTP_200_OK,
    summary="Get verified company details",
    description="Retrieve public details for a verified organization.",
)
async def get_public_company_detail(
    company_id: str,
    db: AsyncSession = Depends(get_database),
) -> PublicCompanyItem:
    """GET /api/v1/companies/{company_id}"""
    return await CompanyService.get_public_company_detail(
        db=db, company_id=company_id
    )


# Attach routes to public_alias_router
public_alias_router.add_api_route(
    "",
    list_public_companies,
    methods=["GET"],
    response_model=PaginatedCompanyResponse,
    status_code=status.HTTP_200_OK,
    summary="List verified public companies (/public/companies)",
)
public_alias_router.add_api_route(
    "/{company_id}",
    get_public_company_detail,
    methods=["GET"],
    response_model=PublicCompanyItem,
    status_code=status.HTTP_200_OK,
    summary="Get verified company details (/public/companies/{id})",
)
