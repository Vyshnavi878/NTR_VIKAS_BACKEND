import asyncio
import json
from sqlalchemy import text
from app.database.session import async_engine

async def seed():
    async with async_engine.begin() as conn:
        # 1. Update Priya Sharma (int-1)
        await conn.execute(text("""
            UPDATE interviews SET 
                date = '2026-09-10',
                scheduled_date = '2026-09-10',
                time = '11:00 AM - 12:00 PM IST',
                start_time = '11:00',
                end_time = '12:00',
                format = 'ONLINE',
                meeting_platform = 'Google Meet',
                meeting_link = 'https://meet.google.com/example',
                interviewer = 'Arjun Reddy & Deepak Verma (Architect)',
                interviewer_panel = '["Arjun Reddy", "Deepak Verma (Architect)"]',
                status = 'SCHEDULED',
                notes = 'Round 1: Component design system, React 19 features, state management, and code challenge.',
                agenda_notes = 'Round 1: Component design system, React 19 features, state management, and code challenge.',
                application_id = '9355cc07-d59a-40b4-8afd-caf234cfe95c'
            WHERE candidate_name = 'Priya Sharma';
        """))

        # 2. Update Rahul Kumar (int-2)
        await conn.execute(text("""
            UPDATE interviews SET 
                date = '2026-09-12',
                scheduled_date = '2026-09-12',
                time = '02:00 PM - 03:00 PM IST',
                start_time = '14:00',
                end_time = '15:00',
                format = 'ONLINE',
                meeting_platform = 'Google Meet',
                meeting_link = 'https://meet.google.com/example',
                interviewer = 'Arjun Reddy & Vikram Seth (VP Eng)',
                interviewer_panel = '["Arjun Reddy", "Vikram Seth (VP Eng)"]',
                status = 'SCHEDULED',
                notes = 'Round 1: FastAPI async workers, database indexing, caching strategies, and concurrency.',
                agenda_notes = 'Round 1: FastAPI async workers, database indexing, caching strategies, and concurrency.',
                application_id = '23965c54-61a0-4237-adcb-1131aad6446d'
            WHERE candidate_name = 'Rahul Kumar';
        """))

        # 3. Insert or update Vikram Sethi (int-3, COMPLETED)
        res = await conn.execute(text("SELECT id FROM interviews WHERE candidate_name = 'Vikram Sethi';"))
        existing_vikram = res.scalar()
        if not existing_vikram:
            await conn.execute(text("""
                INSERT INTO interviews (
                    id, interview_number, recruiter_id, candidate_profile_id, application_id, job_id,
                    candidate_name, candidate_email, job_title, round_name, interview_type,
                    date, time, scheduled_at, meeting_platform, meeting_link, interviewer,
                    status, notes, scheduled_date, start_time, end_time, timezone, format,
                    interviewer_panel, agenda_notes, completed_at, created_at, updated_at
                ) VALUES (
                    'int-3-vikram-sethi', 'INT-VIKRAM-003', '0d4407a6-2b51-4848-a92f-7b593d42c871',
                    '0042212d-b9b8-4a72-b746-21abddb21c40', '0cc1c564-6d26-4af6-a764-edb56ba84d38', 'job-103',
                    'Vikram Sethi', 'vikram.sethi@example.com', 'DevOps & Cloud Infrastructure Specialist',
                    'Technical Evaluation', 'Online (MS Teams)',
                    '2026-08-25', '04:00 PM - 05:00 PM IST', NOW(), 'MS Teams',
                    'https://teams.microsoft.com/example', 'Arjun Reddy',
                    'COMPLETED', 'Cleared technical screening with 9.2/10. Recommended for Senior Director offer stage.',
                    '2026-08-25', '16:00', '17:00', 'Asia/Kolkata', 'ONLINE',
                    '["Arjun Reddy"]', 'Cleared technical screening with 9.2/10. Recommended for Senior Director offer stage.',
                    '2026-08-25 17:00:00', NOW(), NOW()
                );
            """))
        else:
            await conn.execute(text("""
                UPDATE interviews SET 
                    date = '2026-08-25',
                    scheduled_date = '2026-08-25',
                    time = '04:00 PM - 05:00 PM IST',
                    start_time = '16:00',
                    end_time = '17:00',
                    format = 'ONLINE',
                    meeting_platform = 'MS Teams',
                    meeting_link = 'https://teams.microsoft.com/example',
                    interviewer = 'Arjun Reddy',
                    interviewer_panel = '["Arjun Reddy"]',
                    status = 'COMPLETED',
                    notes = 'Cleared technical screening with 9.2/10. Recommended for Senior Director offer stage.',
                    agenda_notes = 'Cleared technical screening with 9.2/10. Recommended for Senior Director offer stage.',
                    completed_at = '2026-08-25 17:00:00'
                WHERE candidate_name = 'Vikram Sethi';
            """))

        print("Seeding completed successfully!")

if __name__ == "__main__":
    asyncio.run(seed())
