from fastapi import APIRouter, Depends, UploadFile, File, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_database, get_current_recruiter
from app.models.user import User
from app.schemas.company import (
    RecruiterCompanyProfileResponse,
    RecruiterCompanyProfileUpdate,
    CompanyLogoUploadResponse,
)
from app.services.company_service import CompanyService

router = APIRouter(
    prefix="/recruiter/company",
    tags=["Recruiter Company Profile"],
)


@router.get(
    "/profile",
    response_model=RecruiterCompanyProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Get authenticated recruiter company profile",
    description="Retrieve company details, verification status, and brand metadata for the authenticated recruiter.",
)
@router.get(
    "",
    response_model=RecruiterCompanyProfileResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def get_company_profile(
    current_recruiter: User = Depends(get_current_recruiter),
    db: AsyncSession = Depends(get_database),
) -> RecruiterCompanyProfileResponse:
    """
    GET /api/v1/recruiter/company/profile
    Requires Bearer JWT token with RECRUITER role.
    """
    return await CompanyService.get_recruiter_company_profile(
        db=db, current_recruiter=current_recruiter
    )


@router.patch(
    "/profile",
    response_model=RecruiterCompanyProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Update authenticated recruiter company profile",
    description="Update company legal name, industry, tagline, website, careers email, phone, size, address, and overview.",
)
@router.patch(
    "",
    response_model=RecruiterCompanyProfileResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
@router.put(
    "/profile",
    response_model=RecruiterCompanyProfileResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
@router.put(
    "",
    response_model=RecruiterCompanyProfileResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def update_company_profile(
    payload: RecruiterCompanyProfileUpdate,
    current_recruiter: User = Depends(get_current_recruiter),
    db: AsyncSession = Depends(get_database),
) -> RecruiterCompanyProfileResponse:
    """
    PATCH /api/v1/recruiter/company/profile
    Requires Bearer JWT token with RECRUITER role.
    """
    return await CompanyService.update_recruiter_company_profile(
        db=db, current_recruiter=current_recruiter, payload=payload
    )


@router.post(
    "/logo",
    response_model=CompanyLogoUploadResponse,
    status_code=status.HTTP_200_OK,
    summary="Upload company logo",
    description="Upload an official company logo image (PNG, JPG, JPEG, WebP, SVG max 2MB).",
)
async def upload_company_logo(
    file: UploadFile = File(..., description="Company logo image file (max 2MB)"),
    current_recruiter: User = Depends(get_current_recruiter),
    db: AsyncSession = Depends(get_database),
) -> CompanyLogoUploadResponse:
    """
    POST /api/v1/recruiter/company/logo
    Requires Bearer JWT token with RECRUITER role.
    """
    return await CompanyService.upload_recruiter_company_logo(
        db=db, current_recruiter=current_recruiter, upload_file=file
    )
