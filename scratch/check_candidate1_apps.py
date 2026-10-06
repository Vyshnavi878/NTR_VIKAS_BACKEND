import asyncio
import sys
sys.path.insert(0, ".")
from sqlalchemy import text
from app.database.session import AsyncSessionLocal

async def check():
    async with AsyncSessionLocal() as db:
        res = await db.execute(text("""
            SELECT id, application_number, job_id, job_title, company_name, status, candidate_profile_id
            FROM candidate_applications
            WHERE candidate_profile_id = '24e74e8d-a22e-4133-9d50-2f16172a8ee3'
        """))
        for r in res.fetchall():
            print(dict(r._mapping))

if __name__ == "__main__":
    asyncio.run(check())
