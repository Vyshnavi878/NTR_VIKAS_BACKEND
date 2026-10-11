import asyncio
from sqlalchemy import select, delete, or_
from app.database.session import AsyncSessionLocal
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
from app.models.website_content import GalleryPhoto, GalleryVideo, PressArticle

DEMO_USER_EMAILS = [
    "candidate1@ntrvikasa.com",
    "candidate2@ntrvikasa.com",
    "recruiter1@ntrvikasa.com",
    "recruiter2@ntrvikasa.com",
]

DEMO_PHOTO_IDS = ["img-1", "img-2", "img-3", "img-4", "img-5", "img-6"]
DEMO_VIDEO_IDS = ["vid-1", "vid-2", "vid-3"]
DEMO_PRESS_IDS = ["news-1", "news-2", "news-3", "news-4"]
DEMO_JOB_IDS = ["job-101", "job-102", "job-103", "job-104"]

PROTECTED_ADMIN_EMAILS = ["admin1@ntrvikasa.com", "admin2@ntrvikasa.com"]

async def run_cleanup():
    print("=" * 60)
    print("Starting NTR Vikasa Safe Database Cleanup...")
    print("=" * 60)

    async with AsyncSessionLocal() as session:
        # 1. Identify dummy & test users to delete
        stmt_users = select(User).where(
            or_(
                User.email.in_(DEMO_USER_EMAILS),
                User.email.like("settings_test_%"),
                User.email.like("notif_tester_%"),
                User.email.like("dyn_cand_%"),
                User.email.like("cand_test_%"),
                User.email.like("inactive_%"),
                User.email.like("reset_test_%"),
                User.email.like("test_%@%"),
                User.email.like("live_%@%"),
                User.email.like("e2e_%@%"),
                User.email.like("pooja_%@abctech.example.com"),
                User.email.like("newhire_%@abctech.com"),
                User.email.like("fresh_test_%"),
                User.email.like("recruiter.%@ntrvikasa.com"),
            )
        )
        res_users = await session.execute(stmt_users)
        users_to_delete = [u for u in res_users.scalars().all() if u.email not in PROTECTED_ADMIN_EMAILS and u.role != "ADMIN"]
        user_ids = [u.id for u in users_to_delete]
        user_emails = [u.email for u in users_to_delete]
        print(f"Found {len(users_to_delete)} dummy/test users to purge:")
        for em in user_emails[:10]:
            print(f"  - {em}")
        if len(user_emails) > 10:
            print(f"  ... and {len(user_emails) - 10} more.")

        # 2. Identify candidate profiles
        res_cands = await session.execute(select(CandidateProfile).where(CandidateProfile.user_id.in_(user_ids)))
        cand_profiles = res_cands.scalars().all()
        cand_ids = [c.id for c in cand_profiles]
        print(f"Found {len(cand_profiles)} candidate profiles associated with dummy users.")

        # 3. Identify recruiter profiles
        res_recs = await session.execute(select(RecruiterProfile).where(RecruiterProfile.user_id.in_(user_ids)))
        rec_profiles = res_recs.scalars().all()
        rec_ids = [r.id for r in rec_profiles]
        print(f"Found {len(rec_profiles)} recruiter profiles associated with dummy users.")

        # 4. Identify dummy jobs
        res_jobs = await session.execute(
            select(Job).where(
                or_(
                    Job.recruiter_id.in_(rec_ids),
                    Job.id.in_(DEMO_JOB_IDS),
                    Job.title.like("%Requisition Role%"),
                )
            )
        )
        jobs_to_delete = res_jobs.scalars().all()
        job_ids = [j.id for j in jobs_to_delete]
        print(f"Found {len(jobs_to_delete)} dummy jobs to purge.")

        # 5. Identify applications
        res_apps = await session.execute(
            select(CandidateApplication).where(
                or_(
                    CandidateApplication.candidate_profile_id.in_(cand_ids),
                    CandidateApplication.job_id.in_(job_ids),
                )
            )
        )
        apps_to_delete = res_apps.scalars().all()
        app_ids = [a.id for a in apps_to_delete]
        print(f"Found {len(apps_to_delete)} applications to purge.")

        # 6. Delete Application Timeline Events
        if app_ids:
            res_del_tl = await session.execute(
                delete(ApplicationTimelineEvent).where(ApplicationTimelineEvent.application_id.in_(app_ids))
            )
            print(f"Deleted {res_del_tl.rowcount} application timeline events.")

        # 7. Delete Applications
        if app_ids:
            res_del_apps = await session.execute(
                delete(CandidateApplication).where(CandidateApplication.id.in_(app_ids))
            )
            print(f"Deleted {res_del_apps.rowcount} candidate applications.")

        # 8. Delete Interviews
        res_del_ints = await session.execute(
            delete(Interview).where(
                or_(
                    Interview.job_id.in_(job_ids),
                    Interview.recruiter_id.in_(rec_ids),
                    Interview.id == "INT-0001",
                )
            )
        )
        print(f"Deleted {res_del_ints.rowcount} interviews.")

        # 9. Delete Saved Jobs
        if cand_ids:
            res_del_sj = await session.execute(
                delete(SavedJob).where(SavedJob.candidate_profile_id.in_(cand_ids))
            )
            print(f"Deleted {res_del_sj.rowcount} saved jobs.")

        # 10. Delete Candidate Notifications
        if cand_ids:
            res_del_notif = await session.execute(
                delete(Notification).where(Notification.candidate_id.in_(cand_ids))
            )
            print(f"Deleted {res_del_notif.rowcount} notifications.")

        # 11. Delete Candidate Profile Details
        if cand_ids:
            await session.execute(delete(CandidateSkill).where(CandidateSkill.candidate_profile_id.in_(cand_ids)))
            await session.execute(delete(CandidateExperience).where(CandidateExperience.candidate_profile_id.in_(cand_ids)))
            await session.execute(delete(CandidateEducation).where(CandidateEducation.candidate_profile_id.in_(cand_ids)))
            await session.execute(delete(CandidateCertification).where(CandidateCertification.candidate_profile_id.in_(cand_ids)))
            await session.execute(delete(CandidateProject).where(CandidateProject.candidate_profile_id.in_(cand_ids)))
            await session.execute(delete(CandidateResume).where(CandidateResume.candidate_profile_id.in_(cand_ids)))
            print(f"Deleted profile sub-entities (skills, experiences, education, certs, projects, resumes).")

        # 12. Delete Candidate Profiles
        if cand_ids:
            res_del_cp = await session.execute(
                delete(CandidateProfile).where(CandidateProfile.id.in_(cand_ids))
            )
            print(f"Deleted {res_del_cp.rowcount} candidate profiles.")

        # 13. Delete Jobs
        if job_ids:
            res_del_jobs = await session.execute(
                delete(Job).where(Job.id.in_(job_ids))
            )
            print(f"Deleted {res_del_jobs.rowcount} jobs.")

        # 14. Delete Recruiter Profiles
        if rec_ids:
            res_del_rp = await session.execute(
                delete(RecruiterProfile).where(RecruiterProfile.id.in_(rec_ids))
            )
            print(f"Deleted {res_del_rp.rowcount} recruiter profiles.")

        # 15. Delete Users
        if user_ids:
            res_del_users = await session.execute(
                delete(User).where(User.id.in_(user_ids))
            )
            print(f"Deleted {res_del_users.rowcount} dummy/test users.")

        # 16. Delete Demo Media & Press records
        res_del_p = await session.execute(
            delete(GalleryPhoto).where(GalleryPhoto.id.in_(DEMO_PHOTO_IDS))
        )
        print(f"Deleted {res_del_p.rowcount} demo gallery photos.")

        res_del_v = await session.execute(
            delete(GalleryVideo).where(GalleryVideo.id.in_(DEMO_VIDEO_IDS))
        )
        print(f"Deleted {res_del_v.rowcount} demo gallery videos.")

        res_del_pr = await session.execute(
            delete(PressArticle).where(PressArticle.id.in_(DEMO_PRESS_IDS))
        )
        print(f"Deleted {res_del_pr.rowcount} demo press articles.")

        await session.commit()
        print("=" * 60)
        print("Database cleanup completed successfully!")
        print("=" * 60)

if __name__ == "__main__":
    asyncio.run(run_cleanup())
