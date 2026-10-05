"""
Candidate Profile Endpoints
GET    /api/v1/candidate/profile
PATCH  /api/v1/candidate/profile/personal
PATCH  /api/v1/candidate/profile/preferences
GET    /api/v1/candidate/profile/skills
POST   /api/v1/candidate/profile/skills
DELETE /api/v1/candidate/profile/skills/{skill_id}
POST   /api/v1/candidate/profile/resume
GET    /api/v1/candidate/profile/resume/{resume_id}/view
GET    /api/v1/candidate/profile/resume/{resume_id}/download
GET    /api/v1/candidate/profile/work-experience
POST   /api/v1/candidate/profile/work-experience
PATCH  /api/v1/candidate/profile/work-experience/{experience_id}
DELETE /api/v1/candidate/profile/work-experience/{experience_id}
GET    /api/v1/candidate/profile/education
POST   /api/v1/candidate/profile/education
PATCH  /api/v1/candidate/profile/education/{education_id}
DELETE /api/v1/candidate/profile/education/{education_id}
GET    /api/v1/candidate/profile/certifications
POST   /api/v1/candidate/profile/certifications
PATCH  /api/v1/candidate/profile/certifications/{certification_id}
DELETE /api/v1/candidate/profile/certifications/{certification_id}
GET    /api/v1/candidate/profile/projects
POST   /api/v1/candidate/profile/projects
PATCH  /api/v1/candidate/profile/projects/{project_id}
DELETE /api/v1/candidate/profile/projects/{project_id}

Authentication:  Bearer JWT (CANDIDATE role only)
Authorization:   Candidate identity derived exclusively from verified JWT bearer token.
"""
from typing import List, Optional, Dict
from fastapi import APIRouter, Depends, status, UploadFile, File, Form, Request
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_database, get_current_candidate
from app.models.user import User
from app.schemas.candidate_profile import (
    PersonalUpdate,
    PreferencesUpdate,
    SkillCreate,
    SkillItem,
    ExperienceCreate,
    ExperienceUpdate,
    ExperienceItem,
    EducationCreate,
    EducationUpdate,
    EducationItem,
    CertificationCreate,
    CertificationUpdate,
    CertificationItem,
    ProjectCreate,
    ProjectUpdate,
    ProjectItem,
    ResumeItem,
    CandidateProfileResponse,
)
from app.services.candidate_profile_service import CandidateProfileService

router = APIRouter(
    prefix="/candidate/profile",
    tags=["Candidate Profile"],
)


# ── Full Profile ───────────────────────────────────────────────────────────────

@router.get(
    "",
    response_model=CandidateProfileResponse,
    summary="Get Complete Candidate Profile",
    description="Returns the authenticated candidate's complete profile with calculated profile_completion_percentage.",
)
async def get_candidate_profile(
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_database),
) -> CandidateProfileResponse:
    return await CandidateProfileService.get_profile(db, current_user)


# ── Personal Information ───────────────────────────────────────────────────────

@router.patch(
    "/personal",
    response_model=CandidateProfileResponse,
    summary="Update Personal & Social Profile",
    description="Updates candidate headline, bio, phone, location, and social links.",
)
async def update_personal_profile(
    data: PersonalUpdate,
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_database),
) -> CandidateProfileResponse:
    return await CandidateProfileService.update_personal(db, current_user, data)


# ── Preferences ───────────────────────────────────────────────────────────────

@router.patch(
    "/preferences",
    response_model=CandidateProfileResponse,
    summary="Update Career Preferences",
    description="Updates experience, salary expectations, work mode, and preferred roles/locations.",
)
async def update_career_preferences(
    data: PreferencesUpdate,
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_database),
) -> CandidateProfileResponse:
    return await CandidateProfileService.update_preferences(db, current_user, data)


# ── Technical Skills ───────────────────────────────────────────────────────────

@router.get(
    "/skills",
    response_model=List[SkillItem],
    summary="Get Candidate Skills",
    description="Returns list of technical skills for the authenticated candidate.",
)
async def get_skills(
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_database),
) -> List[SkillItem]:
    return await CandidateProfileService.get_skills(db, current_user)


@router.post(
    "/skills",
    response_model=SkillItem,
    status_code=status.HTTP_201_CREATED,
    summary="Add Technical Skill",
    description="Adds a unique technical skill for the authenticated candidate.",
)
async def add_skill(
    data: SkillCreate,
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_database),
) -> SkillItem:
    return await CandidateProfileService.add_skill(db, current_user, data)


@router.delete(
    "/skills/{skill_id}",
    response_model=Dict[str, str],
    summary="Delete Technical Skill",
    description="Removes a skill belonging to the authenticated candidate.",
)
async def delete_skill(
    skill_id: str,
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_database),
) -> Dict[str, str]:
    return await CandidateProfileService.delete_skill(db, current_user, skill_id)


# ── Resume ─────────────────────────────────────────────────────────────────────

@router.post(
    "/resume",
    response_model=ResumeItem,
    status_code=status.HTTP_201_CREATED,
    summary="Upload or Replace Resume",
    description="Uploads a new resume file or registers new resume metadata. Deactivates previous resume.",
)
async def upload_resume(
    request: Request,
    file: Optional[UploadFile] = File(None),
    file_name: Optional[str] = Form(None),
    file_size: Optional[str] = Form(None),
    file_type: Optional[str] = Form(None),
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_database),
) -> ResumeItem:
    # Handle JSON body fallback if client sent application/json
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        try:
            body = await request.json()
            file_name = body.get("fileName") or body.get("file_name") or file_name
            file_size = body.get("fileSize") or body.get("file_size") or file_size
            file_type = body.get("fileType") or body.get("file_type") or file_type
        except Exception:
            pass

    return await CandidateProfileService.save_resume_file(
        db,
        current_user,
        file=file,
        file_name=file_name,
        file_size=file_size,
        file_type=file_type,
    )


@router.get(
    "/resume/{resume_id}/view",
    summary="View Candidate Resume",
    description="Streams resume file for viewing in-browser. Verifies candidate ownership.",
)
async def view_resume(
    resume_id: str,
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_database),
):
    file_path, filename, media_type = await CandidateProfileService.get_resume_for_view_or_download(
        db, current_user, resume_id
    )
    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=filename,
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@router.get(
    "/resume/{resume_id}/download",
    summary="Download Candidate Resume",
    description="Downloads resume file as attachment. Verifies candidate ownership.",
)
async def download_resume(
    resume_id: str,
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_database),
):
    file_path, filename, media_type = await CandidateProfileService.get_resume_for_view_or_download(
        db, current_user, resume_id
    )
    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=filename,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Work Experience ────────────────────────────────────────────────────────────

@router.get(
    "/work-experience",
    response_model=List[ExperienceItem],
    summary="Get Work Experiences",
    description="Returns all work experience records for authenticated candidate.",
)
async def get_work_experiences(
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_database),
) -> List[ExperienceItem]:
    return await CandidateProfileService.get_experiences(db, current_user)


@router.post(
    "/work-experience",
    response_model=ExperienceItem,
    status_code=status.HTTP_201_CREATED,
    summary="Add Work Experience",
    description="Creates a work experience record for authenticated candidate.",
)
async def add_work_experience(
    data: ExperienceCreate,
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_database),
) -> ExperienceItem:
    return await CandidateProfileService.add_experience(db, current_user, data)


@router.patch(
    "/work-experience/{experience_id}",
    response_model=ExperienceItem,
    summary="Update Work Experience",
    description="Updates a work experience record belonging to authenticated candidate.",
)
async def update_work_experience(
    experience_id: str,
    data: ExperienceUpdate,
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_database),
) -> ExperienceItem:
    return await CandidateProfileService.update_experience(db, current_user, experience_id, data)


@router.delete(
    "/work-experience/{experience_id}",
    response_model=Dict[str, str],
    summary="Delete Work Experience",
    description="Deletes a work experience record belonging to authenticated candidate.",
)
async def delete_work_experience(
    experience_id: str,
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_database),
) -> Dict[str, str]:
    return await CandidateProfileService.delete_experience(db, current_user, experience_id)


# ── Education ──────────────────────────────────────────────────────────────────

@router.get(
    "/education",
    response_model=List[EducationItem],
    summary="Get Educations",
    description="Returns all education records for authenticated candidate.",
)
async def get_educations(
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_database),
) -> List[EducationItem]:
    return await CandidateProfileService.get_educations(db, current_user)


@router.post(
    "/education",
    response_model=EducationItem,
    status_code=status.HTTP_201_CREATED,
    summary="Add Education",
    description="Creates an education record for authenticated candidate.",
)
async def add_education(
    data: EducationCreate,
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_database),
) -> EducationItem:
    return await CandidateProfileService.add_education(db, current_user, data)


@router.patch(
    "/education/{education_id}",
    response_model=EducationItem,
    summary="Update Education",
    description="Updates an education record belonging to authenticated candidate.",
)
async def update_education(
    education_id: str,
    data: EducationUpdate,
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_database),
) -> EducationItem:
    return await CandidateProfileService.update_education(db, current_user, education_id, data)


@router.delete(
    "/education/{education_id}",
    response_model=Dict[str, str],
    summary="Delete Education",
    description="Deletes an education record belonging to authenticated candidate.",
)
async def delete_education(
    education_id: str,
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_database),
) -> Dict[str, str]:
    return await CandidateProfileService.delete_education(db, current_user, education_id)


# ── Certifications ─────────────────────────────────────────────────────────────

@router.get(
    "/certifications",
    response_model=List[CertificationItem],
    summary="Get Certifications",
    description="Returns all certification records for authenticated candidate.",
)
async def get_certifications(
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_database),
) -> List[CertificationItem]:
    return await CandidateProfileService.get_certifications(db, current_user)


@router.post(
    "/certifications",
    response_model=CertificationItem,
    status_code=status.HTTP_201_CREATED,
    summary="Add Certification",
    description="Creates a certification record for authenticated candidate.",
)
async def add_certification(
    data: CertificationCreate,
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_database),
) -> CertificationItem:
    return await CandidateProfileService.add_certification(db, current_user, data)


@router.patch(
    "/certifications/{certification_id}",
    response_model=CertificationItem,
    summary="Update Certification",
    description="Updates a certification record belonging to authenticated candidate.",
)
async def update_certification(
    certification_id: str,
    data: CertificationUpdate,
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_database),
) -> CertificationItem:
    return await CandidateProfileService.update_certification(db, current_user, certification_id, data)


@router.delete(
    "/certifications/{certification_id}",
    response_model=Dict[str, str],
    summary="Delete Certification",
    description="Deletes a certification record belonging to authenticated candidate.",
)
async def delete_certification(
    certification_id: str,
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_database),
) -> Dict[str, str]:
    return await CandidateProfileService.delete_certification(db, current_user, certification_id)


# ── Featured Projects ──────────────────────────────────────────────────────────

@router.get(
    "/projects",
    response_model=List[ProjectItem],
    summary="Get Projects",
    description="Returns all project records for authenticated candidate.",
)
async def get_projects(
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_database),
) -> List[ProjectItem]:
    return await CandidateProfileService.get_projects(db, current_user)


@router.post(
    "/projects",
    response_model=ProjectItem,
    status_code=status.HTTP_201_CREATED,
    summary="Add Project",
    description="Creates a project record for authenticated candidate.",
)
async def add_project(
    data: ProjectCreate,
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_database),
) -> ProjectItem:
    return await CandidateProfileService.add_project(db, current_user, data)


@router.patch(
    "/projects/{project_id}",
    response_model=ProjectItem,
    summary="Update Project",
    description="Updates a project record belonging to authenticated candidate.",
)
async def update_project(
    project_id: str,
    data: ProjectUpdate,
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_database),
) -> ProjectItem:
    return await CandidateProfileService.update_project(db, current_user, project_id, data)


@router.delete(
    "/projects/{project_id}",
    response_model=Dict[str, str],
    summary="Delete Project",
    description="Deletes a project record belonging to authenticated candidate.",
)
async def delete_project(
    project_id: str,
    current_user: User = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_database),
) -> Dict[str, str]:
    return await CandidateProfileService.delete_project(db, current_user, project_id)
