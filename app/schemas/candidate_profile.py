from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field, ConfigDict


# ── Updates ───────────────────────────────────────────────────────────────────

class PersonalUpdate(BaseModel):
    name: Optional[str] = None
    fullName: Optional[str] = None
    headline: Optional[str] = None
    professional_title: Optional[str] = None
    bio: Optional[str] = None
    professional_summary: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    linkedin: Optional[str] = None
    linkedin_url: Optional[str] = None
    github: Optional[str] = None
    github_url: Optional[str] = None
    portfolio: Optional[str] = None
    portfolio_url: Optional[str] = None
    avatar: Optional[str] = None


class PreferencesUpdate(BaseModel):
    total_experience: Optional[str] = None
    experience: Optional[str] = None
    current_salary: Optional[str] = None
    currentSalary: Optional[str] = None
    expected_salary_min: Optional[str] = None
    expected_salary_max: Optional[str] = None
    expected_salary: Optional[str] = None
    expectedSalary: Optional[str] = None
    work_mode: Optional[str] = None
    workMode: Optional[str] = None
    employment_type: Optional[str] = None
    jobType: Optional[str] = None
    preferred_job_roles: Optional[List[str]] = None
    preferredRoles: Optional[List[str]] = None
    preferred_locations: Optional[List[str]] = None
    preferredLocations: Optional[List[str]] = None


# ── Skills ─────────────────────────────────────────────────────────────────────

class SkillCreate(BaseModel):
    skill_name: Optional[str] = None
    name: Optional[str] = None

    def get_name(self) -> str:
        name = self.skill_name or self.name or ""
        return name.strip()


class SkillItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    skill_name: str
    name: str  # alias for frontend


# ── Experience ─────────────────────────────────────────────────────────────────

class ExperienceCreate(BaseModel):
    role: str = Field(..., min_length=1)
    company: str = Field(..., min_length=1)
    location: Optional[str] = None
    duration: Optional[str] = None
    description: Optional[str] = None


class ExperienceUpdate(BaseModel):
    role: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    duration: Optional[str] = None
    description: Optional[str] = None


class ExperienceItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    role: str
    company: str
    location: Optional[str] = None
    duration: Optional[str] = None
    description: Optional[str] = None


# ── Education ──────────────────────────────────────────────────────────────────

class EducationCreate(BaseModel):
    degree: str = Field(..., min_length=1)
    institution: str = Field(..., min_length=1)
    duration: Optional[str] = None
    score: Optional[str] = None


class EducationUpdate(BaseModel):
    degree: Optional[str] = None
    institution: Optional[str] = None
    duration: Optional[str] = None
    score: Optional[str] = None


class EducationItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    degree: str
    institution: str
    duration: Optional[str] = None
    score: Optional[str] = None


# ── Certifications ─────────────────────────────────────────────────────────────

class CertificationCreate(BaseModel):
    name: str = Field(..., min_length=1)
    issuer: str = Field(..., min_length=1)
    year: Optional[str] = None


class CertificationUpdate(BaseModel):
    name: Optional[str] = None
    issuer: Optional[str] = None
    year: Optional[str] = None


class CertificationItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    issuer: str
    year: Optional[str] = None


# ── Projects ───────────────────────────────────────────────────────────────────

class ProjectCreate(BaseModel):
    title: str = Field(..., min_length=1)
    tech: Optional[str] = None
    description: Optional[str] = None
    link: Optional[str] = None


class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    tech: Optional[str] = None
    description: Optional[str] = None
    link: Optional[str] = None


class ProjectItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    tech: Optional[str] = None
    description: Optional[str] = None
    link: Optional[str] = None


# ── Resume ─────────────────────────────────────────────────────────────────────

class ResumeItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    file_name: str
    fileName: str
    file_size: Optional[str] = None
    fileSize: Optional[str] = None
    file_type: Optional[str] = None
    fileType: Optional[str] = None
    uploaded_at: Optional[str] = None
    uploadedDate: Optional[str] = None


# ── Full Profile Response ──────────────────────────────────────────────────────

class CandidateProfileResponse(BaseModel):
    id: str
    name: str
    fullName: str
    email: str
    phone: Optional[str] = None
    district: Optional[str] = None
    mandal: Optional[str] = None
    village: Optional[str] = None
    qualification_level: Optional[str] = None
    headline: Optional[str] = None
    professional_title: Optional[str] = None
    bio: Optional[str] = None
    professional_summary: Optional[str] = None
    location: Optional[str] = None
    linkedin: Optional[str] = None
    linkedin_url: Optional[str] = None
    github: Optional[str] = None
    github_url: Optional[str] = None
    portfolio: Optional[str] = None
    portfolio_url: Optional[str] = None
    avatar: Optional[str] = None
    profileImage: Optional[str] = None

    profile_completion_percentage: int
    profileCompletion: int

    skillsPreferences: Dict[str, Any]
    skills: List[str]
    skillsList: List[SkillItem]

    resume: Optional[ResumeItem] = None
    experienceList: List[ExperienceItem]
    educationList: List[EducationItem]
    certificationsList: List[CertificationItem]
    projectsList: List[ProjectItem]
