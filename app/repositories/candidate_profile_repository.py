import uuid
from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate import CandidateProfile
from app.models.candidate_profile_details import (
    CandidateSkill,
    CandidateExperience,
    CandidateEducation,
    CandidateCertification,
    CandidateProject,
    CandidateResume,
)


class CandidateProfileRepository:
    @staticmethod
    async def get_profile_by_user_id(
        db: AsyncSession, user_id: str
    ) -> Optional[CandidateProfile]:
        """Fetch candidate profile with all child tables eagerly loaded."""
        stmt = (
            select(CandidateProfile)
            .where(CandidateProfile.user_id == user_id)
            .options(
                selectinload(CandidateProfile.skills),
                selectinload(CandidateProfile.experiences),
                selectinload(CandidateProfile.educations),
                selectinload(CandidateProfile.certifications),
                selectinload(CandidateProfile.projects),
                selectinload(CandidateProfile.resumes),
            )
        )
        res = await db.execute(stmt)
        return res.scalars().first()

    @staticmethod
    async def get_profile_by_id(
        db: AsyncSession, profile_id: str
    ) -> Optional[CandidateProfile]:
        """Fetch candidate profile by its primary key ID."""
        stmt = (
            select(CandidateProfile)
            .where(CandidateProfile.id == profile_id)
            .options(
                selectinload(CandidateProfile.skills),
                selectinload(CandidateProfile.experiences),
                selectinload(CandidateProfile.educations),
                selectinload(CandidateProfile.certifications),
                selectinload(CandidateProfile.projects),
                selectinload(CandidateProfile.resumes),
            )
        )
        res = await db.execute(stmt)
        return res.scalars().first()

    @staticmethod
    async def save_profile(
        db: AsyncSession, profile: CandidateProfile
    ) -> CandidateProfile:
        profile.updated_at = datetime.now(timezone.utc)
        db.add(profile)
        await db.commit()
        reloaded = await CandidateProfileRepository.get_profile_by_id(db, profile.id)
        return reloaded or profile


    # ── Skills ─────────────────────────────────────────────────────────────────

    @staticmethod
    async def get_skills(
        db: AsyncSession, profile_id: str
    ) -> List[CandidateSkill]:
        stmt = (
            select(CandidateSkill)
            .where(CandidateSkill.candidate_profile_id == profile_id)
            .order_by(CandidateSkill.created_at.asc())
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())

    @staticmethod
    async def get_skill_by_name(
        db: AsyncSession, profile_id: str, skill_name: str
    ) -> Optional[CandidateSkill]:
        stmt = select(CandidateSkill).where(
            CandidateSkill.candidate_profile_id == profile_id,
            CandidateSkill.skill_name.ilike(skill_name.strip()),
        )
        res = await db.execute(stmt)
        return res.scalars().first()

    @staticmethod
    async def get_skill_by_id(
        db: AsyncSession, profile_id: str, skill_id: str
    ) -> Optional[CandidateSkill]:
        stmt = select(CandidateSkill).where(
            CandidateSkill.candidate_profile_id == profile_id,
            CandidateSkill.id == skill_id,
        )
        res = await db.execute(stmt)
        return res.scalars().first()

    @staticmethod
    async def add_skill(
        db: AsyncSession, skill: CandidateSkill
    ) -> CandidateSkill:
        db.add(skill)
        await db.commit()
        await db.refresh(skill)
        return skill

    @staticmethod
    async def delete_skill(db: AsyncSession, skill: CandidateSkill) -> None:
        await db.delete(skill)
        await db.commit()

    # ── Work Experience ────────────────────────────────────────────────────────

    @staticmethod
    async def get_experiences(
        db: AsyncSession, profile_id: str
    ) -> List[CandidateExperience]:
        stmt = (
            select(CandidateExperience)
            .where(CandidateExperience.candidate_profile_id == profile_id)
            .order_by(CandidateExperience.created_at.desc())
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())

    @staticmethod
    async def get_experience_by_id(
        db: AsyncSession, profile_id: str, exp_id: str
    ) -> Optional[CandidateExperience]:
        stmt = select(CandidateExperience).where(
            CandidateExperience.candidate_profile_id == profile_id,
            CandidateExperience.id == exp_id,
        )
        res = await db.execute(stmt)
        return res.scalars().first()

    @staticmethod
    async def add_experience(
        db: AsyncSession, exp: CandidateExperience
    ) -> CandidateExperience:
        db.add(exp)
        await db.commit()
        await db.refresh(exp)
        return exp

    @staticmethod
    async def save_experience(
        db: AsyncSession, exp: CandidateExperience
    ) -> CandidateExperience:
        exp.updated_at = datetime.now(timezone.utc)
        db.add(exp)
        await db.commit()
        await db.refresh(exp)
        return exp

    @staticmethod
    async def delete_experience(
        db: AsyncSession, exp: CandidateExperience
    ) -> None:
        await db.delete(exp)
        await db.commit()

    # ── Education ──────────────────────────────────────────────────────────────

    @staticmethod
    async def get_educations(
        db: AsyncSession, profile_id: str
    ) -> List[CandidateEducation]:
        stmt = (
            select(CandidateEducation)
            .where(CandidateEducation.candidate_profile_id == profile_id)
            .order_by(CandidateEducation.created_at.desc())
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())

    @staticmethod
    async def get_education_by_id(
        db: AsyncSession, profile_id: str, edu_id: str
    ) -> Optional[CandidateEducation]:
        stmt = select(CandidateEducation).where(
            CandidateEducation.candidate_profile_id == profile_id,
            CandidateEducation.id == edu_id,
        )
        res = await db.execute(stmt)
        return res.scalars().first()

    @staticmethod
    async def add_education(
        db: AsyncSession, edu: CandidateEducation
    ) -> CandidateEducation:
        db.add(edu)
        await db.commit()
        await db.refresh(edu)
        return edu

    @staticmethod
    async def save_education(
        db: AsyncSession, edu: CandidateEducation
    ) -> CandidateEducation:
        edu.updated_at = datetime.now(timezone.utc)
        db.add(edu)
        await db.commit()
        await db.refresh(edu)
        return edu

    @staticmethod
    async def delete_education(
        db: AsyncSession, edu: CandidateEducation
    ) -> None:
        await db.delete(edu)
        await db.commit()

    # ── Certifications ─────────────────────────────────────────────────────────

    @staticmethod
    async def get_certifications(
        db: AsyncSession, profile_id: str
    ) -> List[CandidateCertification]:
        stmt = (
            select(CandidateCertification)
            .where(CandidateCertification.candidate_profile_id == profile_id)
            .order_by(CandidateCertification.created_at.desc())
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())

    @staticmethod
    async def get_certification_by_id(
        db: AsyncSession, profile_id: str, cert_id: str
    ) -> Optional[CandidateCertification]:
        stmt = select(CandidateCertification).where(
            CandidateCertification.candidate_profile_id == profile_id,
            CandidateCertification.id == cert_id,
        )
        res = await db.execute(stmt)
        return res.scalars().first()

    @staticmethod
    async def add_certification(
        db: AsyncSession, cert: CandidateCertification
    ) -> CandidateCertification:
        db.add(cert)
        await db.commit()
        await db.refresh(cert)
        return cert

    @staticmethod
    async def save_certification(
        db: AsyncSession, cert: CandidateCertification
    ) -> CandidateCertification:
        cert.updated_at = datetime.now(timezone.utc)
        db.add(cert)
        await db.commit()
        await db.refresh(cert)
        return cert

    @staticmethod
    async def delete_certification(
        db: AsyncSession, cert: CandidateCertification
    ) -> None:
        await db.delete(cert)
        await db.commit()

    # ── Featured Projects ──────────────────────────────────────────────────────

    @staticmethod
    async def get_projects(
        db: AsyncSession, profile_id: str
    ) -> List[CandidateProject]:
        stmt = (
            select(CandidateProject)
            .where(CandidateProject.candidate_profile_id == profile_id)
            .order_by(CandidateProject.created_at.desc())
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())

    @staticmethod
    async def get_project_by_id(
        db: AsyncSession, profile_id: str, proj_id: str
    ) -> Optional[CandidateProject]:
        stmt = select(CandidateProject).where(
            CandidateProject.candidate_profile_id == profile_id,
            CandidateProject.id == proj_id,
        )
        res = await db.execute(stmt)
        return res.scalars().first()

    @staticmethod
    async def add_project(
        db: AsyncSession, proj: CandidateProject
    ) -> CandidateProject:
        db.add(proj)
        await db.commit()
        await db.refresh(proj)
        return proj

    @staticmethod
    async def save_project(
        db: AsyncSession, proj: CandidateProject
    ) -> CandidateProject:
        proj.updated_at = datetime.now(timezone.utc)
        db.add(proj)
        await db.commit()
        await db.refresh(proj)
        return proj

    @staticmethod
    async def delete_project(
        db: AsyncSession, proj: CandidateProject
    ) -> None:
        await db.delete(proj)
        await db.commit()

    # ── Resume ─────────────────────────────────────────────────────────────────

    @staticmethod
    async def get_active_resume(
        db: AsyncSession, profile_id: str
    ) -> Optional[CandidateResume]:
        stmt = (
            select(CandidateResume)
            .where(
                CandidateResume.candidate_profile_id == profile_id,
                CandidateResume.is_active == True,
            )
            .order_by(CandidateResume.created_at.desc())
        )
        res = await db.execute(stmt)
        return res.scalars().first()

    @staticmethod
    async def get_resume_by_id(
        db: AsyncSession, profile_id: str, resume_id: str
    ) -> Optional[CandidateResume]:
        stmt = select(CandidateResume).where(
            CandidateResume.candidate_profile_id == profile_id,
            CandidateResume.id == resume_id,
        )
        res = await db.execute(stmt)
        return res.scalars().first()

    @staticmethod
    async def add_resume(
        db: AsyncSession, resume: CandidateResume
    ) -> CandidateResume:
        # Mark previous active resumes as inactive
        stmt = (
            update(CandidateResume)
            .where(
                CandidateResume.candidate_profile_id == resume.candidate_profile_id,
                CandidateResume.is_active == True,
            )
            .values(is_active=False)
        )
        await db.execute(stmt)

        db.add(resume)
        await db.commit()
        await db.refresh(resume)
        return resume
