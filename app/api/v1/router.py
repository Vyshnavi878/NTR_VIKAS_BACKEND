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
    candidate_job_melas,
    candidate_interviews,
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
    recruiter_interviews,
    recruiter_applications,
    recruiter_company,
    recruiter_settings,
    companies,
    admin_companies,
    admin_recruiters,
    admin_candidates,
    admin_profile,
    admin_settings,
    admin_audit_logs,
    admin_analytics,
    reports,
    admin_reports,
    admin_dashboard,
    admin_website_content,
    public_website_content,
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

# Candidate Job Melas & Registrations
api_router.include_router(candidate_job_melas.router)

# Candidate Interviews & Schedule
api_router.include_router(candidate_interviews.router)

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
api_router.include_router(admin_job_melas.admin_mela_approvals_router)
api_router.include_router(admin_job_melas.admin_mela_requests_router)

# Public & Candidate Job Melas
api_router.include_router(job_melas.router)
api_router.include_router(job_melas.router, prefix="/public")

# Recruiter Internships (/recruiters/internships and /recruiter/internships)
api_router.include_router(recruiter_internships.router)
api_router.include_router(recruiter_internships.recruiter_singular_router)

# Admin Internships Governance
api_router.include_router(admin_internships.router)
api_router.include_router(admin_internships.admin_internship_approvals_router)

# Public & Candidate Internships
api_router.include_router(internships.router)
api_router.include_router(internships.router, prefix="/public")

# Recruiter Jobs (/recruiters/jobs and /recruiter/jobs)
api_router.include_router(recruiter_jobs.router)
api_router.include_router(recruiter_jobs.recruiter_singular_router)

# Admin Jobs Governance
api_router.include_router(admin_jobs.router)
api_router.include_router(admin_jobs.admin_job_approvals_router)

# Public & Candidate Jobs
api_router.include_router(jobs.router)
api_router.include_router(jobs.router, prefix="/public")

# Public & Candidate Companies
api_router.include_router(companies.router)
api_router.include_router(companies.public_alias_router)

# Admin Companies Governance & Verification
api_router.include_router(admin_companies.router)
api_router.include_router(admin_companies.verification_alias_router)
api_router.include_router(admin_companies.singular_verification_alias_router)

# Admin Recruiters Governance & Management
api_router.include_router(admin_recruiters.router)
api_router.include_router(admin_recruiters.alias_router)

# Admin Candidates Governance & Management
api_router.include_router(admin_candidates.router)

# Recruiter Interviews (/recruiter/interviews and /recruiters/interviews)
api_router.include_router(recruiter_interviews.router)
api_router.include_router(recruiter_interviews.recruiters_plural_router)

# Recruiter Applications (/recruiter/applications and /recruiters/applications)
api_router.include_router(recruiter_applications.router)
api_router.include_router(recruiter_applications.recruiters_plural_router)

# Recruiter Company Profile
api_router.include_router(recruiter_company.router)

# Recruiter Settings & Preferences (/recruiter/settings)
api_router.include_router(recruiter_settings.router)

# Admin Profile & Identity (/admin/profile)
api_router.include_router(admin_profile.router)

# Admin Platform Settings (/admin/settings)
api_router.include_router(admin_settings.router)

# Admin Audit Logs (/admin/audit-logs)
api_router.include_router(admin_audit_logs.router)

# Admin Platform Analytics (/admin/analytics)
api_router.include_router(admin_analytics.router)

# User Grievance & Reports Submission (/reports)
api_router.include_router(reports.router)

# Admin Reports & Complaints Moderation (/admin/reports)
api_router.include_router(admin_reports.router)

# Admin Command Center Dashboard (/admin/dashboard)
api_router.include_router(admin_dashboard.router)

# Admin Website Content Management (/admin/website-content)
api_router.include_router(admin_website_content.router)

# Public Website Content (/public/website-content)
api_router.include_router(public_website_content.router)






