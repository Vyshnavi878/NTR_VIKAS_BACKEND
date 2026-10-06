import asyncio
import sys
from datetime import datetime, timezone, timedelta
sys.path.insert(0, ".")
from sqlalchemy import text
from app.database.session import AsyncSessionLocal

async def seed():
    async with AsyncSessionLocal() as db:
        # Check recruiter profile
        res = await db.execute(text("SELECT id, company_name FROM recruiter_profiles LIMIT 1"))
        recruiter = res.fetchone()
        if not recruiter:
            print("No recruiter profile found!")
            return
        recruiter_id = recruiter.id
        print(f"Using recruiter_id: {recruiter_id}")

        candidate_profile_id = "24e74e8d-a22e-4133-9d50-2f16172a8ee3"
        candidate_email = "candidate1@ntrvikasa.com"
        candidate_name = "Priya Sharma"

        # IST today
        ist = timezone(timedelta(hours=5, minutes=30))
        now_ist = datetime.now(ist)
        today_iso = now_ist.strftime("%Y-%m-%d")
        future_iso = (now_ist + timedelta(days=5)).strftime("%Y-%m-%d")
        past_iso = (now_ist - timedelta(days=15)).strftime("%Y-%m-%d")

        # Clean existing mock test interviews for candidate1
        await db.execute(text("DELETE FROM interviews WHERE candidate_profile_id = :cid OR candidate_email = :cemail"), {"cid": candidate_profile_id, "cemail": candidate_email})

        interviews_to_insert = [
            {
                "id": "INT-0001",
                "interview_number": "INT-2026-0001",
                "recruiter_id": recruiter_id,
                "candidate_profile_id": candidate_profile_id,
                "application_id": "fc7e835f-0c8a-4369-b07c-4ed8664f48de",
                "job_id": "2",
                "candidate_name": candidate_name,
                "candidate_email": candidate_email,
                "job_title": "Senior React Developer",
                "company_name": "Infosys Digital",
                "round_name": "Technical Round 1: React & Architecture",
                "interview_type": "Online (Google Meet)",
                "date": (now_ist + timedelta(days=5)).strftime("%d %b %Y"),
                "time": "11:00 AM - 12:00 PM IST",
                "scheduled_at": now_ist + timedelta(days=5),
                "scheduled_date": future_iso,
                "start_time": "11:00",
                "end_time": "12:00",
                "timezone": "Asia/Kolkata",
                "format": "ONLINE",
                "meeting_platform": "Google Meet",
                "meeting_link": "https://meet.google.com/abc-ntrv-xyz",
                "interviewer": "Deepak Verma (Principal Architect)",
                "interviewer_panel": '["Deepak Verma (Principal Architect)"]',
                "status": "SCHEDULED",
                "notes": "Please be ready with your code IDE and a working camera/microphone 10 minutes prior.",
                "agenda_notes": "Please be ready with your code IDE and a working camera/microphone 10 minutes prior.",
                "result": None,
            },
            {
                "id": "INT-0002",
                "interview_number": "INT-2026-0002",
                "recruiter_id": recruiter_id,
                "candidate_profile_id": candidate_profile_id,
                "application_id": "16051f28-3d07-41d4-8ac9-284b08572228",
                "job_id": "1",
                "candidate_name": candidate_name,
                "candidate_email": candidate_email,
                "job_title": "Senior Python Developer",
                "company_name": "TechCorp India",
                "round_name": "System Design & State Management Discussion",
                "interview_type": "Online (Google Meet)",
                "date": now_ist.strftime("%d %b %Y"),
                "time": "02:30 PM - 03:30 PM IST",
                "scheduled_at": now_ist,
                "scheduled_date": today_iso,
                "start_time": "14:30",
                "end_time": "15:30",
                "timezone": "Asia/Kolkata",
                "format": "ONLINE",
                "meeting_platform": "Google Meet",
                "meeting_link": "https://meet.google.com/def-tech-mno",
                "interviewer": "Ananya Roy (Director of Engineering)",
                "interviewer_panel": '["Ananya Roy (Director of Engineering)"]',
                "status": "SCHEDULED",
                "notes": "Discussion on distributed architectures, database caching strategies, and system reliability.",
                "agenda_notes": "Discussion on distributed architectures, database caching strategies, and system reliability.",
                "result": None,
            },
            {
                "id": "INT-0003",
                "interview_number": "INT-2026-0003",
                "recruiter_id": recruiter_id,
                "candidate_profile_id": candidate_profile_id,
                "application_id": "12910e4e-2244-42b6-a38a-778b08c0ca44",
                "job_id": "5",
                "candidate_name": candidate_name,
                "candidate_email": candidate_email,
                "job_title": "Frontend Developer (React)",
                "company_name": "TCS Innovation",
                "round_name": "Final Technical & Culture Fit Round",
                "interview_type": "Online (Google Meet)",
                "date": (now_ist - timedelta(days=15)).strftime("%d %b %Y"),
                "time": "10:00 AM - 11:00 AM IST",
                "scheduled_at": now_ist - timedelta(days=15),
                "scheduled_date": past_iso,
                "start_time": "10:00",
                "end_time": "11:00",
                "timezone": "Asia/Kolkata",
                "format": "ONLINE",
                "meeting_platform": "Google Meet",
                "meeting_link": "https://meet.google.com/ghi-tcsc-pqr",
                "interviewer": "Raghavan Iyer (Vice President of Talent)",
                "interviewer_panel": '["Raghavan Iyer (Vice President of Talent)"]',
                "status": "COMPLETED",
                "notes": "Final leadership interview. Candidate demonstrated outstanding culture fit and technical leadership.",
                "agenda_notes": "Final leadership interview. Candidate demonstrated outstanding culture fit and technical leadership.",
                "result": "Selected for Offer",
                "completed_at": now_ist - timedelta(days=15),
            }
        ]

        for item in interviews_to_insert:
            await db.execute(text("""
                INSERT INTO interviews (
                    id, interview_number, recruiter_id, candidate_profile_id, application_id,
                    job_id, candidate_name, candidate_email, job_title, company_name, round_name,
                    interview_type, date, time, scheduled_at, scheduled_date, start_time, end_time,
                    timezone, format, meeting_platform, meeting_link, interviewer, interviewer_panel,
                    status, notes, agenda_notes, result, completed_at, created_at, updated_at
                ) VALUES (
                    :id, :interview_number, :recruiter_id, :candidate_profile_id, :application_id,
                    :job_id, :candidate_name, :candidate_email, :job_title, :company_name, :round_name,
                    :interview_type, :date, :time, :scheduled_at, :scheduled_date, :start_time, :end_time,
                    :timezone, :format, :meeting_platform, :meeting_link, :interviewer, :interviewer_panel,
                    :status, :notes, :agenda_notes, :result, :completed_at, NOW(), NOW()
                )
            """), {
                **item,
                "completed_at": item.get("completed_at")
            })

        await db.commit()
        print("Successfully seeded candidate1 interviews!")

if __name__ == "__main__":
    asyncio.run(seed())
