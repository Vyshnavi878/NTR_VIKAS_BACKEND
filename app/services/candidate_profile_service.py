import os
import json
import uuid
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime, timezone
from fastapi import HTTPException, status, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.candidate import CandidateProfile
from app.models.candidate_profile_details import (
    CandidateSkill,
    CandidateExperience,
    CandidateEducation,
    CandidateCertification,
    CandidateProject,
    CandidateResume,
)
from app.repositories.candidate_profile_repository import CandidateProfileRepository
from app.services.candidate_dashboard_service import _calculate_profile_strength
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

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads", "resumes")
os.makedirs(UPLOAD_DIR, exist_ok=True)


def calculate_completion_percentage(
    profile: CandidateProfile,
    user_email: str,
    skills_count: int,
    experience_count: int,
    education_count: int,
    has_active_resume: bool,
) -> int:
    score = 0
    # 1. Five Signup/Personal fields: 5% each = 25% total
    if profile.name and profile.name.strip():
        score += 5
    if user_email and user_email.strip():
        score += 5
    if profile.phone and profile.phone.strip():
        score += 5
    if profile.location and profile.location.strip():
        score += 5
    if profile.aadhaar_number and profile.aadhaar_number.strip():
        score += 5

    # 2. Headline & Bio: 10% each = 20% total
    if profile.headline and len(profile.headline.strip()) >= 3:
        score += 10
    if profile.bio and len(profile.bio.strip()) >= 10:
        score += 10

    # 3. Resume: 20%
    if has_active_resume:
        score += 20

    # 4. Skills: 15% (at least 3 skills)
    if skills_count >= 3:
        score += 15

    # 5. Work Experience: 10%
    if experience_count > 0 or (
        profile.total_experience
        and profile.total_experience.lower() not in ("fresher", "fresher (0-1 yr)")
    ):
        score += 10

    # 6. Education: 10%
    if education_count > 0 or (profile.qualification_level and profile.qualification_level.strip()):
        score += 10

    return min(score, 100)


def _parse_list_field(val: Any) -> List[str]:
    if not val:
        return []
    if isinstance(val, list):
        return [str(v).strip() for v in val if str(v).strip()]
    if isinstance(val, str):
        try:
            parsed = json.loads(val)
            if isinstance(parsed, list):
                return [str(v).strip() for v in parsed if str(v).strip()]
        except Exception:
            return [v.strip() for v in val.split(",") if v.strip()]
    return []


class CandidateProfileService:
    @staticmethod
    async def get_or_create_candidate_profile(
        db: AsyncSession, current_user: User
    ) -> CandidateProfile:
        """Fetch candidate profile or raise 404."""
        profile = await CandidateProfileRepository.get_profile_by_user_id(db, current_user.id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Candidate profile not found.",
            )
        return profile

    @staticmethod
    async def serialize_profile(
        db: AsyncSession, profile: CandidateProfile, current_user: User
    ) -> CandidateProfileResponse:
        skills = profile.skills or []
        experiences = profile.experiences or []
        educations = profile.educations or []
        certifications = profile.certifications or []
        projects = profile.projects or []
        resumes = [r for r in (profile.resumes or []) if r.is_active]
        active_resume = resumes[0] if resumes else None

        strength = _calculate_profile_strength(profile)
        completion = strength.percentage


        # Update stored completion if changed
        if profile.profile_completion != completion:
            profile.profile_completion = completion
            await db.commit()


        preferred_roles = _parse_list_field(profile.preferred_job_roles)
        preferred_locations = _parse_list_field(profile.preferred_locations)

        skill_names = [s.skill_name for s in skills]
        skill_items = [
            SkillItem(id=s.id, skill_name=s.skill_name, name=s.skill_name) for s in skills
        ]

        resume_item = None
        if active_resume:
            date_str = (
                active_resume.created_at.strftime("%d %b %Y")
                if active_resume.created_at
                else "Recent"
            )
            resume_item = ResumeItem(
                id=active_resume.id,
                file_name=active_resume.file_name,
                fileName=active_resume.file_name,
                file_size=active_resume.file_size or "1.0 MB",
                fileSize=active_resume.file_size or "1.0 MB",
                file_type=active_resume.file_type or "PDF Document",
                fileType=active_resume.file_type or "PDF Document",
                uploaded_at=date_str,
                uploadedDate=date_str,
            )

        exp_items = [
            ExperienceItem(
                id=e.id,
                role=e.role,
                company=e.company,
                location=e.location,
                duration=e.duration,
                description=e.description,
            )
            for e in experiences
        ]

        edu_items = [
            EducationItem(
                id=ed.id,
                degree=ed.degree,
                institution=ed.institution,
                duration=ed.duration,
                score=ed.score,
            )
            for ed in educations
        ]

        cert_items = [
            CertificationItem(
                id=c.id,
                name=c.name,
                issuer=c.issuer,
                year=c.year,
            )
            for c in certifications
        ]

        proj_items = [
            ProjectItem(
                id=p.id,
                title=p.title,
                tech=p.tech,
                description=p.description,
                link=p.link,
            )
            for p in projects
        ]

        skills_preferences = {
            "skills": skill_names,
            "preferredRoles": preferred_roles,
            "preferredLocations": preferred_locations,
            "expectedSalary": profile.expected_salary or "",
            "currentSalary": profile.current_salary or "",
            "workMode": profile.work_mode or "Hybrid",
            "jobType": profile.employment_type or "Full-time",
            "experience": profile.total_experience or "Fresher (0-1 yr)",
            "educationLevel": profile.qualification_level or "",
        }

        display_location = profile.location or (
            f"{profile.mandal}, {profile.district}" if profile.mandal else profile.district
        )

        return CandidateProfileResponse(
            id=profile.id,
            name=profile.name,
            fullName=profile.name,
            email=current_user.email,
            phone=profile.phone,
            district=profile.district,
            mandal=profile.mandal,
            village=profile.village,
            qualification_level=profile.qualification_level,
            headline=profile.headline,
            professional_title=profile.headline,
            bio=profile.bio,
            professional_summary=profile.bio,
            location=display_location,
            linkedin=profile.linkedin_url,
            linkedin_url=profile.linkedin_url,
            github=profile.github_url,
            github_url=profile.github_url,
            portfolio=profile.portfolio_url,
            portfolio_url=profile.portfolio_url,
            avatar=profile.avatar,
            profileImage=profile.avatar,
            profile_completion_percentage=completion,
            profileCompletion=completion,
            skillsPreferences=skills_preferences,
            skills=skill_names,
            skillsList=skill_items,
            resume=resume_item,
            experienceList=exp_items,
            educationList=edu_items,
            certificationsList=cert_items,
            projectsList=proj_items,
        )

    @staticmethod
    async def get_profile(
        db: AsyncSession, current_user: User
    ) -> CandidateProfileResponse:
        profile = await CandidateProfileService.get_or_create_candidate_profile(db, current_user)
        return await CandidateProfileService.serialize_profile(db, profile, current_user)

    @staticmethod
    async def update_personal(
        db: AsyncSession, current_user: User, data: PersonalUpdate
    ) -> CandidateProfileResponse:
        profile = await CandidateProfileService.get_or_create_candidate_profile(db, current_user)

        name = data.name or data.fullName
        if name and name.strip():
            profile.name = name.strip()

        headline = data.headline if data.headline is not None else data.professional_title
        if headline is not None:
            profile.headline = headline.strip()

        bio = data.bio if data.bio is not None else data.professional_summary
        if bio is not None:
            profile.bio = bio.strip()

        if data.phone is not None:
            profile.phone = data.phone.strip()

        if data.location is not None:
            profile.location = data.location.strip()

        linkedin = data.linkedin if data.linkedin is not None else data.linkedin_url
        if linkedin is not None:
            profile.linkedin_url = linkedin.strip()

        github = data.github if data.github is not None else data.github_url
        if github is not None:
            profile.github_url = github.strip()

        portfolio = data.portfolio if data.portfolio is not None else data.portfolio_url
        if portfolio is not None:
            profile.portfolio_url = portfolio.strip()

        if data.avatar is not None:
            profile.avatar = data.avatar

        saved_profile = await CandidateProfileRepository.save_profile(db, profile)
        return await CandidateProfileService.serialize_profile(db, saved_profile, current_user)

    @staticmethod
    async def update_preferences(
        db: AsyncSession, current_user: User, data: PreferencesUpdate
    ) -> CandidateProfileResponse:
        profile = await CandidateProfileService.get_or_create_candidate_profile(db, current_user)

        exp = data.total_experience if data.total_experience is not None else data.experience
        if exp is not None:
            profile.total_experience = exp.strip()

        curr_sal = data.current_salary if data.current_salary is not None else data.currentSalary
        if curr_sal is not None:
            profile.current_salary = curr_sal.strip()

        if data.expected_salary_min is not None:
            profile.expected_salary_min = str(data.expected_salary_min).strip()
        if data.expected_salary_max is not None:
            profile.expected_salary_max = str(data.expected_salary_max).strip()

        exp_sal = data.expected_salary if data.expected_salary is not None else data.expectedSalary
        if exp_sal is not None:
            profile.expected_salary = exp_sal.strip()
        elif profile.expected_salary_min and profile.expected_salary_max:
            profile.expected_salary = f"{profile.expected_salary_min} - {profile.expected_salary_max}"

        wm = data.work_mode if data.work_mode is not None else data.workMode
        if wm is not None:
            profile.work_mode = wm.strip()

        emp_type = data.employment_type if data.employment_type is not None else data.jobType
        if emp_type is not None:
            profile.employment_type = emp_type.strip()

        roles = data.preferred_job_roles if data.preferred_job_roles is not None else data.preferredRoles
        if roles is not None:
            profile.preferred_job_roles = json.dumps(_parse_list_field(roles))

        locations = data.preferred_locations if data.preferred_locations is not None else data.preferredLocations
        if locations is not None:
            profile.preferred_locations = json.dumps(_parse_list_field(locations))

        saved_profile = await CandidateProfileRepository.save_profile(db, profile)
        return await CandidateProfileService.serialize_profile(db, saved_profile, current_user)

    # ── Skills ─────────────────────────────────────────────────────────────────

    @staticmethod
    async def get_skills(
        db: AsyncSession, current_user: User
    ) -> List[SkillItem]:
        profile = await CandidateProfileService.get_or_create_candidate_profile(db, current_user)
        skills = await CandidateProfileRepository.get_skills(db, profile.id)
        return [SkillItem(id=s.id, skill_name=s.skill_name, name=s.skill_name) for s in skills]

    @staticmethod
    async def add_skill(
        db: AsyncSession, current_user: User, data: SkillCreate
    ) -> SkillItem:
        profile = await CandidateProfileService.get_or_create_candidate_profile(db, current_user)
        name = data.get_name()
        if not name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Skill name cannot be empty.",
            )

        existing = await CandidateProfileRepository.get_skill_by_name(db, profile.id, name)
        if existing:
            return SkillItem(id=existing.id, skill_name=existing.skill_name, name=existing.skill_name)

        new_skill = CandidateSkill(
            id=str(uuid.uuid4()),
            candidate_profile_id=profile.id,
            skill_name=name,
        )
        created = await CandidateProfileRepository.add_skill(db, new_skill)
        return SkillItem(id=created.id, skill_name=created.skill_name, name=created.skill_name)

    @staticmethod
    async def delete_skill(
        db: AsyncSession, current_user: User, skill_id: str
    ) -> Dict[str, str]:
        profile = await CandidateProfileService.get_or_create_candidate_profile(db, current_user)
        skill = await CandidateProfileRepository.get_skill_by_id(db, profile.id, skill_id)
        if not skill:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Skill not found or does not belong to candidate.",
            )
        await CandidateProfileRepository.delete_skill(db, skill)
        return {"detail": "Skill removed successfully."}

    # ── Resume ─────────────────────────────────────────────────────────────────

    @staticmethod
    async def save_resume_file(
        db: AsyncSession,
        current_user: User,
        file: Optional[UploadFile] = None,
        file_name: Optional[str] = None,
        file_size: Optional[str] = None,
        file_type: Optional[str] = None,
    ) -> ResumeItem:
        profile = await CandidateProfileService.get_or_create_candidate_profile(db, current_user)
        resume_id = str(uuid.uuid4())

        if file:
            filename = file.filename or f"resume_{resume_id}.pdf"
            # Sanitize and create unique path
            disk_filename = f"{profile.id}_{resume_id}_{filename}"
            file_path = os.path.join(UPLOAD_DIR, disk_filename)

            contents = await file.read()
            with open(file_path, "wb") as f:
                f.write(contents)

            size_mb = f"{(len(contents) / (1024 * 1024)):.1f} MB"
            mime_type = file.content_type or ("PDF Document" if filename.endswith(".pdf") else "Word Document")
        else:
            filename = file_name or "Resume.pdf"
            file_path = os.path.join(UPLOAD_DIR, f"{profile.id}_{resume_id}_{filename}")
            # Ensure an actual placeholder file exists on disk
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(f"Candidate Resume: {profile.name}\nEmail: {current_user.email}\n")
            size_mb = file_size or "1.2 MB"
            mime_type = file_type or ("PDF Document" if filename.endswith(".pdf") else "Word Document")

        new_resume = CandidateResume(
            id=resume_id,
            candidate_profile_id=profile.id,
            file_name=filename,
            file_path=file_path,
            file_size=size_mb,
            file_type=mime_type,
            is_active=True,
        )
        created = await CandidateProfileRepository.add_resume(db, new_resume)
        date_str = created.created_at.strftime("%d %b %Y") if created.created_at else "Today"

        return ResumeItem(
            id=created.id,
            file_name=created.file_name,
            fileName=created.file_name,
            file_size=created.file_size,
            fileSize=created.file_size,
            file_type=created.file_type,
            fileType=created.file_type,
            uploaded_at=date_str,
            uploadedDate=date_str,
        )

    @staticmethod
    async def get_resume_for_view_or_download(
        db: AsyncSession, current_user: User, resume_id: str
    ) -> Tuple[str, str, str]:
        """
        Validates resume ownership and returns (file_path, filename, media_type).
        Candidate A cannot access Candidate B's resume.
        """
        profile = await CandidateProfileService.get_or_create_candidate_profile(db, current_user)
        resume = await CandidateProfileRepository.get_resume_by_id(db, profile.id, resume_id)
        if not resume:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resume not found or does not belong to you.",
            )

        if not os.path.exists(resume.file_path):
            # Create a mock file if path missing on disk
            with open(resume.file_path, "w", encoding="utf-8") as f:
                f.write(f"Candidate Resume: {profile.name}\nFile: {resume.file_name}\n")

        media_type = "application/pdf" if resume.file_name.endswith(".pdf") else "application/octet-stream"
        return resume.file_path, resume.file_name, media_type

    # ── Work Experience ────────────────────────────────────────────────────────

    @staticmethod
    async def get_experiences(
        db: AsyncSession, current_user: User
    ) -> List[ExperienceItem]:
        profile = await CandidateProfileService.get_or_create_candidate_profile(db, current_user)
        exps = await CandidateProfileRepository.get_experiences(db, profile.id)
        return [
            ExperienceItem(
                id=e.id,
                role=e.role,
                company=e.company,
                location=e.location,
                duration=e.duration,
                description=e.description,
            )
            for e in exps
        ]

    @staticmethod
    async def add_experience(
        db: AsyncSession, current_user: User, data: ExperienceCreate
    ) -> ExperienceItem:
        profile = await CandidateProfileService.get_or_create_candidate_profile(db, current_user)
        new_exp = CandidateExperience(
            id=str(uuid.uuid4()),
            candidate_profile_id=profile.id,
            role=data.role.strip(),
            company=data.company.strip(),
            location=data.location.strip() if data.location else None,
            duration=data.duration.strip() if data.duration else None,
            description=data.description.strip() if data.description else None,
        )
        created = await CandidateProfileRepository.add_experience(db, new_exp)
        return ExperienceItem(
            id=created.id,
            role=created.role,
            company=created.company,
            location=created.location,
            duration=created.duration,
            description=created.description,
        )

    @staticmethod
    async def update_experience(
        db: AsyncSession, current_user: User, exp_id: str, data: ExperienceUpdate
    ) -> ExperienceItem:
        profile = await CandidateProfileService.get_or_create_candidate_profile(db, current_user)
        exp = await CandidateProfileRepository.get_experience_by_id(db, profile.id, exp_id)
        if not exp:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Work experience record not found.",
            )
        if data.role is not None:
            exp.role = data.role.strip()
        if data.company is not None:
            exp.company = data.company.strip()
        if data.location is not None:
            exp.location = data.location.strip()
        if data.duration is not None:
            exp.duration = data.duration.strip()
        if data.description is not None:
            exp.description = data.description.strip()

        saved = await CandidateProfileRepository.save_experience(db, exp)
        return ExperienceItem(
            id=saved.id,
            role=saved.role,
            company=saved.company,
            location=saved.location,
            duration=saved.duration,
            description=saved.description,
        )

    @staticmethod
    async def delete_experience(
        db: AsyncSession, current_user: User, exp_id: str
    ) -> Dict[str, str]:
        profile = await CandidateProfileService.get_or_create_candidate_profile(db, current_user)
        exp = await CandidateProfileRepository.get_experience_by_id(db, profile.id, exp_id)
        if not exp:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Work experience record not found.",
            )
        await CandidateProfileRepository.delete_experience(db, exp)
        return {"detail": "Work experience removed successfully."}

    # ── Education ──────────────────────────────────────────────────────────────

    @staticmethod
    async def get_educations(
        db: AsyncSession, current_user: User
    ) -> List[EducationItem]:
        profile = await CandidateProfileService.get_or_create_candidate_profile(db, current_user)
        edus = await CandidateProfileRepository.get_educations(db, profile.id)
        return [
            EducationItem(
                id=ed.id,
                degree=ed.degree,
                institution=ed.institution,
                duration=ed.duration,
                score=ed.score,
            )
            for ed in edus
        ]

    @staticmethod
    async def add_education(
        db: AsyncSession, current_user: User, data: EducationCreate
    ) -> EducationItem:
        profile = await CandidateProfileService.get_or_create_candidate_profile(db, current_user)
        new_edu = CandidateEducation(
            id=str(uuid.uuid4()),
            candidate_profile_id=profile.id,
            degree=data.degree.strip(),
            institution=data.institution.strip(),
            duration=data.duration.strip() if data.duration else None,
            score=data.score.strip() if data.score else None,
        )
        created = await CandidateProfileRepository.add_education(db, new_edu)
        return EducationItem(
            id=created.id,
            degree=created.degree,
            institution=created.institution,
            duration=created.duration,
            score=created.score,
        )

    @staticmethod
    async def update_education(
        db: AsyncSession, current_user: User, edu_id: str, data: EducationUpdate
    ) -> EducationItem:
        profile = await CandidateProfileService.get_or_create_candidate_profile(db, current_user)
        edu = await CandidateProfileRepository.get_education_by_id(db, profile.id, edu_id)
        if not edu:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Education record not found.",
            )
        if data.degree is not None:
            edu.degree = data.degree.strip()
        if data.institution is not None:
            edu.institution = data.institution.strip()
        if data.duration is not None:
            edu.duration = data.duration.strip()
        if data.score is not None:
            edu.score = data.score.strip()

        saved = await CandidateProfileRepository.save_education(db, edu)
        return EducationItem(
            id=saved.id,
            degree=saved.degree,
            institution=saved.institution,
            duration=saved.duration,
            score=saved.score,
        )

    @staticmethod
    async def delete_education(
        db: AsyncSession, current_user: User, edu_id: str
    ) -> Dict[str, str]:
        profile = await CandidateProfileService.get_or_create_candidate_profile(db, current_user)
        edu = await CandidateProfileRepository.get_education_by_id(db, profile.id, edu_id)
        if not edu:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Education record not found.",
            )
        await CandidateProfileRepository.delete_education(db, edu)
        return {"detail": "Education record removed successfully."}

    # ── Certifications ─────────────────────────────────────────────────────────

    @staticmethod
    async def get_certifications(
        db: AsyncSession, current_user: User
    ) -> List[CertificationItem]:
        profile = await CandidateProfileService.get_or_create_candidate_profile(db, current_user)
        certs = await CandidateProfileRepository.get_certifications(db, profile.id)
        return [
            CertificationItem(
                id=c.id,
                name=c.name,
                issuer=c.issuer,
                year=c.year,
            )
            for c in certs
        ]

    @staticmethod
    async def add_certification(
        db: AsyncSession, current_user: User, data: CertificationCreate
    ) -> CertificationItem:
        profile = await CandidateProfileService.get_or_create_candidate_profile(db, current_user)
        new_cert = CandidateCertification(
            id=str(uuid.uuid4()),
            candidate_profile_id=profile.id,
            name=data.name.strip(),
            issuer=data.issuer.strip(),
            year=data.year.strip() if data.year else None,
        )
        created = await CandidateProfileRepository.add_certification(db, new_cert)
        return CertificationItem(
            id=created.id,
            name=created.name,
            issuer=created.issuer,
            year=created.year,
        )

    @staticmethod
    async def update_certification(
        db: AsyncSession, current_user: User, cert_id: str, data: CertificationUpdate
    ) -> CertificationItem:
        profile = await CandidateProfileService.get_or_create_candidate_profile(db, current_user)
        cert = await CandidateProfileRepository.get_certification_by_id(db, profile.id, cert_id)
        if not cert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Certification record not found.",
            )
        if data.name is not None:
            cert.name = data.name.strip()
        if data.issuer is not None:
            cert.issuer = data.issuer.strip()
        if data.year is not None:
            cert.year = data.year.strip()

        saved = await CandidateProfileRepository.save_certification(db, cert)
        return CertificationItem(
            id=saved.id,
            name=saved.name,
            issuer=saved.issuer,
            year=saved.year,
        )

    @staticmethod
    async def delete_certification(
        db: AsyncSession, current_user: User, cert_id: str
    ) -> Dict[str, str]:
        profile = await CandidateProfileService.get_or_create_candidate_profile(db, current_user)
        cert = await CandidateProfileRepository.get_certification_by_id(db, profile.id, cert_id)
        if not cert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Certification record not found.",
            )
        await CandidateProfileRepository.delete_certification(db, cert)
        return {"detail": "Certification record removed successfully."}

    # ── Projects ───────────────────────────────────────────────────────────────

    @staticmethod
    async def get_projects(
        db: AsyncSession, current_user: User
    ) -> List[ProjectItem]:
        profile = await CandidateProfileService.get_or_create_candidate_profile(db, current_user)
        projs = await CandidateProfileRepository.get_projects(db, profile.id)
        return [
            ProjectItem(
                id=p.id,
                title=p.title,
                tech=p.tech,
                description=p.description,
                link=p.link,
            )
            for p in projs
        ]

    @staticmethod
    async def add_project(
        db: AsyncSession, current_user: User, data: ProjectCreate
    ) -> ProjectItem:
        profile = await CandidateProfileService.get_or_create_candidate_profile(db, current_user)
        new_proj = CandidateProject(
            id=str(uuid.uuid4()),
            candidate_profile_id=profile.id,
            title=data.title.strip(),
            tech=data.tech.strip() if data.tech else None,
            description=data.description.strip() if data.description else None,
            link=data.link.strip() if data.link else None,
        )
        created = await CandidateProfileRepository.add_project(db, new_proj)
        return ProjectItem(
            id=created.id,
            title=created.title,
            tech=created.tech,
            description=created.description,
            link=created.link,
        )

    @staticmethod
    async def update_project(
        db: AsyncSession, current_user: User, proj_id: str, data: ProjectUpdate
    ) -> ProjectItem:
        profile = await CandidateProfileService.get_or_create_candidate_profile(db, current_user)
        proj = await CandidateProfileRepository.get_project_by_id(db, profile.id, proj_id)
        if not proj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project record not found.",
            )
        if data.title is not None:
            proj.title = data.title.strip()
        if data.tech is not None:
            proj.tech = data.tech.strip()
        if data.description is not None:
            proj.description = data.description.strip()
        if data.link is not None:
            proj.link = data.link.strip()

        saved = await CandidateProfileRepository.save_project(db, proj)
        return ProjectItem(
            id=saved.id,
            title=saved.title,
            tech=saved.tech,
            description=saved.description,
            link=saved.link,
        )

    @staticmethod
    async def delete_project(
        db: AsyncSession, current_user: User, proj_id: str
    ) -> Dict[str, str]:
        profile = await CandidateProfileService.get_or_create_candidate_profile(db, current_user)
        proj = await CandidateProfileRepository.get_project_by_id(db, profile.id, proj_id)
        if not proj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project record not found.",
            )
        await CandidateProfileRepository.delete_project(db, proj)
        return {"detail": "Project record removed successfully."}
