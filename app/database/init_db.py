import os
import json
import uuid
from datetime import datetime, timezone
from sqlalchemy import text, select, func
from sqlalchemy.ext.asyncio import AsyncConnection
from app.database.session import async_engine, AsyncSessionLocal
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
from app.models.saved_job import SavedJob
from app.models.application import CandidateApplication, ApplicationTimelineEvent
from app.models.notification import Notification
from app.models.recruiter import RecruiterProfile
from app.models.job import Job
from app.models.interview import Interview
from app.models.admin_profile import AdminProfile
import re
from app.models.website_content import (
    GalleryPhoto,
    GalleryVideo,
    PressArticle,
    WebsiteSectionHeader,
    JobPageSetting,
    JobLocation,
    AboutUsSetting,
    JobMelaPageSetting,
    SkillCmsSection,
)
from app.core.security import hash_password


DEMO_USERS = [
    {
        "email": "candidate1@ntrvikasa.com",
        "name": "Priya Sharma",
        "phone": "9876543210",
        "role": "CANDIDATE",
        "password": "password123",
        "aadhaar_number": "999900001111",
        "district": "NTR District",
        "mandal": "Vijayawada Urban",
    },
    {
        "email": "candidate2@ntrvikasa.com",
        "name": "Rahul Varma",
        "phone": "9876543211",
        "role": "CANDIDATE",
        "password": "password123",
        "aadhaar_number": "999900001112",
        "district": "NTR District",
        "mandal": "Vijayawada Urban",
    },
    {
        "email": "recruiter1@ntrvikasa.com",
        "name": "Arjun",
        "phone": "9876543220",
        "role": "RECRUITER",
        "password": "password123",
    },
    {
        "email": "recruiter2@ntrvikasa.com",
        "name": "Sneha",
        "phone": "9876543221",
        "role": "RECRUITER",
        "password": "password123",
    },
    {
        "email": "admin1@ntrvikasa.com",
        "name": "Admin User",
        "phone": "9876543230",
        "role": "ADMIN",
        "password": "password123",
    },
    {
        "email": "admin2@ntrvikasa.com",
        "name": "Super Admin",
        "phone": "9876543231",
        "role": "ADMIN",
        "password": "password123",
    },
]


async def check_db_connection() -> bool:
    """
    Verify async connection to MySQL database using AsyncEngine and AsyncConnection.
    Executes 'SELECT 1' to ensure connectivity.
    """
    try:
        async with async_engine.connect() as conn:  # type: AsyncConnection
            result = await conn.execute(text("SELECT 1"))
            return result.scalar() == 1
    except Exception as e:
        raise ConnectionError(
            f"[MySQL Connection Error] Failed to connect using asyncmy: {e}"
        ) from e


async def seed_demo_users() -> None:
    """Seed default demo accounts into MySQL if they do not exist."""
    async with AsyncSessionLocal() as session:
        for u in DEMO_USERS:
            stmt = select(User).where(User.email == u["email"])
            res = await session.execute(stmt)
            existing = res.scalar_one_or_none()
            user_id = existing.id if existing else str(uuid.uuid4())
            if not existing:
                user = User(
                    id=user_id,
                    email=u["email"],
                    phone=u["phone"],
                    hashed_password=hash_password(u["password"]),
                    role=u["role"],
                    is_active=True,
                    is_verified=True,
                )
                session.add(user)

                if u["role"] == "CANDIDATE":
                    profile = CandidateProfile(
                        id=str(uuid.uuid4()),
                        user_id=user_id,
                        name=u["name"],
                        phone=u["phone"],
                        aadhaar_number=u["aadhaar_number"],
                        district=u["district"],
                        mandal=u["mandal"],
                        qualification_level="UG",
                        profile_completion=80,
                        verified=True,
                    )
                    session.add(profile)

            if u["role"] == "ADMIN":
                adm_prof_stmt = select(AdminProfile).where(AdminProfile.user_id == user_id)
                adm_prof_res = await session.execute(adm_prof_stmt)
                if not adm_prof_res.scalar_one_or_none():
                    adm_profile = AdminProfile(
                        id=str(uuid.uuid4()),
                        user_id=user_id,
                        full_name=u["name"],
                        designation="State Operations Lead" if "admin1" in u["email"] else "Directorate of Employment",
                        contact_phone="+91 98765 43210" if "admin1" in u["email"] else "+91 98765 43211",
                        department="State Employment & Skill Development Authority",
                        profile_image_url=None,
                    )
                    session.add(adm_profile)

        await session.commit()



INITIAL_CANDIDATE1_SAVED_JOBS = [
    {
        "job_id": "1",
        "title": "Senior Frontend Engineer",
        "company_name": "TechCorp India",
        "company_verified": True,
        "location": "Bengaluru, Karnataka",
        "salary": "₹14 - ₹22 LPA",
        "experience": "3-5 years",
        "employment_type": "Full-time",
        "work_mode": "Hybrid",
        "skills": ["React", "TypeScript", "Node.js", "Redux Toolkit", "Tailwind CSS"],
    },
    {
        "job_id": "2",
        "title": "Full Stack Developer",
        "company_name": "Infosys",
        "company_verified": True,
        "location": "Bengaluru, Karnataka",
        "salary": "₹18 - ₹28 LPA",
        "experience": "3-6 years",
        "employment_type": "Full-time",
        "work_mode": "Hybrid",
        "skills": ["Java", "Spring Boot", "React", "Kafka"],
    },
    {
        "job_id": "3",
        "title": "Product Manager - Fintech",
        "company_name": "Razorpay",
        "company_verified": True,
        "location": "Bengaluru, Karnataka",
        "salary": "₹22 - ₹35 LPA",
        "experience": "4-7 years",
        "employment_type": "Full-time",
        "work_mode": "Hybrid",
        "skills": ["Product Management", "SQL", "Fintech", "Agile"],
    },
    {
        "job_id": "7",
        "title": "Staff DevOps / SRE Engineer",
        "company_name": "Flipkart",
        "company_verified": True,
        "location": "Bengaluru, Karnataka",
        "salary": "₹28 - ₹42 LPA",
        "experience": "5-8 years",
        "employment_type": "Full-time",
        "work_mode": "Hybrid",
        "skills": ["Kubernetes", "Docker", "AWS", "Terraform", "Go"],
    },
    {
        "job_id": "8",
        "title": "Data Scientist - Recommendation Systems",
        "company_name": "Zomato",
        "company_verified": True,
        "location": "Gurugram, Haryana",
        "salary": "₹20 - ₹32 LPA",
        "experience": "3-5 years",
        "employment_type": "Full-time",
        "work_mode": "Hybrid",
        "skills": ["Python", "Machine Learning", "SQL", "PyTorch"],
    },
    {
        "job_id": "11",
        "title": "Senior Android Engineer",
        "company_name": "Swiggy",
        "company_verified": True,
        "location": "Bengaluru, Karnataka",
        "salary": "₹22 - ₹34 LPA",
        "experience": "4-6 years",
        "employment_type": "Full-time",
        "work_mode": "Hybrid",
        "skills": ["Kotlin", "Android SDK", "Jetpack Compose", "Coroutines"],
    },
]


async def seed_candidate_saved_jobs() -> None:
    """Seed initial 6 saved jobs for candidate 1 (Priya Sharma) if not already present."""
    async with AsyncSessionLocal() as session:
        u_stmt = select(User).where(User.email == "candidate1@ntrvikasa.com")
        u_res = await session.execute(u_stmt)
        c1_user = u_res.scalar_one_or_none()
        if not c1_user:
            return

        cp_stmt = select(CandidateProfile).where(CandidateProfile.user_id == c1_user.id)
        cp_res = await session.execute(cp_stmt)
        c1_profile = cp_res.scalar_one_or_none()
        if not c1_profile:
            return

        # Check existing saved jobs count
        sj_stmt = select(SavedJob).where(SavedJob.candidate_profile_id == c1_profile.id)
        sj_res = await session.execute(sj_stmt)
        existing_jobs = sj_res.scalars().all()
        if existing_jobs:
            return

        for job_data in INITIAL_CANDIDATE1_SAVED_JOBS:
            saved_job = SavedJob(
                id=str(uuid.uuid4()),
                candidate_profile_id=c1_profile.id,
                job_id=job_data["job_id"],
                title=job_data["title"],
                company_name=job_data["company_name"],
                company_verified=job_data["company_verified"],
                location=job_data["location"],
                salary=job_data["salary"],
                experience=job_data["experience"],
                employment_type=job_data["employment_type"],
                work_mode=job_data["work_mode"],
                skills=json.dumps(job_data["skills"]),
                is_applied=False,
                saved_at=datetime.now(timezone.utc),
            )
            session.add(saved_job)

        await session.commit()


INITIAL_CANDIDATE1_APPLICATIONS = [
    {
        "application_number": "NTR-01-02-0024",
        "job_id": "mela-1-comp-2",
        "job_title": "Graduate Trainee Engineer",
        "company_name": "TechCorp India",
        "location": "Visakhapatnam",
        "salary": "₹5.0 - ₹8.0 LPA",
        "employment_type": "Full-time",
        "work_mode": "On-site",
        "application_type": "Job Mela Application",
        "mela_id": "1",
        "mela_title": "AP Mega IT & ITES Job Mela 2026",
        "event_number": "01",
        "company_sequence": "02",
        "application_sequence": "0024",
        "status": "SHORTLISTED",
        "applied_date": "22 Aug 2026",
        "timeline": [
            {"stage": "Applied", "status": "APPLIED", "label": "Application Submitted", "date": "22 Aug 2026", "completed": True, "current": False, "step_order": 1},
            {"stage": "Screening", "status": "SCREENING", "label": "Application Screened", "date": "24 Aug 2026", "completed": True, "current": False, "step_order": 2},
            {"stage": "Shortlisted", "status": "SHORTLISTED", "label": "Profile Shortlisted for Mela Interview", "date": "26 Aug 2026", "completed": True, "current": True, "step_order": 3},
            {"stage": "Interview", "status": "INTERVIEW", "label": "Spot Interview at Event", "date": "28 Sept 2026", "completed": False, "current": False, "step_order": 4},
            {"stage": "Selected", "status": "SELECTED", "label": "Final Selection Result", "date": "TBD", "completed": False, "current": False, "step_order": 5},
        ],
    },
    {
        "application_number": "NTR-01-04-0001",
        "job_id": "mela-1-comp-7",
        "job_title": "TCS Digital Software Developer",
        "company_name": "TCS",
        "location": "Visakhapatnam",
        "salary": "₹7.0 - ₹9.0 LPA",
        "employment_type": "Full-time",
        "work_mode": "On-site",
        "application_type": "Job Mela Application",
        "mela_id": "1",
        "mela_title": "AP Mega IT & ITES Job Mela 2026",
        "event_number": "01",
        "company_sequence": "04",
        "application_sequence": "0001",
        "status": "APPLIED",
        "applied_date": "28 Aug 2026",
        "timeline": [
            {"stage": "Applied", "status": "APPLIED", "label": "Application Submitted", "date": "28 Aug 2026", "completed": True, "current": True, "step_order": 1},
            {"stage": "Screening", "status": "SCREENING", "label": "Resume Under Screening", "date": "Pending Review", "completed": False, "current": False, "step_order": 2},
            {"stage": "Shortlisted", "status": "SHORTLISTED", "label": "Pending Shortlist", "date": "Pending", "completed": False, "current": False, "step_order": 3},
            {"stage": "Interview", "status": "INTERVIEW", "label": "Spot Interview at Event", "date": "28 Sept 2026", "completed": False, "current": False, "step_order": 4},
            {"stage": "Selected", "status": "SELECTED", "label": "Final Selection", "date": "TBD", "completed": False, "current": False, "step_order": 5},
        ],
    },
    {
        "application_number": "APP-000124",
        "job_id": "1",
        "job_title": "Senior Python Developer",
        "company_name": "TechCorp India",
        "location": "Hyderabad",
        "salary": "₹12,00,000 - ₹18,00,000",
        "employment_type": "Full-time",
        "work_mode": "Hybrid",
        "application_type": "Direct Job Application",
        "status": "SHORTLISTED",
        "applied_date": "02 Sept 2026",
        "timeline": [
            {"stage": "Applied", "status": "APPLIED", "label": "Applied Online", "date": "02 Sept 2026", "completed": True, "current": False, "step_order": 1},
            {"stage": "Screening", "status": "SCREENING", "label": "HR Screening Cleared", "date": "03 Sept 2026", "completed": True, "current": False, "step_order": 2},
            {"stage": "Shortlisted", "status": "SHORTLISTED", "label": "Shortlisted for Tech Interview", "date": "04 Sept 2026", "completed": True, "current": True, "step_order": 3},
            {"stage": "Interview", "status": "INTERVIEW", "label": "Interview Round 1", "date": "Pending Schedule", "completed": False, "current": False, "step_order": 4},
            {"stage": "Selected", "status": "SELECTED", "label": "Final Decision", "date": "TBD", "completed": False, "current": False, "step_order": 5},
        ],
    },
    {
        "application_number": "APP-000002",
        "job_id": "2",
        "job_title": "Senior React Developer",
        "company_name": "Infosys Digital",
        "location": "Visakhapatnam",
        "salary": "₹15,00,000 - ₹22,00,000",
        "employment_type": "Full-time",
        "work_mode": "Remote",
        "application_type": "Direct Job Application",
        "status": "INTERVIEW",
        "applied_date": "30 Aug 2026",
        "timeline": [
            {"stage": "Applied", "status": "APPLIED", "label": "Application Submitted", "date": "30 Aug 2026", "completed": True, "current": False, "step_order": 1},
            {"stage": "Screening", "status": "SCREENING", "label": "Recruiter Screening", "date": "31 Aug 2026", "completed": True, "current": False, "step_order": 2},
            {"stage": "Shortlisted", "status": "SHORTLISTED", "label": "Shortlisted by Hiring Manager", "date": "01 Sept 2026", "completed": True, "current": False, "step_order": 3},
            {"stage": "Interview", "status": "INTERVIEW", "label": "Technical Round 1 (Google Meet)", "date": "10 Sept 2026 (11:00 AM)", "completed": True, "current": True, "step_order": 4},
            {"stage": "Selected", "status": "SELECTED", "label": "Offer Rollout", "date": "TBD", "completed": False, "current": False, "step_order": 5},
        ],
    },
    {
        "application_number": "APP-000003",
        "job_id": "3",
        "job_title": "Frontend UI Architect",
        "company_name": "Wipro Cloud Services",
        "location": "Bengaluru",
        "salary": "₹18,00,000 - ₹25,00,000",
        "employment_type": "Full-time",
        "work_mode": "Hybrid",
        "application_type": "Direct Job Application",
        "status": "SCREENING",
        "applied_date": "26 Aug 2026",
        "timeline": [
            {"stage": "Applied", "status": "APPLIED", "label": "Application Received", "date": "26 Aug 2026", "completed": True, "current": False, "step_order": 1},
            {"stage": "Screening", "status": "SCREENING", "label": "Portfolio & Code Screening", "date": "28 Aug 2026", "completed": True, "current": True, "step_order": 2},
            {"stage": "Shortlisted", "status": "SHORTLISTED", "label": "Shortlist Review", "date": "Pending Review", "completed": False, "current": False, "step_order": 3},
            {"stage": "Interview", "status": "INTERVIEW", "label": "Architect Interview", "date": "TBD", "completed": False, "current": False, "step_order": 4},
            {"stage": "Selected", "status": "SELECTED", "label": "Selection", "date": "TBD", "completed": False, "current": False, "step_order": 5},
        ],
    },
    {
        "application_number": "APP-000004",
        "job_id": "4",
        "job_title": "Design Systems Engineer",
        "company_name": "Flipkart AP Tech Hub",
        "location": "Vijayawada",
        "salary": "₹14,00,000 - ₹20,00,000",
        "employment_type": "Full-time",
        "work_mode": "On-site",
        "application_type": "Direct Job Application",
        "status": "APPLIED",
        "applied_date": "01 Sept 2026",
        "timeline": [
            {"stage": "Applied", "status": "APPLIED", "label": "Application Sent", "date": "01 Sept 2026", "completed": True, "current": True, "step_order": 1},
            {"stage": "Screening", "status": "SCREENING", "label": "Reviewing Application", "date": "Pending Review", "completed": False, "current": False, "step_order": 2},
            {"stage": "Shortlisted", "status": "SHORTLISTED", "label": "Shortlist", "date": "Pending", "completed": False, "current": False, "step_order": 3},
            {"stage": "Interview", "status": "INTERVIEW", "label": "Design System Interview", "date": "Pending", "completed": False, "current": False, "step_order": 4},
            {"stage": "Selected", "status": "SELECTED", "label": "Selection", "date": "TBD", "completed": False, "current": False, "step_order": 5},
        ],
    },
    {
        "application_number": "APP-000005",
        "job_id": "5",
        "job_title": "Frontend Developer (React)",
        "company_name": "TCS Innovation",
        "location": "Visakhapatnam",
        "salary": "₹12,00,000 - ₹16,00,000",
        "employment_type": "Full-time",
        "work_mode": "Hybrid",
        "application_type": "Direct Job Application",
        "status": "SELECTED",
        "applied_date": "15 Aug 2026",
        "timeline": [
            {"stage": "Applied", "status": "APPLIED", "label": "Applied Online", "date": "15 Aug 2026", "completed": True, "current": False, "step_order": 1},
            {"stage": "Screening", "status": "SCREENING", "label": "Screening Passed", "date": "17 Aug 2026", "completed": True, "current": False, "step_order": 2},
            {"stage": "Shortlisted", "status": "SHORTLISTED", "label": "Shortlisted for Interview", "date": "19 Aug 2026", "completed": True, "current": False, "step_order": 3},
            {"stage": "Interview", "status": "INTERVIEW", "label": "Technical Interview Cleared", "date": "20 Aug 2026", "completed": True, "current": False, "step_order": 4},
            {"stage": "Selected", "status": "SELECTED", "label": "Selected & Offer Released", "date": "24 Aug 2026", "completed": True, "current": True, "step_order": 5},
        ],
    },
    {
        "application_number": "APP-000006",
        "job_id": "6",
        "job_title": "Senior JavaScript Engineer",
        "company_name": "Capgemini India",
        "location": "Hyderabad",
        "salary": "₹13,00,000 - ₹17,00,000",
        "employment_type": "Full-time",
        "work_mode": "Hybrid",
        "application_type": "Direct Job Application",
        "status": "REJECTED",
        "applied_date": "05 Aug 2026",
        "timeline": [
            {"stage": "Applied", "status": "APPLIED", "label": "Application Submitted", "date": "05 Aug 2026", "completed": True, "current": False, "step_order": 1},
            {"stage": "Screening", "status": "SCREENING", "label": "Resume Screening", "date": "08 Aug 2026", "completed": True, "current": False, "step_order": 2},
            {"stage": "Shortlisted", "status": "SHORTLISTED", "label": "Not Progressed", "date": "Not Shortlisted", "completed": False, "current": False, "step_order": 3},
            {"stage": "Interview", "status": "INTERVIEW", "label": "Interview", "date": "N/A", "completed": False, "current": False, "step_order": 4},
            {"stage": "Rejected", "status": "REJECTED", "label": "Position Filled / Not Selected", "date": "10 Aug 2026", "completed": True, "current": True, "step_order": 5},
        ],
    },
]


async def seed_candidate_applications() -> None:
    """Seed initial 8 applications and timelines for candidate 1 (Priya Sharma) if not already present."""
    async with AsyncSessionLocal() as session:
        u_stmt = select(User).where(User.email == "candidate1@ntrvikasa.com")
        u_res = await session.execute(u_stmt)
        c1_user = u_res.scalar_one_or_none()
        if not c1_user:
            return

        cp_stmt = select(CandidateProfile).where(CandidateProfile.user_id == c1_user.id)
        cp_res = await session.execute(cp_stmt)
        c1_profile = cp_res.scalar_one_or_none()
        if not c1_profile:
            return

        # Check existing applications count
        app_stmt = select(CandidateApplication).where(CandidateApplication.candidate_profile_id == c1_profile.id)
        app_res = await session.execute(app_stmt)
        existing_apps = app_res.scalars().all()
        if existing_apps:
            return

        for app_data in INITIAL_CANDIDATE1_APPLICATIONS:
            app_id = str(uuid.uuid4())
            new_app = CandidateApplication(
                id=app_id,
                application_number=app_data["application_number"],
                candidate_profile_id=c1_profile.id,
                job_id=app_data["job_id"],
                job_title=app_data["job_title"],
                company_name=app_data["company_name"],
                location=app_data["location"],
                salary=app_data["salary"],
                employment_type=app_data["employment_type"],
                work_mode=app_data["work_mode"],
                application_type=app_data["application_type"],
                mela_id=app_data.get("mela_id"),
                mela_title=app_data.get("mela_title"),
                event_number=app_data.get("event_number"),
                company_sequence=app_data.get("company_sequence"),
                application_sequence=app_data.get("application_sequence"),
                status=app_data["status"],
                applied_date=app_data["applied_date"],
                applied_at=datetime.now(timezone.utc),
            )
            session.add(new_app)

            # Add timeline events
            for t in app_data.get("timeline", []):
                event = ApplicationTimelineEvent(
                    id=str(uuid.uuid4()),
                    application_id=app_id,
                    stage=t["stage"],
                    status=t["status"],
                    label=t.get("label"),
                    date=t.get("date"),
                    completed=t.get("completed", False),
                    current=t.get("current", False),
                    step_order=t.get("step_order", 1),
                )
                session.add(event)

        await session.commit()


async def seed_candidate_profile_details() -> None:
    """Seed Candidate 1 (Priya Sharma) extended profile, skills, experience, etc."""
    async with AsyncSessionLocal() as session:
        u_stmt = select(User).where(User.email == "candidate1@ntrvikasa.com")
        u_res = await session.execute(u_stmt)
        c1_user = u_res.scalar_one_or_none()
        if not c1_user:
            return

        cp_stmt = select(CandidateProfile).where(CandidateProfile.user_id == c1_user.id)
        cp_res = await session.execute(cp_stmt)
        c1_profile = cp_res.scalar_one_or_none()
        if not c1_profile:
            return

        # Update candidate 1 profile details
        c1_profile.headline = "Senior React & Frontend Developer | 4+ Years Experience"
        c1_profile.bio = (
            "Passionate frontend engineer specializing in performant React architectures, "
            "design systems, TypeScript, and micro-frontend state management with 4+ years "
            "of industry experience across enterprise web applications."
        )
        c1_profile.location = "Visakhapatnam, Andhra Pradesh"
        c1_profile.linkedin_url = "https://linkedin.com/in/priyasharma-dev"
        c1_profile.github_url = "https://github.com/priyasharma-frontend"
        c1_profile.portfolio_url = "https://priyasharma.dev"
        c1_profile.total_experience = "4.2 Years"
        c1_profile.current_salary = "₹14,50,000 / year"
        c1_profile.expected_salary = "₹18,00,000 - ₹24,00,000 / year"
        c1_profile.work_mode = "Hybrid"
        c1_profile.employment_type = "Full-time"
        c1_profile.preferred_job_roles = json.dumps([
            "Senior Frontend Developer", "React Specialist", "UI Engineer", "Fullstack UI Lead"
        ])
        c1_profile.preferred_locations = json.dumps([
            "Visakhapatnam", "Vijayawada", "Hyderabad", "Bengaluru"
        ])
        c1_profile.profile_completion = 100
        session.add(c1_profile)

        # Check existing skills
        sk_stmt = select(CandidateSkill).where(CandidateSkill.candidate_profile_id == c1_profile.id)
        sk_res = await session.execute(sk_stmt)
        if not sk_res.scalars().first():
            initial_skills = [
                "React.js", "TypeScript", "Next.js", "JavaScript (ES6+)", "Redux Toolkit",
                "Tailwind CSS", "HTML5/CSS3", "Jest & Testing Library", "Webpack/Vite", "REST APIs & GraphQL"
            ]
            for sk in initial_skills:
                session.add(CandidateSkill(
                    id=str(uuid.uuid4()),
                    candidate_profile_id=c1_profile.id,
                    skill_name=sk,
                ))

        # Check existing experiences
        exp_stmt = select(CandidateExperience).where(CandidateExperience.candidate_profile_id == c1_profile.id)
        exp_res = await session.execute(exp_stmt)
        if not exp_res.scalars().first():
            initial_exps = [
                {
                    "role": "Senior Frontend Engineer",
                    "company": "Infosys Digital",
                    "location": "Hyderabad (Hybrid)",
                    "duration": "June 2023 - Present (1 yr 3 mos)",
                    "description": "Architected responsive portal components for banking clients. Reduced initial bundle size by 35% using code-splitting and dynamic imports.",
                },
                {
                    "role": "Frontend Developer",
                    "company": "TCS Innovation Labs",
                    "location": "Visakhapatnam",
                    "duration": "Aug 2021 - May 2023 (1 yr 10 mos)",
                    "description": "Developed scalable single-page applications using React, Redux, and RESTful APIs for telecom enterprise solutions.",
                },
            ]
            for ex in initial_exps:
                session.add(CandidateExperience(
                    id=str(uuid.uuid4()),
                    candidate_profile_id=c1_profile.id,
                    **ex
                ))

        # Check existing educations
        edu_stmt = select(CandidateEducation).where(CandidateEducation.candidate_profile_id == c1_profile.id)
        edu_res = await session.execute(edu_stmt)
        if not edu_res.scalars().first():
            initial_edus = [
                {
                    "degree": "B.Tech in Computer Science & Engineering",
                    "institution": "Andhra University College of Engineering, Visakhapatnam",
                    "duration": "2017 - 2021",
                    "score": "8.7 CGPA",
                },
                {
                    "degree": "Intermediate (MPC)",
                    "institution": "Sri Chaitanya Junior College, Vijayawada",
                    "duration": "2015 - 2017",
                    "score": "96.2%",
                },
            ]
            for ed in initial_edus:
                session.add(CandidateEducation(
                    id=str(uuid.uuid4()),
                    candidate_profile_id=c1_profile.id,
                    **ed
                ))

        # Check existing certifications
        cert_stmt = select(CandidateCertification).where(CandidateCertification.candidate_profile_id == c1_profile.id)
        cert_res = await session.execute(cert_stmt)
        if not cert_res.scalars().first():
            initial_certs = [
                {"name": "Meta Certified Frontend Developer", "issuer": "Meta / Coursera", "year": "2024"},
                {"name": "AWS Certified Cloud Practitioner", "issuer": "Amazon Web Services", "year": "2023"},
            ]
            for ce in initial_certs:
                session.add(CandidateCertification(
                    id=str(uuid.uuid4()),
                    candidate_profile_id=c1_profile.id,
                    **ce
                ))

        # Check existing projects
        proj_stmt = select(CandidateProject).where(CandidateProject.candidate_profile_id == c1_profile.id)
        proj_res = await session.execute(proj_stmt)
        if not proj_res.scalars().first():
            initial_projs = [
                {
                    "title": "NTR Vikasa Candidate Portal",
                    "tech": "React, Vite, CSS Modules",
                    "description": "Interactive job portal frontend with responsive candidate dashboard, multi-step filter search, and applicant tracking.",
                },
                {
                    "title": "Enterprise Design System UI Kit",
                    "tech": "TypeScript, Storybook, Tailwind",
                    "description": "Comprehensive component library with 45+ accessible UI components used across 6 product teams.",
                },
            ]
            for pr in initial_projs:
                session.add(CandidateProject(
                    id=str(uuid.uuid4()),
                    candidate_profile_id=c1_profile.id,
                    **pr
                ))

        # Check existing resume
        res_stmt = select(CandidateResume).where(CandidateResume.candidate_profile_id == c1_profile.id)
        res_res = await session.execute(res_stmt)
        if not res_res.scalars().first():
            session.add(CandidateResume(
                id=str(uuid.uuid4()),
                candidate_profile_id=c1_profile.id,
                file_name="Vyshnavi_Resume.pdf",
                file_path=os.path.join(
                    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                    "uploads",
                    "resumes",
                    "c1_Vyshnavi_Resume.pdf",
                ),
                file_size="1.4 MB",
                file_type="PDF Document",
                is_active=True,
            ))

        await session.commit()


CANDIDATE_INITIAL_NOTIFICATIONS = [
    {
        "category": "shortlisted",
        "title": "Application Shortlisted: Senior Python Developer",
        "message": "TechCorp India has shortlisted your application (Application No: APP-000001) for Senior Python Developer. The recruiter may contact you soon for interview scheduling.",
        "link": "/candidate/applications",
        "application_id": "APP-000001",
        "is_read": False,
        "created_delta_minutes": 15,
    },
    {
        "category": "interview",
        "title": "Interview Scheduled: Technical Round 1 with Infosys Digital",
        "message": "Infosys Digital scheduled your Technical Round 1 for Senior React Developer on 10 Sept 2026, 11:00 AM - 12:00 PM IST via Google Meet.",
        "link": "/candidate/interviews",
        "application_id": "APP-000002",
        "interview_id": "INT-2026-001",
        "is_read": False,
        "created_delta_minutes": 45,
    },
    {
        "category": "application",
        "title": "Application Submitted: Design Systems Engineer",
        "message": "Your application for Design Systems Engineer at Flipkart AP Tech Hub has been submitted successfully (Application No: APP-000004). Status: Applied.",
        "link": "/candidate/applications",
        "application_id": "APP-000004",
        "is_read": False,
        "created_delta_minutes": 120,
    },
    {
        "category": "job_mela",
        "title": "Job Mela Shortlist: Graduate Trainee Engineer",
        "message": "AP Mega IT & ITES Job Mela 2026: TechCorp India shortlisted your Job Mela application (Job Mela Application No: NTR-01-02-0024) for spot interview at the event.",
        "link": "/candidate/applications",
        "job_mela_id": "MELA-AP-01",
        "is_read": False,
        "created_delta_minutes": 240,
    },
    {
        "category": "interview",
        "title": "Interview Reminder: Technical Round 1 in 2 Hours",
        "message": "Reminder: Your online technical interview with Infosys Digital for Senior React Developer starts at 11:00 AM IST today via Google Meet. Please join 10 minutes prior.",
        "link": "/candidate/interviews",
        "application_id": "APP-000002",
        "interview_id": "INT-2026-001",
        "is_read": False,
        "created_delta_minutes": 300,
    },
    {
        "category": "job_mela",
        "title": "Job Mela Entry Pass Confirmed: PASS-AP-849201",
        "message": "Your Fast-Track QR pass for AP Mega IT & ITES Job Mela 2026 is confirmed. Event Date: 28 Sept 2026. Venue: AU Convention Center, Beach Road, Visakhapatnam. Gate 3 opens at 9:00 AM.",
        "link": "/candidate/job-melas",
        "job_mela_id": "MELA-AP-01",
        "is_read": True,
        "created_delta_minutes": 1440,
    },
    {
        "category": "application",
        "title": "Application Status Update: Frontend UI Architect",
        "message": "Your application (Application No: APP-000003) for Frontend UI Architect at Wipro Cloud Services has moved to Screening stage review.",
        "link": "/candidate/applications",
        "application_id": "APP-000003",
        "is_read": True,
        "created_delta_minutes": 1500,
    },
    {
        "category": "offer",
        "title": "Congratulations! Selected by TCS Innovation 🎉",
        "message": "You have been selected for Frontend Developer (React) at TCS Innovation (Application No: APP-000005) following successful completion of all interview rounds.",
        "link": "/candidate/applications",
        "application_id": "APP-000005",
        "is_read": True,
        "created_delta_minutes": 2880,
    },
    {
        "category": "rejection",
        "title": "Application Update: Capgemini India",
        "message": "Capgemini India has concluded review for Senior JavaScript Engineer (Application No: APP-000006) and decided not to move forward at this time.",
        "link": "/candidate/applications",
        "application_id": "APP-000006",
        "is_read": True,
        "created_delta_minutes": 4320,
    },
    {
        "category": "account",
        "title": "Resume Updated: Vyshnavi_Resume.pdf",
        "message": "Your active resume 'Vyshnavi_Resume.pdf' was updated successfully. Recruiters downloading your profile will now receive this newest document.",
        "link": "/candidate/resume",
        "is_read": True,
        "created_delta_minutes": 4400,
    },
    {
        "category": "account",
        "title": "Profile Strength Reminder: 85% Complete",
        "message": "Add your latest project repository links to reach 100% profile strength and get 2x recruiter visibility across the Andhra Pradesh talent pool.",
        "link": "/candidate/profile",
        "is_read": True,
        "created_delta_minutes": 5760,
    },
    {
        "category": "account",
        "title": "Security Alert: Password Updated",
        "message": "Your candidate account password was updated securely. If you did not make this change, please contact candidate support immediately.",
        "link": "/candidate/settings",
        "is_read": True,
        "created_delta_minutes": 7200,
    },
    {
        "category": "support",
        "title": "Support Ticket #732104 Resolved",
        "message": "Your support ticket regarding 'Interview Scheduling & Links' has been resolved by the candidate support desk.",
        "link": "/candidate/help-support",
        "is_read": True,
        "created_delta_minutes": 8640,
    },
]


async def seed_candidate_notifications() -> None:
    """Seed initial notifications for candidate 1 (Priya Sharma) if not already present."""
    from datetime import timedelta
    async with AsyncSessionLocal() as session:
        u_stmt = select(User).where(User.email == "candidate1@ntrvikasa.com")
        u_res = await session.execute(u_stmt)
        c1_user = u_res.scalar_one_or_none()
        if not c1_user:
            return

        cp_stmt = select(CandidateProfile).where(CandidateProfile.user_id == c1_user.id)
        cp_res = await session.execute(cp_stmt)
        c1_profile = cp_res.scalar_one_or_none()
        if not c1_profile:
            return

        # Check existing notifications
        cnt_stmt = select(func.count(Notification.id)).where(Notification.candidate_id == c1_profile.id)
        cnt_res = await session.execute(cnt_stmt)
        if cnt_res.scalar_one() > 0:
            return

        now = datetime.now(timezone.utc)
        for item in CANDIDATE_INITIAL_NOTIFICATIONS:
            delta = timedelta(minutes=item.get("created_delta_minutes", 10))
            created_at = now - delta
            read_at = (now - timedelta(minutes=max(1, item.get("created_delta_minutes", 10) - 5))) if item["is_read"] else None

            notif = Notification(
                id=str(uuid.uuid4()),
                candidate_id=c1_profile.id,
                category=item["category"],
                title=item["title"],
                message=item["message"],
                link=item.get("link"),
                application_id=item.get("application_id"),
                interview_id=item.get("interview_id"),
                job_id=item.get("job_id"),
                job_mela_id=item.get("job_mela_id"),
                is_read=item["is_read"],
                is_dismissed=False,
                created_at=created_at,
                read_at=read_at,
            )
            session.add(notif)

        await session.commit()



async def seed_recruiter_profile_and_dashboard_data() -> None:
    """Seed default RecruiterProfile, Jobs, Applications, and Interviews for recruiter1 (Arjun Reddy)."""
    async with AsyncSessionLocal() as session:
        u_stmt = select(User).where(User.email == "recruiter1@ntrvikasa.com")
        u_res = await session.execute(u_stmt)
        recruiter_user = u_res.scalar_one_or_none()
        if not recruiter_user:
            return

        # 1. RecruiterProfile
        rp_stmt = select(RecruiterProfile).where(RecruiterProfile.user_id == recruiter_user.id)
        rp_res = await session.execute(rp_stmt)
        rec_profile = rp_res.scalar_one_or_none()
        if not rec_profile:
            rec_profile = RecruiterProfile(
                id=str(uuid.uuid4()),
                user_id=recruiter_user.id,
                recruiter_name="Arjun Reddy",
                designation="Director of Talent Acquisition",
                work_email="recruiter1@ntrvikasa.com",
                mobile_phone="+91 98765 00112",
                company_name="ABC Technologies Pvt Ltd",
                company_website="https://abctechnologies.example.com",
                corporate_email="careers@abctechnologies.example.com",
                company_phone="+91 80 4920 1000",
                primary_industry="Information Technology",
                company_size="1000-5000 employees",
                headquarters_city_state="Bengaluru, Karnataka",
                registered_office_address="Block B, RMZ Ecospace, Outer Ring Road, Bellandur, Bengaluru 560103",
                company_description="ABC Technologies is a premier enterprise IT software solutions provider powering digital platforms across Fintech, E-Commerce, and Supply Chain.",
                incorporation_document_path="/docs/incorporation/abc_tech_inc.pdf",
                recruiter_authorization_document_path="/docs/auth/arjun_auth.pdf",
                company_logo_path="/logos/abc_tech.png",
                status="APPROVED",
            )
            session.add(rec_profile)
            await session.commit()
            await session.refresh(rec_profile)

        recruiter_id = rec_profile.id

        # 2. Jobs
        job_cnt_stmt = select(func.count(Job.id)).where(Job.recruiter_id == recruiter_id)
        job_cnt_res = await session.execute(job_cnt_stmt)
        if job_cnt_res.scalar_one() == 0:
            demo_jobs = [
                {
                    "job_id": "job-101",
                    "title": "Senior Frontend Engineer (React / TypeScript)",
                    "department": "Core Engineering",
                    "job_type": "Full-time",
                    "work_mode": "Hybrid",
                    "location": "Bengaluru, Karnataka",
                    "experience": "3-5 years",
                    "salary": "₹16,00,000 - ₹24,00,000 / year",
                    "openings": 3,
                    "status": "PUBLISHED",
                    "description": "Architect and implement performant React UI components using modern state architectures.",
                    "skills": "React.js, TypeScript, Next.js, Redux Toolkit, Tailwind CSS",
                    "deadline": "2026-11-30",
                },
                {
                    "job_id": "job-102",
                    "title": "Senior Python & Cloud Backend Developer",
                    "department": "Platform Core",
                    "job_type": "Full-time",
                    "work_mode": "Hybrid",
                    "location": "Hyderabad, Telangana",
                    "experience": "3-6 years",
                    "salary": "₹14,00,000 - ₹22,00,000 / year",
                    "openings": 2,
                    "status": "PUBLISHED",
                    "description": "Design and scale asynchronous microservices, REST APIs, and event pipelines using Python and FastAPI.",
                    "skills": "Python, FastAPI, PostgreSQL, Docker, AWS, Redis",
                    "deadline": "2026-11-25",
                },
                {
                    "job_id": "job-103",
                    "title": "DevOps & Cloud Infrastructure Specialist",
                    "department": "Infra & SecOps",
                    "job_type": "Full-time",
                    "work_mode": "Remote",
                    "location": "Remote (India)",
                    "experience": "4-7 years",
                    "salary": "₹20,00,000 - ₹30,00,000 / year",
                    "openings": 2,
                    "status": "PUBLISHED",
                    "description": "Lead automated multi-cloud provisioning, Kubernetes cluster management, and CI/CD automation.",
                    "skills": "Kubernetes, AWS, Terraform, Docker, CI/CD",
                    "deadline": "2026-12-10",
                },
                {
                    "job_id": "job-104",
                    "title": "AI / ML Engineer — Computer Vision & NLP",
                    "department": "AI Innovation Lab",
                    "job_type": "Full-time",
                    "work_mode": "Hybrid",
                    "location": "Bengaluru, Karnataka",
                    "experience": "2-4 years",
                    "salary": "₹18,00,000 - ₹26,00,000 / year",
                    "openings": 2,
                    "status": "PENDING",
                    "description": "Build predictive AI models, multimodal pipelines, and production LLM integrations.",
                    "skills": "PyTorch, Python, Machine Learning, NLP, LLMs",
                    "deadline": "2026-12-15",
                },
            ]
            for jd in demo_jobs:
                job_obj = Job(
                    id=str(uuid.uuid4()),
                    job_id=jd["job_id"],
                    recruiter_id=recruiter_id,
                    company_name=rec_profile.company_name,
                    title=jd["title"],
                    department=jd["department"],
                    job_type=jd["job_type"],
                    work_mode=jd["work_mode"],
                    location=jd["location"],
                    experience=jd["experience"],
                    salary=jd["salary"],
                    openings=jd["openings"],
                    status=jd["status"],
                    description=jd["description"],
                    skills=jd["skills"],
                    deadline=jd["deadline"],
                )
                session.add(job_obj)
            await session.commit()

        # 3. Applications
        # Find candidate 1 profile if available
        cp_stmt = select(CandidateProfile).limit(1)
        cp_res = await session.execute(cp_stmt)
        cand1_profile = cp_res.scalar_one_or_none()
        cand1_id = cand1_profile.id if cand1_profile else str(uuid.uuid4())

        app_cnt_stmt = select(func.count(CandidateApplication.id)).where(
            CandidateApplication.recruiter_id == recruiter_id
        )
        app_cnt_res = await session.execute(app_cnt_stmt)
        if app_cnt_res.scalar_one() == 0:
            demo_apps = [
                {
                    "app_num": "NTR-APP-501",
                    "cand_id": cand1_id,
                    "job_id": "job-101",
                    "job_title": "Senior Frontend Engineer (React / TypeScript)",
                    "exp": "4.2 Years",
                    "match": 95,
                    "status": "SHORTLISTED",
                    "applied_date": "02 Sept 2026",
                },
                {
                    "app_num": "NTR-APP-502",
                    "cand_id": cand1_id,
                    "job_id": "job-102",
                    "job_title": "Senior Python & Cloud Backend Developer",
                    "exp": "3.5 Years",
                    "match": 92,
                    "status": "INTERVIEW",
                    "applied_date": "01 Sept 2026",
                },
                {
                    "app_num": "NTR-APP-503",
                    "cand_id": cand1_id,
                    "job_id": "job-103",
                    "job_title": "DevOps & Cloud Infrastructure Specialist",
                    "exp": "6.0 Years",
                    "match": 94,
                    "status": "SHORTLISTED",
                    "applied_date": "28 Aug 2026",
                },
                {
                    "app_num": "NTR-APP-504",
                    "cand_id": cand1_id,
                    "job_id": "job-101",
                    "job_title": "Senior Frontend Engineer (React / TypeScript)",
                    "exp": "4.0 Years",
                    "match": 89,
                    "status": "UNDER_REVIEW",
                    "applied_date": "20 Aug 2026",
                },
                {
                    "app_num": "NTR-APP-505",
                    "cand_id": cand1_id,
                    "job_id": "job-101",
                    "job_title": "Senior Frontend Engineer (React / TypeScript)",
                    "exp": "3.0 Years",
                    "match": 82,
                    "status": "APPLIED",
                    "applied_date": "01 Sept 2026",
                },
            ]
            for da in demo_apps:
                app_obj = CandidateApplication(
                    id=str(uuid.uuid4()),
                    application_number=da["app_num"],
                    candidate_profile_id=da["cand_id"],
                    recruiter_id=recruiter_id,
                    job_id=da["job_id"],
                    job_title=da["job_title"],
                    company_name=rec_profile.company_name,
                    location="Bengaluru, Karnataka",
                    salary="₹16 - ₹24 LPA",
                    employment_type="Full-time",
                    work_mode="Hybrid",
                    application_type="Direct Job Application",
                    match_percentage=da["match"],
                    experience=da["exp"],
                    status=da["status"],
                    applied_date=da["applied_date"],
                    applied_at=datetime.now(timezone.utc),
                )
                session.add(app_obj)
            await session.commit()

        # 4. Interviews
        int_cnt_stmt = select(func.count(Interview.id)).where(Interview.recruiter_id == recruiter_id)
        int_cnt_res = await session.execute(int_cnt_stmt)
        if int_cnt_res.scalar_one() == 0:
            demo_interviews = [
                {
                    "int_num": "INT-001",
                    "cand_name": "Priya Sharma",
                    "cand_email": "priya.sharma@example.com",
                    "job_id": "job-101",
                    "job_title": "Senior Frontend Engineer (React / TypeScript)",
                    "round": "Technical Round 1",
                    "type": "Online (Google Meet)",
                    "date": "2026-10-10",
                    "time": "11:00 AM - 12:00 PM IST",
                    "platform": "Google Meet",
                    "link": "https://meet.google.com/abc-priya-fe",
                    "interviewer": "Arjun Reddy & Lead Architect",
                    "status": "SCHEDULED",
                },
                {
                    "int_num": "INT-002",
                    "cand_name": "Rahul Kumar",
                    "cand_email": "rahul.kumar@example.com",
                    "job_id": "job-102",
                    "job_title": "Senior Python & Cloud Backend Developer",
                    "round": "System Design & Architecture",
                    "type": "Online (Google Meet)",
                    "date": "2026-10-12",
                    "time": "02:00 PM - 03:00 PM IST",
                    "platform": "Google Meet",
                    "link": "https://meet.google.com/abc-rahul-py",
                    "interviewer": "Arjun Reddy & VP Engineering",
                    "status": "SCHEDULED",
                },
                {
                    "int_num": "INT-003",
                    "cand_name": "Manish Varma",
                    "cand_email": "manish.varma@example.com",
                    "job_id": "job-109",
                    "job_title": "Data Engineer — Spark & Databricks",
                    "round": "Live Coding & Algorithms",
                    "type": "Online (Google Meet)",
                    "date": "2026-10-14",
                    "time": "04:00 PM - 05:00 PM IST",
                    "platform": "Google Meet",
                    "link": "https://meet.google.com/abc-manish-de",
                    "interviewer": "Arjun Reddy & Data Platform Lead",
                    "status": "SCHEDULED",
                },
            ]
            for di in demo_interviews:
                int_obj = Interview(
                    id=str(uuid.uuid4()),
                    interview_number=di["int_num"],
                    recruiter_id=recruiter_id,
                    candidate_profile_id=cand1_id,
                    job_id=di["job_id"],
                    candidate_name=di["cand_name"],
                    candidate_email=di["cand_email"],
                    job_title=di["job_title"],
                    round_name=di["round"],
                    interview_type=di["type"],
                    date=di["date"],
                    time=di["time"],
                    meeting_platform=di["platform"],
                    meeting_link=di["link"],
                    interviewer=di["interviewer"],
                    status=di["status"],
                )
                session.add(int_obj)
            await session.commit()


async def seed_website_content() -> None:
    """Seed baseline gallery photos, videos, and newspaper articles if not already present."""
    async with AsyncSessionLocal() as session:
        # 1. Photos
        res = await session.execute(select(func.count(GalleryPhoto.id)))
        if (res.scalar() or 0) == 0:
            demo_photos = [
                {
                    "id": "img-1",
                    "title": "Mega Job Mela Vijayawada 2026",
                    "category": "Job Melas",
                    "image_url": "https://images.unsplash.com/photo-1540575467063-178a50c2df87?w=800&auto=format&fit=crop&q=80",
                    "date": "15 Sep 2026",
                    "description": "Over 120 recruiters and 4,500+ candidates attended the grand employment summit in Vijayawada.",
                    "display_order": 1,
                },
                {
                    "id": "img-2",
                    "title": "Advanced Skill Training Lab",
                    "category": "Skill Training",
                    "image_url": "https://images.unsplash.com/photo-1531482615713-2afd69097998?w=800&auto=format&fit=crop&q=80",
                    "date": "08 Sep 2026",
                    "description": "Enrolled students engaging in practical simulated software engineering and web development modules.",
                    "display_order": 2,
                },
                {
                    "id": "img-3",
                    "title": "Spot Offer Letter Distribution Ceremony",
                    "category": "Placements",
                    "image_url": "https://images.unsplash.com/photo-1523240795612-9a054b0db644?w=800&auto=format&fit=crop&q=80",
                    "date": "28 Aug 2026",
                    "description": "Selected candidates receiving immediate appointment orders from attending enterprise hiring teams.",
                    "display_order": 3,
                },
                {
                    "id": "img-4",
                    "title": "Corporate HR & Recruiter Summit",
                    "category": "Conferences",
                    "image_url": "https://images.unsplash.com/photo-1511578314322-379afb476865?w=800&auto=format&fit=crop&q=80",
                    "date": "18 Aug 2026",
                    "description": "Industry leaders discussing youth employability, tech apprenticeships, and regional hiring targets.",
                    "display_order": 4,
                },
                {
                    "id": "img-5",
                    "title": "Candidate Counselling & Guidance Booth",
                    "category": "Job Melas",
                    "image_url": "https://images.unsplash.com/photo-1577495508048-b635879837f1?w=800&auto=format&fit=crop&q=80",
                    "date": "02 Aug 2026",
                    "description": "Free resume evaluation, soft-skill mock interviews, and career counseling for rural youth.",
                    "display_order": 5,
                },
                {
                    "id": "img-6",
                    "title": "Women in Tech Empowerment Program",
                    "category": "Skill Training",
                    "image_url": "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=800&auto=format&fit=crop&q=80",
                    "date": "20 Jul 2026",
                    "description": "Empowering women engineers and technicians with cloud computing and AI certification courses.",
                    "display_order": 6,
                },
            ]
            for dp in demo_photos:
                photo_obj = GalleryPhoto(
                    id=dp["id"],
                    title=dp["title"],
                    category=dp["category"],
                    image_url=dp["image_url"],
                    date=dp["date"],
                    description=dp["description"],
                    display_order=dp["display_order"],
                    is_published=True,
                )
                session.add(photo_obj)

        # 2. Videos
        res_v = await session.execute(select(func.count(GalleryVideo.id)))
        if (res_v.scalar() or 0) == 0:
            demo_videos = [
                {
                    "id": "vid-1",
                    "title": "Mega Job Mela Vijayawada Highlights & Walk-in Drives",
                    "youtube_url": "https://www.youtube.com/watch?v=kYI_t91Z6oA",
                    "category": "Job Melas",
                    "date": "16 Sep 2026",
                    "description": "Watch the energetic atmosphere, recruiter interviews, and joyful candidate reactions at our mega recruitment drive.",
                    "display_order": 1,
                },
                {
                    "id": "vid-2",
                    "title": "Candidate Success Journey & Spot Offer Letters — NTR VIKASA",
                    "youtube_url": "https://www.youtube.com/watch?v=SqcY0GlETPk",
                    "category": "Placements",
                    "date": "05 Sep 2026",
                    "description": "Hear from our alumni who transitioned from college freshers to placed professionals in top corporations.",
                    "display_order": 2,
                },
                {
                    "id": "vid-3",
                    "title": "Skill Development Labs & Practical Industry Training Batch",
                    "youtube_url": "https://www.youtube.com/watch?v=tgbNymZ7vqY",
                    "category": "Skill Training",
                    "date": "22 Aug 2026",
                    "description": "Hands-on training, expert mentor guidance, and real-world project development at our modern center.",
                    "display_order": 3,
                },
            ]
            for dv in demo_videos:
                video_obj = GalleryVideo(
                    id=dv["id"],
                    title=dv["title"],
                    youtube_url=dv["youtube_url"],
                    category=dv["category"],
                    date=dv["date"],
                    description=dv["description"],
                    display_order=dv["display_order"],
                    is_published=True,
                )
                session.add(video_obj)

        # 3. Press Articles
        res_p = await session.execute(select(func.count(PressArticle.id)))
        if (res_p.scalar() or 0) == 0:
            demo_press = [
                {
                    "id": "news-1",
                    "newspaper": "Sakshi",
                    "title": "జాబ్‌మేళాలో 68 మందికి ఉద్యోగాలు",
                    "date": "08 Feb 2026",
                    "edition": "Tiruvuru Edition | Page 9",
                    "image_url": "/news/news-sakshi-job-mela.png",
                    "source_url": "https://epaper.sakshi.com/",
                    "summary": "ఆంధ్రప్రదేశ్ రాష్ట్ర నైపుణ్యాభివృద్ధి సంస్థ ఆధ్వర్యంలో జిల్లాలోని నిరుద్యోగ యువతకు గుంటుపల్లిలో నిర్వహించిన జాబ్ మేళాలో 68 మందికి ఉద్యోగాలు లభించాయి. జిల్లా కలెక్టర్ జి. లక్ష్మీశ స్వయంగా నియామక పత్రాలు అందజేశారు.",
                    "category": "Press Coverage",
                    "display_order": 1,
                },
                {
                    "id": "news-2",
                    "newspaper": "Eenadu",
                    "title": "18న ప్రత్యేక ఉద్యోగ మేళా",
                    "date": "14 Feb 2026",
                    "edition": "Andhra Pradesh State Edition",
                    "image_url": "/news/news-eenadu-job-mela.png",
                    "source_url": "https://epaper.eenadu.net/",
                    "summary": "కరెన్సీనగర్: రూరల్ ఇంక్యుబేషన్ స్కిల్లింగ్ అండ్ ఎంట్రప్రెన్యూర్ సెంటర్ (రైజ్), ఏపీఎస్ఎస్డీసీ, ఎన్టీఆర్ వికాస, జిల్లా ఉపాధి కల్పన శాఖ సంయుక్తంగా నిర్వహించనున్న ప్రత్యేక డ్రైవ్.",
                    "category": "Press Coverage",
                    "display_order": 2,
                },
                {
                    "id": "news-3",
                    "newspaper": "Special Press Bulletin",
                    "title": "గుంటుపల్లిలో “రైజ్” ఆధ్వర్యంలో ఎన్టీఆర్ వికాస జాబ్ మేళా — యువత సద్వినియోగం చేసుకోవాలి",
                    "date": "07 Feb 2026",
                    "edition": "Ibrahimpatnam - Udayatara",
                    "image_url": "/news/news-rise-job-mela.png",
                    "source_url": "https://naipunyam.ap.gov.in/",
                    "summary": "ఎన్టీఆర్ వికాస జాబ్ మేళా ద్వారా నిరుద్యోగ యువతకు 10కి పైగా ప్రముఖ కంపెనీలలో నెలకు రూ.12,000 నుండి రూ.35,000 వరకు వేతనంతో ఉద్యోగ అవకాశాలు.",
                    "category": "Press Coverage",
                    "display_order": 3,
                },
                {
                    "id": "news-4",
                    "newspaper": "Suryaa",
                    "title": "ఎన్టీఆర్ వికాస జాబ్ మేళా నిర్వహణ విజయవంతం",
                    "date": "08 Feb 2026",
                    "edition": "Major News | Page 2",
                    "image_url": "/news/news-surya-job-mela.png",
                    "source_url": "https://www.suryaa.com/",
                    "summary": "విజయవాడ: గుంటుపల్లిలో నిర్వహించిన జాబ్ మేళాలో 91 మంది హాజరు కాగా 68 మంది అభ్యర్థులకు ప్రైవేట్ కంపెనీలలో ఉద్యోగాలు లభించాయి, 14 మంది షార్ట్‌లిస్ట్ అయ్యారు. కలెక్టర్ డా. జి.లక్ష్మీశ ప్రశంసలు.",
                    "category": "Press Coverage",
                    "display_order": 4,
                },
            ]
            for da in demo_press:
                art_obj = PressArticle(
                    id=da["id"],
                    newspaper=da["newspaper"],
                    title=da["title"],
                    date=da["date"],
                    edition=da["edition"],
                    image_url=da["image_url"],
                    source_url=da["source_url"],
                    summary=da["summary"],
                    category=da["category"],
                    display_order=da["display_order"],
                    is_published=True,
                )
                session.add(art_obj)

        # 4. Section Headers
        res_h = await session.execute(select(WebsiteSectionHeader).where(WebsiteSectionHeader.id == "gallery"))
        if not res_h.scalar_one_or_none():
            session.add(WebsiteSectionHeader(
                id="gallery",
                badge="Moments & Media Highlights",
                heading1="NTR VIKASA Event &",
                heading2="Media Gallery",
                subtitle="Explore glimpses from our mega job fairs, candidate felicitations, skill training batches, and industry partner summits across Andhra Pradesh.",
            ))
        res_nh = await session.execute(select(WebsiteSectionHeader).where(WebsiteSectionHeader.id == "news"))
        if not res_nh.scalar_one_or_none():
            session.add(WebsiteSectionHeader(
                id="news",
                badge="In The Media & Press",
                heading1="Official Newspaper &",
                heading2="Press Highlights",
                subtitle="Read authentic press coverage, newspaper clippings, and administrative reports of NTR VIKASA Mega Job Melas across Andhra Pradesh.",
            ))

        # 5. Jobs Page Settings
        res_jps = await session.execute(select(JobPageSetting).where(JobPageSetting.id == "default"))
        if not res_jps.scalar_one_or_none():
            session.add(JobPageSetting(
                id="default",
                hero_badge="Corporate Recruitment Portal",
                hero_heading="Find Your Dream Job in Andhra Pradesh & India",
                hero_subtitle="Explore 2,450+ verified corporate job openings with zero placement fees",
                search_placeholder="Job title, skills (Python, React...), or company...",
                location_placeholder="All Locations (All India)",
                popular_searches=json.dumps([
                    "Python Developer",
                    "React JS",
                    "Data Analyst",
                    "Fresher Jobs",
                    "Hybrid Work",
                    "FastAPI",
                ]),
                updated_by="System Seed",
            ))

        # 6. Job Locations (28 States + 8 Union Territories)
        indian_states = [
            "Andhra Pradesh",
            "Arunachal Pradesh",
            "Assam",
            "Bihar",
            "Chhattisgarh",
            "Goa",
            "Gujarat",
            "Haryana",
            "Himachal Pradesh",
            "Jharkhand",
            "Karnataka",
            "Kerala",
            "Madhya Pradesh",
            "Maharashtra",
            "Manipur",
            "Meghalaya",
            "Mizoram",
            "Nagaland",
            "Odisha",
            "Punjab",
            "Rajasthan",
            "Sikkim",
            "Tamil Nadu",
            "Telangana",
            "Tripura",
            "Uttar Pradesh",
            "Uttarakhand",
            "West Bengal",
        ]
        indian_uts = [
            "Andaman and Nicobar Islands",
            "Chandigarh",
            "Dadra and Nagar Haveli and Daman and Diu",
            "Delhi",
            "Jammu and Kashmir",
            "Ladakh",
            "Lakshadweep",
            "Puducherry",
        ]

        order = 1
        for st in indian_states:
            res_loc = await session.execute(select(JobLocation).where(JobLocation.name == st))
            if not res_loc.scalar_one_or_none():
                loc_id = f"loc-{re.sub(r'[^a-z0-9]+', '-', st.lower()).strip('-')}"
                session.add(JobLocation(
                    id=loc_id,
                    name=st,
                    state_ut_type="state",
                    display_order=order,
                    is_active=True,
                ))
            order += 1

        for ut in indian_uts:
            res_loc = await session.execute(select(JobLocation).where(JobLocation.name == ut))
            if not res_loc.scalar_one_or_none():
                loc_id = f"loc-{re.sub(r'[^a-z0-9]+', '-', ut.lower()).strip('-')}"
                session.add(JobLocation(
                    id=loc_id,
                    name=ut,
                    state_ut_type="union_territory",
                    display_order=order,
                    is_active=True,
                ))
            order += 1

        # 7. About Us Settings (Hero, Principles, Team, Leadership, Partners)
        res_about = await session.execute(select(AboutUsSetting).where(AboutUsSetting.id == "default"))
        if not res_about.scalar_one_or_none():
            session.add(AboutUsSetting(
                id="default",
                hero_badge="Our Mission & Impact",
                hero_heading="Bridging Talent with Opportunity Across India",
                hero_description="NTR VIKASA Job Portal was founded on a simple principle: every candidate deserves fair, direct access to employment opportunities without scam fees, opaque processes, or dead ends.",
                wwsf_heading="What We Stand For",
                wwsf_description="Guiding principles that power our candidate-first architecture and employer verification policies.",
                wwsf_cards=json.dumps([
                    {
                        "id": "wwsf-1",
                        "icon": "ShieldCheck",
                        "title": "100% Verified Quality",
                        "desc": "Every single recruiter profile and job listing is reviewed to eliminate illegitimate recruiters and recruitment charges.",
                        "color": "primary",
                    },
                    {
                        "id": "wwsf-2",
                        "icon": "Target",
                        "title": "Transparent Application Lifecycle",
                        "desc": "Candidates receive live feedback across all 20 standard recruitment milestones from applied to interview to offer letters.",
                        "color": "success",
                    },
                    {
                        "id": "wwsf-3",
                        "icon": "Users",
                        "title": "Inclusive Mega Job Melas",
                        "desc": "Bringing top corporate opportunities directly to Tier-2, Tier-3 and rural graduate communities through walk-in physical fairs.",
                        "color": "warning",
                    },
                ]),
                team_badge="Our Leadership & Team",
                team_heading="Our Team",
                team_description="Experienced leaders with backgrounds across technology, public policy, and corporate recruitment.",
                team_members=json.dumps([
                    {
                        "id": "team-1",
                        "name": "Dr. Ramesh Sundaram",
                        "role": "Founder & Managing Director",
                        "organization": "NTR Vikasa",
                        "bio": "Former National Employment Council advisor with 20+ years driving talent mobility initiatives.",
                        "image": None,
                    },
                    {
                        "id": "team-2",
                        "name": "Ananya Deshmukh",
                        "role": "Chief Technology Officer",
                        "organization": "NTR Vikasa",
                        "bio": "Ex-Google & Flipkart engineering leader passionate about AI-driven career matching.",
                        "image": None,
                    },
                    {
                        "id": "team-3",
                        "name": "Siddharth Nair",
                        "role": "Head of Employer Partnerships",
                        "organization": "NTR Vikasa",
                        "bio": "Built recruitment pipelines across 500+ Indian corporate enterprises and SME networks.",
                        "image": None,
                    },
                    {
                        "id": "team-4",
                        "name": "Meera Sengupta",
                        "role": "Director of Diversity & Job Melas",
                        "organization": "NTR Vikasa",
                        "bio": "Pioneered inclusive job fairs for women, PwD, and tier-2/3 college graduates across India.",
                        "image": None,
                    },
                ]),
                leadership_badge="LEADERSHIP",
                leadership_heading="Leadership Messages",
                leadership_description="Words from our esteemed leaders who guide our mission",
                leadership_messages=json.dumps([
                    {
                        "id": "msg-1",
                        "name": "K Lacha Rao",
                        "designation": "Chairperson",
                        "role": "Chairperson",
                        "organization": "NTR Vikasa Jobs",
                        "image": None,
                        "initials": "VIKASA",
                        "headerBg": "#0f2a59",
                        "message": "Our mission is to bridge the gap between academia and industry by providing industry-aligned curriculum to ICT faculty and students, offering the finest skill, career connect, and mentorship guidance.",
                        "fullMessage": "Our mission is to bridge the gap between academia and industry by providing industry-aligned curriculum to ICT faculty and students, offering the finest skill, career connect, and mentorship guidance. Through deep collaboration with industry leaders and government stakeholders, we are dedicated to providing transformational employment avenues for all aspiring youth across the state.",
                        "hasViewAction": False,
                    },
                    {
                        "id": "msg-2",
                        "name": "K. Lacha Rao",
                        "designation": "Project Director",
                        "role": "Project Director",
                        "organization": "Vikasa Jobs",
                        "image": None,
                        "initials": "KLR",
                        "headerBg": "#047857",
                        "message": "At NTR Vikasa, our mission is to empower youth by creating meaningful employment opportunities and building a skilled workforce for the future. We believe that every individual deserves the right guidance, training, and platform to achieve their career aspirations. Through our initiatives such as Job Melas, skill development programs, and industry partnerships,...",
                        "fullMessage": "At NTR Vikasa, our mission is to empower youth by creating meaningful employment opportunities and building a skilled workforce for the future. We believe that every individual deserves the right guidance, training, and platform to achieve their career aspirations. Through our initiatives such as Job Melas, skill development programs, and industry partnerships, we strive to build sustainable bridges between talent and industry requirements across the state.",
                        "hasViewAction": True,
                    },
                ]),
                partners_heading="OUR INDUSTRY & ACADEMIC TRAINING PARTNERS",
                partners_description="Empowering future-ready talent in collaboration with leading corporate and educational organizations.",
                partners_list=json.dumps([
                    {"id": "p-1", "name": "Hyundai MOBIS", "logoText": "HYUNDAI MOBIS", "active": True, "order": 1},
                    {"id": "p-2", "name": "ISUZU", "logoText": "ISUZU", "active": True, "order": 2},
                    {"id": "p-3", "name": "MedPlus+", "logoText": "MedPlus+", "active": True, "order": 3},
                    {"id": "p-4", "name": "Apollo Pharmacy", "logoText": "Apollo Pharmacy", "active": True, "order": 4},
                    {"id": "p-5", "name": "IndiGo", "logoText": "IndiGo", "active": True, "order": 5},
                    {"id": "p-6", "name": "INZI Controls", "logoText": "INZI CONTROLS", "active": True, "order": 6},
                    {"id": "p-7", "name": "Dixon", "logoText": "Dixon", "active": True, "order": 7},
                    {"id": "p-8", "name": "COGENT", "logoText": "COGENT", "active": True, "order": 8},
                    {"id": "p-9", "name": "Indus", "logoText": "Indus", "active": True, "order": 9},
                    {"id": "p-10", "name": "NIIT", "logoText": "NIIT", "active": True, "order": 10},
                    {"id": "p-11", "name": "iSON", "logoText": "iSON", "active": True, "order": 11},
                    {"id": "p-12", "name": "Deccan", "logoText": "deccan", "active": True, "order": 12},
                    {"id": "p-13", "name": "ICICI Bank", "logoText": "ICICI Bank", "active": True, "order": 13},
                ]),
                stats_data=json.dumps([
                    {"id": "ab-stat-1", "label": "Registered Job Seekers", "value": "2,80,000+", "color": "var(--color-primary-600)"},
                    {"id": "ab-stat-2", "label": "Confirmed Placements", "value": "1,95,000+", "color": "var(--color-success-600)"},
                    {"id": "ab-stat-3", "label": "Verified Hiring Employers", "value": "14,200+", "color": "var(--color-warning-600)"},
                    {"id": "ab-stat-4", "label": "State-Wide Job Melas Held", "value": "24+", "color": "var(--color-info-600)"},
                ]),
                updated_by="System Seed",
            ))

        # Seed Job Mela Page Setting
        jm_stmt = select(JobMelaPageSetting).where(JobMelaPageSetting.id == "default")
        jm_res = await session.execute(jm_stmt)
        if not jm_res.scalar_one_or_none():
            session.add(JobMelaPageSetting(
                id="default",
                hero_badge="Nationwide Recruitment Drives",
                hero_heading="Mega Job Melas & Career Fairs",
                hero_description=(
                    "Attend on-ground walk-in interview sessions with 100+ hiring companies, "
                    "receive free career guidance, and get spot job offer letters. Free registration for all job seekers."
                ),
                updated_by="System Seed",
            ))

        # Seed Skill Development CMS Sections
        skill_defaults = {
            "skills_hero": {
                "title": "Hero Section — Top Banner",
                "content": {
                    "badge": "NTR VIKASA • Skill Development & Employment Generation",
                    "heading": "Skill Development & Training Programs",
                    "description": "Empowering job seekers with government-recognized, industry-aligned training, practical learning, and placement support.",
                    "exploreBtnText": "Explore Programs",
                    "viewCoursesBtnText": "View Courses",
                },
            },
            "skills_highlights": {
                "title": "Highlights — Trust Metrics",
                "content": [
                    {"id": "hl-1", "icon": "Award", "title": "Government Recognized", "subtitle": "NSDC / NSQF Certified"},
                    {"id": "hl-2", "icon": "TrendingUp", "title": "Placement Support", "subtitle": "Job Mela / Employment Support"},
                    {"id": "hl-3", "icon": "BookOpen", "title": "Practical Curriculum", "subtitle": "Hands-on Industry Labs"},
                    {"id": "hl-4", "icon": "Users", "title": "Expert Mentors", "subtitle": "Experienced Professionals"},
                ],
            },
            "skills_mission": {
                "title": "Institutional Mission — Mission & Pillars",
                "content": {
                    "badge": "Institutional Mission",
                    "heading": "Empowering Skills. Enabling Careers.",
                    "description": "The NTR VIKASA Skill Development initiative bridges the critical divide between academic qualifications and industry hiring standards. By partnering with state government bodies, national sector skill councils, and corporate employers, we deliver employment-focused, hands-on training to youth across Andhra Pradesh.",
                    "cards": [
                        {
                            "id": "es-1",
                            "icon": "Code2",
                            "title": "Industry-Relevant Learning",
                            "desc": "Curricula designed directly in consultation with tech leaders, BFSI corporations, and manufacturing employers to teach in-demand workplace tools."
                        },
                        {
                            "id": "es-2",
                            "icon": "Laptop",
                            "title": "Practical Training Labs",
                            "desc": "Over 70% of course time is dedicated to hands-on lab practicals, simulated industrial environments, and live capstone projects."
                        },
                        {
                            "id": "es-3",
                            "icon": "TrendingUp",
                            "title": "Placement Assistance",
                            "desc": "Trained candidates receive dedicated interview preparation, resume enhancement, and direct fast-track access to regional Mega Job Melas."
                        }
                    ],
                },
            },
            "skills_pathway": {
                "title": "Candidate Pathway — Training Journey",
                "content": {
                    "badge": "Candidate Pathway",
                    "heading": "From Training to Employment",
                    "description": "A structured 6-step journey designed to take you from foundational training to confirmed corporate placement.",
                    "steps": [
                        {"step": "01", "title": "Choose a Program", "desc": "Browse through high-demand domains like Tech, AI, Cloud, and BFSI to select the right skill track aligned with your career goals."},
                        {"step": "02", "title": "Register & Counseling", "desc": "Submit a free online enrollment request. Our skill counselors guide you through batch schedules, prerequisite review, and center allocation."},
                        {"step": "03", "title": "Hands-on Training", "desc": "Undergo practical, lab-based learning with experienced industry mentors, real-world capstone assignments, and modern equipment."},
                        {"step": "04", "title": "Get Certified", "desc": "Earn government-recognized NSDC, NSQF, and Sector Skill Council certifications validating your industry-ready competencies."},
                        {"step": "05", "title": "Placement Preparation", "desc": "Participate in resume enhancement sessions, technical interview simulations, soft skills coaching, and mock tests."},
                        {"step": "06", "title": "Employment & Job Melas", "desc": "Receive direct interview access to 14,000+ verified corporate recruiters and fast-track entry to statewide Mega Job Melas."},
                    ],
                },
            },
            "skills_advantages": {
                "title": "Why Choose NTR VIKASA — Institutional Excellence",
                "content": {
                    "badge": "Institutional Excellence",
                    "heading": "Why Choose NTR VIKASA",
                    "description": "Outcome-focused advantages designed to give candidates a real competitive edge in modern job markets.",
                    "cards": [
                        {"icon": "Award", "title": "Govt. & NSDC Recognized", "desc": "All programs follow National Skill Qualification Framework (NSQF) standards ensuring nationwide employer recognition."},
                        {"icon": "Laptop", "title": "70% Practical Lab Training", "desc": "Emphasis on experiential lab exercises, software simulations, and hardware setups rather than rote memorization."},
                        {"icon": "Users", "title": "Certified Expert Mentors", "desc": "Learn directly from seasoned industry practitioners and certified instructors with extensive domain track records."},
                        {"icon": "TrendingUp", "title": "100% Placement Support", "desc": "Direct pipeline to NTR VIKASA verified recruiters, corporate interview drives, and district-wide Mega Job Melas."},
                        {"icon": "ShieldCheck", "title": "100% Free / Subsidized", "desc": "State-sponsored skill development initiatives designed to empower aspiring job seekers across all districts of Andhra Pradesh."},
                        {"icon": "Sparkles", "title": "Future-Ready Curriculum", "desc": "Regularly updated course modules integrating modern AI tools, cloud platforms, and modern industrial requirements."},
                    ],
                },
            },
            "skills_programs": {
                "title": "Programs We Offer — Programs & Sectors",
                "content": {
                    "badge": "Sector Domains",
                    "heading": "Programs We Offer",
                    "description": "Specialized training pathways spanning modern tech, finance, core engineering, and administrative sectors.",
                    "categories": [
                        {"id": "it", "name": "Information Technology", "icon": "Code2", "desc": "Web development, cloud computing, and computer fundamentals", "count": "3 Courses"},
                        {"id": "data-ai", "name": "Data & AI", "icon": "Database", "desc": "Data analytics, Power BI dashboards, and business intelligence", "count": "2 Courses"},
                        {"id": "ai-tools", "name": "AI & Productivity Tools", "icon": "Sparkles", "desc": "ChatGPT prompt engineering, Gemini AI & office automation", "count": "2 Courses"},
                        {"id": "banking", "name": "Banking & Finance", "icon": "Landmark", "desc": "BFSI operations, retail banking, credit appraisal & compliance", "count": "2 Courses"},
                        {"id": "accounting", "name": "Office & Accounting", "icon": "Calculator", "desc": "Tally Prime, GST return filing, MS Office & Advanced Excel", "count": "2 Courses"},
                        {"id": "core-eng", "name": "Core Engineering", "icon": "Cpu", "desc": "PLC automation, SCADA systems, and industrial electrical wiring", "count": "2 Courses"},
                        {"id": "healthcare", "name": "Healthcare", "icon": "Activity", "desc": "Hospital administration, patient care, EMR systems & billing", "count": "2 Courses"},
                        {"id": "marketing", "name": "Marketing & Sales", "icon": "Megaphone", "desc": "Digital marketing, SEO, social media ads & customer support", "count": "2 Courses"},
                    ],
                },
            },
        }

        for sec_key, sec_data in skill_defaults.items():
            s_stmt = select(SkillCmsSection).where(SkillCmsSection.section_key == sec_key)
            s_res = await session.execute(s_stmt)
            if not s_res.scalar_one_or_none():
                session.add(SkillCmsSection(
                    section_key=sec_key,
                    title=sec_data["title"],
                    content=json.dumps(sec_data["content"]),
                    updated_by="System Seed",
                ))

        await session.commit()



async def init_db() -> None:
    """
    Database startup check and initial seed.
    """
    await check_db_connection()
    await seed_demo_users()
    await seed_candidate_saved_jobs()
    await seed_candidate_applications()
    await seed_candidate_notifications()
    await seed_recruiter_profile_and_dashboard_data()
    await seed_website_content()




