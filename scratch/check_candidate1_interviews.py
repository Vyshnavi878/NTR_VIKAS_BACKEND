import asyncio
import sys
sys.path.insert(0, ".")
from sqlalchemy import text
from app.database.session import AsyncSessionLocal

async def check():
    async with AsyncSessionLocal() as db:
        res = await db.execute(text("""
            SELECT i.id, i.candidate_name, i.candidate_email, i.candidate_profile_id, i.job_title, i.round_name, i.status, i.scheduled_date, i.start_time, i.end_time, i.meeting_link, i.interviewer, i.interviewer_panel, i.notes, i.agenda_notes, i.recruiter_id, r.company_name
            FROM interviews i
            LEFT JOIN recruiter_profiles r ON i.recruiter_id = r.id
            WHERE i.candidate_profile_id = '24e74e8d-a22e-4133-9d50-2f16172a8ee3' 
               OR i.candidate_email = 'candidate1@ntrvikasa.com'
               OR i.candidate_name = 'Priya Sharma'
        """))
        rows = res.fetchall()
        print(f"Candidate1 matching interviews: {len(rows)}")
        for r in rows:
            print(dict(r._mapping))

if __name__ == "__main__":
    asyncio.run(check())
