import os
import re
import uuid
from pathlib import Path
from typing import Optional
from fastapi import HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import (
    RECRUITER_INDUSTRIES,
    RECRUITER_COMPANY_SIZES,
    APPROVED_HEADQUARTERS_CITIES,
    RecruiterStatus,
)
from app.core.security import hash_password
from app.models.user import User
from app.models.recruiter import RecruiterProfile
from app.repositories.recruiter_repository import RecruiterRepository
from app.schemas.recruiter import RecruiterRegisterResponse

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DOCUMENTS_DIR = BASE_DIR / "uploads" / "documents"
LOGOS_DIR = BASE_DIR / "uploads" / "logos"

ALLOWED_DOC_TYPES = {
    "application/pdf": ".pdf",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
}

ALLOWED_LOGO_TYPES = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/webp": ".webp",
    "image/svg+xml": ".svg",
    "image/svg": ".svg",
}

MAX_DOC_SIZE = 5 * 1024 * 1024   # 5 MB
MAX_LOGO_SIZE = 2 * 1024 * 1024  # 2 MB


class RecruiterService:
    """
    Service layer handling recruiter registration:
    - Input normalization & validation
    - Dropdown fixed-list validation
    - Secure file upload inspection & storage
    - Password hashing & duplicate checks
    - Async MySQL persistence via RecruiterRepository
    """

    @classmethod
    def validate_contact_details(
        cls,
        recruiter_name: str,
        designation: str,
        work_email: str,
        mobile_phone: str,
        password: str,
        confirm_password: str,
    ) -> tuple[str, str, str, str]:
        """Validate recruiter contact details and credentials."""
        if not recruiter_name or not recruiter_name.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Recruiter / HR Name is required.",
            )

        if not designation or not designation.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Official Designation is required.",
            )

        # Email validation & normalization
        clean_email = work_email.strip().lower() if work_email else ""
        email_regex = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
        if not clean_email or not re.match(email_regex, clean_email):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="A valid Work Email Address is required.",
            )

        # Phone validation
        clean_phone = re.sub(r"[\s\-\(\)\+]", "", mobile_phone or "")
        if clean_phone.startswith("91") and len(clean_phone) == 12:
            clean_phone = clean_phone[2:]
        if not clean_phone or not re.match(r"^[6-9]\d{9}$", clean_phone):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Mobile Phone must be a valid 10-digit Indian mobile number starting with 6-9.",
            )

        # Password validation
        if not password or len(password) < 8:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Password must be at least 8 characters long.",
            )

        if password != confirm_password:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Create Password and Confirm Password do not match.",
            )

        return recruiter_name.strip(), designation.strip(), clean_email, clean_phone

    @classmethod
    def validate_company_details(
        cls,
        company_name: str,
        company_website: str,
        corporate_email: Optional[str],
        company_phone: Optional[str],
        primary_industry: str,
        company_size: str,
        headquarters_city_state: str,
        registered_office_address: str,
        company_description: str,
    ) -> tuple[str, str, Optional[str], Optional[str], str, str, str, str, str]:
        """Validate company profile and enforce fixed dropdown constants."""
        if not company_name or not company_name.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Company / Organization Name is required.",
            )

        # Website validation
        clean_website = company_website.strip() if company_website else ""
        website_regex = r"^(https?:\/\/)?([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}(:\d+)?(\/.*)?$"
        if not clean_website or not re.match(website_regex, clean_website):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Company Website must be a valid web address (e.g., https://company.com).",
            )

        # Corporate email (optional)
        clean_corp_email = corporate_email.strip().lower() if corporate_email and corporate_email.strip() else None
        if clean_corp_email:
            email_regex = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
            if not re.match(email_regex, clean_corp_email):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Corporate Email format is invalid.",
                )

        # Corporate phone (optional)
        clean_corp_phone = company_phone.strip() if company_phone and company_phone.strip() else None

        # Fixed dropdown validations - must match exact approved string list
        selected_industry = (primary_industry or "").strip()
        if selected_industry not in RECRUITER_INDUSTRIES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid Primary Industry selected: '{selected_industry}'. Must be one of: {', '.join(RECRUITER_INDUSTRIES)}",
            )

        selected_size = (company_size or "").strip()
        if selected_size not in RECRUITER_COMPANY_SIZES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid Company Size selected: '{selected_size}'. Must be one of: {', '.join(RECRUITER_COMPANY_SIZES)}",
            )

        selected_hq = (headquarters_city_state or "").strip()
        if selected_hq not in APPROVED_HEADQUARTERS_CITIES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid Headquarters City/State selected: '{selected_hq}'. Must be one of approved AP districts: {', '.join(APPROVED_HEADQUARTERS_CITIES)}",
            )

        if not registered_office_address or not registered_office_address.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Registered Office Address is required.",
            )

        if not company_description or not company_description.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Company Overview & Description is required.",
            )

        return (
            company_name.strip(),
            clean_website,
            clean_corp_email,
            clean_corp_phone,
            selected_industry,
            selected_size,
            selected_hq,
            registered_office_address.strip(),
            company_description.strip(),
        )

    @classmethod
    async def save_uploaded_file(
        cls,
        upload_file: Optional[UploadFile],
        is_logo: bool = False,
        required: bool = True,
    ) -> Optional[str]:
        """
        Validate file presence, size, MIME type, and save securely with UUID filename.
        Returns the saved relative path (e.g. 'uploads/documents/uuid.pdf').
        """
        if not upload_file or not upload_file.filename:
            if required:
                doc_name = "Company Logo" if is_logo else "Verification Document"
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"{doc_name} is required.",
                )
            return None

        # Read content
        content = await upload_file.read()
        file_size = len(content)

        max_size = MAX_LOGO_SIZE if is_logo else MAX_DOC_SIZE
        max_size_label = "2 MB" if is_logo else "5 MB"

        if file_size == 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Uploaded file '{upload_file.filename}' is empty.",
            )

        if file_size > max_size:
            label = "Company Logo" if is_logo else "Document"
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"{label} file size exceeds maximum permitted limit of {max_size_label}.",
            )

        # Validate MIME / content type
        content_type = (upload_file.content_type or "").lower().strip()
        filename_ext = Path(upload_file.filename).suffix.lower()

        allowed_map = ALLOWED_LOGO_TYPES if is_logo else ALLOWED_DOC_TYPES
        allowed_exts = set(allowed_map.values())

        # Determine extension from filename or content type
        ext = None
        if content_type in allowed_map:
            ext = allowed_map[content_type]
        elif filename_ext in allowed_exts:
            ext = filename_ext

        if not ext:
            allowed_desc = "PNG, SVG, JPG/JPEG" if is_logo else "PDF, JPG/JPEG, PNG"
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid file format for '{upload_file.filename}'. Allowed formats: {allowed_desc}.",
            )

        # Verify magic bytes for security
        if ext == ".pdf" and not content.startswith(b"%PDF"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Uploaded PDF file failed binary integrity verification.",
            )
        elif ext == ".png" and not content.startswith(b"\x89PNG\r\n\x1a\n"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Uploaded PNG file failed binary integrity verification.",
            )
        elif ext in [".jpg", ".jpeg"] and not content.startswith(b"\xff\xd8\xff"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Uploaded JPEG file failed binary integrity verification.",
            )
        elif ext == ".webp" and not (content.startswith(b"RIFF") and b"WEBP" in content[:16]):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Uploaded WebP file failed binary integrity verification.",
            )
        elif ext == ".svg":
            head_snippet = content[:1024].decode("utf-8", errors="ignore").lower()
            if "<svg" not in head_snippet and "<?xml" not in head_snippet:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Uploaded SVG file failed XML/SVG format verification.",
                )

        # Ensure target directory exists
        target_dir = LOGOS_DIR if is_logo else DOCUMENTS_DIR
        os.makedirs(target_dir, exist_ok=True)

        # Generate secure UUID filename to prevent path traversal
        unique_filename = f"{uuid.uuid4().hex}{ext}"
        dest_path = target_dir / unique_filename

        with open(dest_path, "wb") as f:
            f.write(content)

        folder_name = "logos" if is_logo else "documents"
        return f"uploads/{folder_name}/{unique_filename}"

    @classmethod
    async def register_recruiter(
        cls,
        recruiter_name: str,
        designation: str,
        work_email: str,
        mobile_phone: str,
        password: str,
        confirm_password: str,
        company_name: str,
        company_website: str,
        corporate_email: Optional[str],
        company_phone: Optional[str],
        primary_industry: str,
        company_size: str,
        headquarters_city_state: str,
        registered_office_address: str,
        company_description: str,
        terms_accepted: bool,
        incorporation_document: Optional[UploadFile],
        recruiter_authorization_document: Optional[UploadFile],
        company_logo: Optional[UploadFile],
        db: AsyncSession,
    ) -> RecruiterRegisterResponse:
        """
        Complete Recruiter Registration pipeline:
        1. Terms acceptance verification (HTTP 422 on failure)
        2. Recruiter contact validation & normalization
        3. Company details & fixed dropdown validation
        4. Duplicate checks for work email and mobile phone (HTTP 409)
        5. Secure file uploads (Certificate, Authorization, optional Logo)
        6. Password hashing using bcrypt
        7. Asynchronous persistence to MySQL (User + RecruiterProfile) with PENDING_APPROVAL status
        8. Return safe HTTP 201 response
        """
        # 1. Terms acceptance check
        if not terms_accepted:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="You must agree to the Terms & Conditions and Privacy Policy to proceed.",
            )

        # 2. Contact details validation
        valid_name, valid_desig, clean_email, clean_phone = cls.validate_contact_details(
            recruiter_name=recruiter_name,
            designation=designation,
            work_email=work_email,
            mobile_phone=mobile_phone,
            password=password,
            confirm_password=confirm_password,
        )

        # 3. Company details validation
        (
            clean_company_name,
            clean_website,
            clean_corp_email,
            clean_corp_phone,
            valid_industry,
            valid_size,
            valid_hq,
            clean_address,
            clean_desc,
        ) = cls.validate_company_details(
            company_name=company_name,
            company_website=company_website,
            corporate_email=corporate_email,
            company_phone=company_phone,
            primary_industry=primary_industry,
            company_size=company_size,
            headquarters_city_state=headquarters_city_state,
            registered_office_address=registered_office_address,
            company_description=company_description,
        )

        # 4. Duplicate checks
        existing_user_email = await RecruiterRepository.get_user_by_email(db, clean_email)
        existing_profile_email = await RecruiterRepository.get_profile_by_work_email(db, clean_email)
        if existing_user_email or existing_profile_email:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this work email already exists.",
            )

        existing_user_phone = await RecruiterRepository.get_user_by_phone(db, clean_phone)
        existing_profile_phone = await RecruiterRepository.get_profile_by_mobile(db, clean_phone)
        if existing_user_phone or existing_profile_phone:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this mobile phone already exists.",
            )

        # 5. File upload handling
        coi_path = await cls.save_uploaded_file(
            incorporation_document,
            is_logo=False,
            required=True,
        )
        auth_doc_path = await cls.save_uploaded_file(
            recruiter_authorization_document,
            is_logo=False,
            required=True,
        )
        logo_path = await cls.save_uploaded_file(
            company_logo,
            is_logo=True,
            required=False,
        )

        # 6. Password hashing
        hashed_pwd = hash_password(password)

        # 7. Model instantiation
        user_id = str(uuid.uuid4())
        user = User(
            id=user_id,
            email=clean_email,
            phone=clean_phone,
            hashed_password=hashed_pwd,
            role="RECRUITER",
            is_active=False,       # Inactive until Admin approval
            is_verified=False,     # Unverified until Admin review
        )

        recruiter_profile = RecruiterProfile(
            id=str(uuid.uuid4()),
            user_id=user_id,
            recruiter_name=valid_name,
            designation=valid_desig,
            work_email=clean_email,
            mobile_phone=clean_phone,
            company_name=clean_company_name,
            company_website=clean_website,
            corporate_email=clean_corp_email,
            company_phone=clean_corp_phone,
            primary_industry=valid_industry,
            company_size=valid_size,
            headquarters_city_state=valid_hq,
            registered_office_address=clean_address,
            company_description=clean_desc,
            incorporation_document_path=coi_path,
            recruiter_authorization_document_path=auth_doc_path,
            company_logo_path=logo_path,
            status=RecruiterStatus.PENDING_APPROVAL.value,
        )

        # Persist to database via repository
        await RecruiterRepository.create_recruiter(db, user, recruiter_profile)

        return RecruiterRegisterResponse(
            message="Recruiter registration submitted successfully for admin approval.",
            status=RecruiterStatus.PENDING_APPROVAL.value,
            company_name=clean_company_name,
        )
