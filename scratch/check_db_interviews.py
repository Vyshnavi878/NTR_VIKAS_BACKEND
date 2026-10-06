import asyncio
import sys
sys.path.insert(0, ".")
from sqlalchemy import text
from app.database.session import AsyncSessionLocal

async def check():
    async with AsyncSessionLocal() as db:
        res = await db.execute(text("SELECT id, candidate_name, candidate_email, job_title, status, scheduled_date, start_time, end_time, recruiter_id, candidate_profile_id FROM interviews"))
        rows = res.fetchall()
        print(f"Total interviews in DB: {len(rows)}")
        for r in rows:
            print(dict(r._mapping))

if __name__ == "__main__":
    asyncio.run(check())
