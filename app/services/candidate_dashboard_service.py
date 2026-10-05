"""
Candidate Dashboard Service
Aggregates repository data into the CandidateDashboardResponse schema.

Profile Strength Calculation (deterministic, based on CandidateProfile fields):

  Item                      Weight   Field used
  ─────────────────────────────────────────────────────────────
  Basic contact info         25 %    name + phone (both set at reg)
  Email verified             15 %    user.email (always present)
  Qualification added        15 %    qualification_level (always set)
  Headline added             20 %    profile.headline
  Profile bio written        20 %    profile.bio (>= 10 chars)
  Village / address detail    5 %    profile.village
  ─────────────────────────────────────────────────────────────
  Total possible            100 %
"""
from typing import List
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.candidate import CandidateProfile
from app.repositories.candidate_dashboard_repository import CandidateDashboardRepository
from app.schemas.candidate_dashboard import (
    CandidateDashboardResponse,
    CandidateSummary,
    DashboardStatistics,
    ProfileStrength,
    ProfileStrengthItem,
)


# ── Profile Strength ──────────────────────────────────────────────────────────

def _calculate_profile_strength(profile: CandidateProfile) -> ProfileStrength:
    """
    Return a ProfileStrength object based only on fields that actually exist
    in the CandidateProfile table.
    """
    items: List[ProfileStrengthItem] = []
    total_weight = 0

    def _add(key: str, label: str, done: bool, weight: int) -> None:
        nonlocal total_weight
        items.append(ProfileStrengthItem(key=key, label=label, completed=done))
        if done:
            total_weight += weight

    # 1. Basic contact info — name & phone are set at registration (always done)
    contact_done = bool(profile.name and profile.name.strip()) and bool(profile.phone)
    _add("basic_info", "Basic contact information completed", contact_done, 25)

    # 2. Email verified — always true (email comes from the user record)
    _add("email_verified", "Email address verified", True, 15)

    # 3. Qualification added — always set (required at registration)
    qual_done = bool(profile.qualification_level and profile.qualification_level.strip())
    _add("qualification", "Education qualification added", qual_done, 15)

    # 4. Headline added
    headline_done = bool(profile.headline and len(profile.headline.strip()) >= 3)
    _add("headline", "Professional headline added", headline_done, 20)

    # 5. Bio / Professional summary
    bio_done = bool(profile.bio and len(profile.bio.strip()) >= 10)
    _add("bio", "Professional bio / summary written", bio_done, 20)

    # 6. Village / address details
    location_done = bool(profile.village and profile.village.strip())
    _add("location", "Village / address details added", location_done, 5)

    pct = min(total_weight, 100)

    if pct >= 90:
        label = "Expert Profile"
    elif pct >= 70:
        label = "Strong Profile"
    elif pct >= 50:
        label = "Good Profile"
    elif pct >= 30:
        label = "Getting Started"
    else:
        label = "Incomplete Profile"

    return ProfileStrength(percentage=pct, label=label, items=items)


# ── Dashboard Aggregation Service ─────────────────────────────────────────────

class CandidateDashboardService:

    @staticmethod
    async def get_dashboard(
        db: AsyncSession,
        current_user: User,
    ) -> CandidateDashboardResponse:
        """
        Aggregate all dashboard data for the authenticated candidate.
        Identity is taken strictly from the JWT-verified user — not from
        any query parameter supplied by the client.
        """
        # 1. Fetch candidate profile
        profile: CandidateProfile | None = (
            await CandidateDashboardRepository.get_candidate_profile(
                db, current_user.id
            )
        )
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    "Candidate profile not found. "
                    "Please complete your registration first."
                ),
            )

        candidate_summary = CandidateSummary(
            id=profile.id,
            full_name=profile.name,
            email=current_user.email,
            district=profile.district,
            mandal=profile.mandal,
            qualification_level=profile.qualification_level,
            headline=profile.headline,
        )

        # 2. Statistics (real queries once application tables exist)
        applied_count = await CandidateDashboardRepository.get_applied_jobs_count(
            db, profile.id
        )
        shortlisted_count = await CandidateDashboardRepository.get_shortlisted_count(
            db, profile.id
        )
        interviews_count = await CandidateDashboardRepository.get_interviews_count(
            db, profile.id
        )
        saved_count = await CandidateDashboardRepository.get_saved_jobs_count(
            db, profile.id
        )

        statistics = DashboardStatistics(
            applied_jobs=applied_count,
            shortlisted=shortlisted_count,
            interviews=interviews_count,
            saved_jobs=saved_count,
        )

        # 3. Recent Applications (newest-first, max 5)
        raw_apps = await CandidateDashboardRepository.get_recent_applications(
            db, profile.id, limit=5
        )

        # 4. Profile Strength
        profile_strength = _calculate_profile_strength(profile)

        # 5. Recommended Jobs
        raw_jobs = await CandidateDashboardRepository.get_recommended_jobs(
            db,
            candidate_profile_id=profile.id,
            qualification=profile.qualification_level,
            district=profile.district,
        )

        # 6. Upcoming Interviews
        raw_interviews = await CandidateDashboardRepository.get_upcoming_interviews(
            db, profile.id
        )

        return CandidateDashboardResponse(
            candidate=candidate_summary,
            statistics=statistics,
            recent_applications=raw_apps,
            profile_strength=profile_strength,
            recommended_jobs=raw_jobs,
            upcoming_interviews=raw_interviews,
        )
