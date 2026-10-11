import asyncio
from sqlalchemy import select, func, text
from app.database.session import AsyncSessionLocal
from app.models.user import User
from app.models.candidate import CandidateProfile
from app.models.recruiter import RecruiterProfile
from app.models.job import Job
from app.models.application import CandidateApplication
from app.models.interview import Interview
from app.models.saved_job import SavedJob
from app.models.notification import Notification
from app.models.website_content import GalleryPhoto, GalleryVideo, PressArticle, JobMelaPageSetting, SkillCmsSection, AboutUsSetting, JobPageSetting, JobLocation

async def main():
    async with AsyncSessionLocal() as session:
        user_res = await session.execute(select(User.email, User.role))
        users = user_res.all()
        print(f"Total Users: {len(users)}")
        for u in users:
            print(f"  User: {u[0]} ({u[1]})")

        jobs_res = await session.execute(select(Job.id, Job.title, Job.company_name))
        jobs = jobs_res.all()
        print(f"\nTotal Jobs: {len(jobs)}")
        for j in jobs[:10]:
            print(f"  Job: id={j[0]} title={j[1]} company={j[2]}")

        app_res = await session.execute(select(CandidateApplication.id, CandidateApplication.application_number, CandidateApplication.job_title))
        apps = app_res.all()
        print(f"\nTotal Applications: {len(apps)}")
        for a in apps[:10]:
            print(f"  App: id={a[0]} num={a[1]} title={a[2]}")

        int_res = await session.execute(select(Interview.id, Interview.job_title, Interview.candidate_name))
        interviews = int_res.all()
        print(f"\nTotal Interviews: {len(interviews)}")
        for i in interviews[:10]:
            print(f"  Interview: id={i[0]} title={i[1]} cand={i[2]}")

        gp_res = await session.execute(select(GalleryPhoto.id, GalleryPhoto.title))
        photos = gp_res.all()
        print(f"\nTotal GalleryPhotos: {len(photos)}")
        for p in photos:
            print(f"  Photo: {p[0]} - {p[1]}")

        gv_res = await session.execute(select(GalleryVideo.id, GalleryVideo.title))
        videos = gv_res.all()
        print(f"\nTotal GalleryVideos: {len(videos)}")
        for v in videos:
            print(f"  Video: {v[0]} - {v[1]}")

        pa_res = await session.execute(select(PressArticle.id, PressArticle.newspaper, PressArticle.title))
        articles = pa_res.all()
        print(f"\nTotal PressArticles: {len(articles)}")
        for pa in articles:
            print(f"  Article: {pa[0]} - {pa[1]} - {pa[2]}")

if __name__ == "__main__":
    asyncio.run(main())
