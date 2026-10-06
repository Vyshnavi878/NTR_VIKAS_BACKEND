import asyncio
import sys
sys.path.insert(0, ".")
from sqlalchemy import text
from app.database.session import AsyncSessionLocal

async def check():
    async with AsyncSessionLocal() as db:
        res = await db.execute(text("""
            SELECT cp.id as profile_id, cp.name, u.email, u.id as user_id
            FROM candidate_profiles cp
            JOIN users u ON cp.user_id = u.id
            WHERE u.email LIKE '%candidate1%' OR u.email LIKE '%priya%' OR cp.name LIKE '%Priya%' OR cp.name LIKE '%Vyshnavi%'
        """))
        for r in res.fetchall():
            print(dict(r._mapping))

if __name__ == "__main__":
    asyncio.run(check())
