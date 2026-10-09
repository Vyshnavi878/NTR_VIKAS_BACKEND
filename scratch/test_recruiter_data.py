import asyncio
from app.database.session import AsyncSessionLocal
from sqlalchemy import text

async def check():
    async with AsyncSessionLocal() as db:
        res = await db.execute(text("SELECT u.id, u.email, u.is_active, rp.id, rp.recruiter_name, rp.company_name, rp.status FROM users u LEFT JOIN recruiter_profiles rp ON u.id = rp.user_id WHERE u.role = 'RECRUITER';"))
        for r in res.fetchall():
            print(r)

if __name__ == '__main__':
    asyncio.run(check())
