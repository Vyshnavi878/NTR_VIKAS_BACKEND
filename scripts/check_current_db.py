import asyncio
import sys
import os
sys.path.insert(0, os.path.abspath("."))
from sqlalchemy import select
from app.database.session import AsyncSessionLocal
from app.models import PressArticle, GalleryPhoto, GalleryVideo, JobMela, RecruiterProfile, User

async def main():
    async with AsyncSessionLocal() as session:
        press = (await session.execute(select(PressArticle))).scalars().all()
        print(f"PressArticles: {len(press)}")
        for p in press:
            print(f"  Press: id={p.id}, date={p.date}, paper={p.newspaper}")

        photos = (await session.execute(select(GalleryPhoto))).scalars().all()
        print(f"GalleryPhotos: {len(photos)}")
        for ph in photos:
            print(f"  Photo: id={ph.id}, title={ph.title}")

        videos = (await session.execute(select(GalleryVideo))).scalars().all()
        print(f"GalleryVideos: {len(videos)}")
        for v in videos:
            print(f"  Video: id={v.id}, title={v.title}")

if __name__ == "__main__":
    asyncio.run(main())
