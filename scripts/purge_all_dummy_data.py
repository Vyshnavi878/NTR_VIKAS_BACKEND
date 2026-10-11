import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath("."))

from sqlalchemy import select, delete, text
from app.database.session import AsyncSessionLocal
from app.models import (
    User, AdminProfile, RecruiterProfile, CandidateProfile,
    Job, JobSkill, Internship, InternshipApplication,
    CandidateApplication, ApplicationTimelineEvent,
    JobMela, JobMelaCompanyParticipation, JobMelaJobOpening, JobMelaRequest, JobMelaRegistration,
    CompanyMember, CompanyInvitation, RecruiterNotificationPreference,
    PressArticle, GalleryPhoto, GalleryVideo,
    SavedJob, Notification, SupportTicket, Interview, RecruiterSupportRequest,
    CandidateSkill, CandidateExperience, CandidateEducation, CandidateCertification,
    CandidateProject, CandidateResume, CandidateSettings,
    JobLocation, WebsiteSectionHeader, JobPageSetting, AboutUsSetting,
    JobMelaPageSetting, SkillCmsSection, PlatformSettings
)

PRESERVED_ADMIN_EMAILS = {"admin1@ntrvikasa.com", "admin2@ntrvikasa.com"}


async def purge():
    async with AsyncSessionLocal() as session:
        print("=== PURGING DUMMY / SEED DATA FROM MYSQL ===")

        # 1. Purge Job Melas & Participations
        await session.execute(delete(JobMelaJobOpening))
        await session.execute(delete(JobMelaCompanyParticipation))
        await session.execute(delete(JobMelaRegistration))
        await session.execute(delete(JobMelaRequest))
        await session.execute(delete(JobMela))
        print("[OK] Purged job_melas, participations, openings, requests, registrations")

        # 2. Purge Applications & Interviews
        await session.execute(delete(ApplicationTimelineEvent))
        await session.execute(delete(CandidateApplication))
        await session.execute(delete(InternshipApplication))
        await session.execute(delete(Interview))
        print("[OK] Purged applications, events, and interviews")

        # 3. Purge Jobs & Internships
        await session.execute(delete(JobSkill))
        await session.execute(delete(SavedJob))
        await session.execute(delete(Job))
        await session.execute(delete(Internship))
        print("[OK] Purged jobs and internships")

        # 4. Purge Recruiter Profiles and Teams
        await session.execute(delete(CompanyMember))
        await session.execute(delete(CompanyInvitation))
        await session.execute(delete(RecruiterNotificationPreference))
        await session.execute(delete(RecruiterSupportRequest))
        await session.execute(delete(RecruiterProfile))
        print("[OK] Purged recruiter profiles and team records")

        # 5. Purge Candidate Profile Details & Profiles
        await session.execute(delete(CandidateSkill))
        await session.execute(delete(CandidateExperience))
        await session.execute(delete(CandidateEducation))
        await session.execute(delete(CandidateCertification))
        await session.execute(delete(CandidateProject))
        await session.execute(delete(CandidateResume))
        await session.execute(delete(CandidateSettings))
        await session.execute(delete(CandidateProfile))
        print("[OK] Purged candidate profiles and details")

        # 6. Purge Notifications and Support Tickets
        await session.execute(delete(Notification))
        await session.execute(delete(SupportTicket))
        print("[OK] Purged notifications and support tickets")

        # 7. Purge Press and Gallery entries
        await session.execute(delete(PressArticle))
        await session.execute(delete(GalleryPhoto))
        await session.execute(delete(GalleryVideo))
        print("[OK] Purged press articles, gallery photos, and videos")

        # 8. Purge all Non-Admin Users
        all_users = (await session.execute(select(User))).scalars().all()
        deleted_users_count = 0
        for u in all_users:
            if u.email.strip().lower() not in PRESERVED_ADMIN_EMAILS:
                await session.delete(u)
                deleted_users_count += 1
        print(f"[OK] Purged {deleted_users_count} non-admin dummy users")

        await session.commit()
        print("=== PURGE COMPLETED SUCCESSFULLY ===")

        # Verify Remaining Data
        remaining_users = (await session.execute(select(User))).scalars().all()
        print(f"Remaining Users ({len(remaining_users)}):")
        for u in remaining_users:
            print(f"  - {u.id}: {u.email} ({u.role})")

        rec_cnt = (await session.execute(select(RecruiterProfile))).scalars().all()
        print(f"Remaining Recruiter Profiles: {len(rec_cnt)}")

        mela_cnt = (await session.execute(select(JobMela))).scalars().all()
        print(f"Remaining Job Melas: {len(mela_cnt)}")

        press_cnt = (await session.execute(select(PressArticle))).scalars().all()
        print(f"Remaining Press Articles: {len(press_cnt)}")

        loc_cnt = (await session.execute(select(JobLocation))).scalars().all()
        print(f"Preserved Job Locations: {len(loc_cnt)}")


if __name__ == "__main__":
    asyncio.run(purge())
