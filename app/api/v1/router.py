from fastapi import APIRouter
from app.api.v1.endpoints import (
    auth,
    candidate_dashboard,
    candidate_profile,
    saved_jobs,
    candidate_applications,
    candidate_support,
    candidate_settings,
    notifications,
    recruiter_dashboard,
    recruiter_support,
    recruiter_analytics,
    recruiter_job_melas,
    admin_job_melas,
    job_melas,
    recruiter_internships,
    admin_internships,
    internships,
    recruiter_jobs,
    admin_jobs,
    jobs,
)

api_router = APIRouter()

# Authentication & Registration
api_router.include_router(auth.router)

# Candidate Dashboard
api_router.include_router(candidate_dashboard.router)

# Candidate Profile
api_router.include_router(candidate_profile.router)

# Candidate Saved Jobs
api_router.include_router(saved_jobs.router)

# Candidate Applications
api_router.include_router(candidate_applications.router)

# Candidate Help & Support Tickets
api_router.include_router(candidate_support.router)

# Candidate Settings & Privacy
api_router.include_router(candidate_settings.router)

# Candidate Notifications
api_router.include_router(notifications.router)

# Recruiter Dashboard
api_router.include_router(recruiter_dashboard.router)

# Recruiter Help & Support
api_router.include_router(recruiter_support.router)

# Recruiter Hiring Analytics
api_router.include_router(recruiter_analytics.router)

# Recruiter Job Melas Participation
api_router.include_router(recruiter_job_melas.router)

# Admin Job Melas Participation Reviews
api_router.include_router(admin_job_melas.router)

# Public & Candidate Job Melas
api_router.include_router(job_melas.router)

# Recruiter Internships (/recruiters/internships and /recruiter/internships)
api_router.include_router(recruiter_internships.router)
api_router.include_router(recruiter_internships.recruiter_singular_router)

# Admin Internships Governance
api_router.include_router(admin_internships.router)

# Public & Candidate Internships
api_router.include_router(internships.router)

# Recruiter Jobs (/recruiters/jobs and /recruiter/jobs)
api_router.include_router(recruiter_jobs.router)
api_router.include_router(recruiter_jobs.recruiter_singular_router)

# Admin Jobs Governance
api_router.include_router(admin_jobs.router)

# Public & Candidate Jobs
api_router.include_router(jobs.router)



