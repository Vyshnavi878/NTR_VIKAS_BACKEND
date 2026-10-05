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

