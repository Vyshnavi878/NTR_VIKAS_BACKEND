import asyncio
from datetime import datetime, timezone, timedelta
from sqlalchemy import text
from app.database.session import async_engine

async def seed_reports():
    async with async_engine.begin() as conn:
        res = await conn.execute(text("SELECT COUNT(*) FROM reports;"))
        count = res.scalar() or 0
        if count >= 3:
            print(f"Reports table already has {count} records. Skipping seed.")
            return

        # Fetch candidate and recruiter user IDs
        cand_res = await conn.execute(text("SELECT id FROM users WHERE role = 'CANDIDATE' LIMIT 2;"))
        cand_ids = [row[0] for row in cand_res.fetchall()]
        
        rec_res = await conn.execute(text("SELECT id FROM users WHERE role = 'RECRUITER' LIMIT 2;"))
        rec_ids = [row[0] for row in rec_res.fetchall()]
        
        admin_res = await conn.execute(text("SELECT id FROM users WHERE role = 'ADMIN' LIMIT 1;"))
        admin_id = admin_res.scalar()

        reporter_1 = cand_ids[0] if cand_ids else admin_id
        reporter_2 = cand_ids[1] if len(cand_ids) > 1 else reporter_1
        reporter_3 = rec_ids[0] if rec_ids else admin_id
        
        reported_user_1 = rec_ids[0] if rec_ids else None
        reported_user_2 = rec_ids[1] if len(rec_ids) > 1 else reported_user_1
        reported_user_3 = cand_ids[0] if cand_ids else None

        now = datetime.now(timezone.utc)
        
        # 1. Job Scam / Fee Request (RESOLVED)
        await conn.execute(text("""
            INSERT INTO reports (
                id, report_number, report_type, reported_user_type, reported_user_id,
                reported_entity_type, reported_entity_id, reported_entity_name, reporter_user_id,
                subject, description, status, admin_notes, resolution_reason,
                resolved_by_admin_id, resolved_at, created_at, updated_at
            ) VALUES (
                'rep-1-seed-scam', 'REP-000001', 'JOB_SCAM', 'RECRUITER', :rep_user_1,
                'JOB', 'job-scam-1', 'Fast Cash Enterprises (Manoj Kumar)', :reporter_1,
                'Recruiter asking for registration fee',
                'Recruiter asked for Rs 500 registration fee before releasing interview schedule.',
                'RESOLVED', 'Recruiter account suspended and company blacklisted from platform.',
                'POLICY_VIOLATION_CONFIRMED', :admin_id, :resolved_1, :created_1, :created_1
            ) ON DUPLICATE KEY UPDATE id=id;
        """), {
            "rep_user_1": reported_user_1,
            "reporter_1": reporter_1,
            "admin_id": admin_id,
            "resolved_1": now - timedelta(days=40),
            "created_1": now - timedelta(days=42),
        })

        # 2. Misleading Job Description (RESOLVED)
        await conn.execute(text("""
            INSERT INTO reports (
                id, report_number, report_type, reported_user_type, reported_user_id,
                reported_entity_type, reported_entity_id, reported_entity_name, reporter_user_id,
                subject, description, status, admin_notes, resolution_reason,
                resolved_by_admin_id, resolved_at, created_at, updated_at
            ) VALUES (
                'rep-2-seed-mislead', 'REP-000002', 'MISLEADING_JOB_DESCRIPTION', 'RECRUITER', :rep_user_2,
                'JOB', 'job-mislead-2', 'AI Model Trainer (TechGlobal)', :reporter_2,
                'Misleading Job Description',
                'Listed as hybrid engineering job, but actually required door-to-door direct sales.',
                'RESOLVED', 'Job description corrected and employer warned.',
                'POLICY_VIOLATION_CONFIRMED', :admin_id, :resolved_2, :created_2, :created_2
            ) ON DUPLICATE KEY UPDATE id=id;
        """), {
            "rep_user_2": reported_user_2,
            "reporter_2": reporter_2,
            "admin_id": admin_id,
            "resolved_2": now - timedelta(days=35),
            "created_2": now - timedelta(days=37),
        })

        # 3. Profile Harassment in Messages (DISMISSED)
        await conn.execute(text("""
            INSERT INTO reports (
                id, report_number, report_type, reported_user_type, reported_user_id,
                reported_entity_type, reported_entity_id, reported_entity_name, reporter_user_id,
                subject, description, status, admin_notes, resolution_reason,
                dismissed_by_admin_id, dismissed_at, created_at, updated_at
            ) VALUES (
                'rep-3-seed-harass', 'REP-000003', 'PROFILE_HARASSMENT', 'CANDIDATE', :rep_user_3,
                'CANDIDATE_PROFILE', 'cand-409', 'Unverified Candidate ID #409', :reporter_3,
                'Profile Harassment in Messages',
                'Repeated offensive spam submissions through application portal.',
                'DISMISSED', 'Investigated portal logs; duplicate applications were due to network timeout, not harassment.',
                'INSUFFICIENT_EVIDENCE', :admin_id, :dismissed_3, :created_3, :created_3
            ) ON DUPLICATE KEY UPDATE id=id;
        """), {
            "rep_user_3": reported_user_3,
            "reporter_3": reporter_3,
            "admin_id": admin_id,
            "dismissed_3": now - timedelta(days=33),
            "created_3": now - timedelta(days=35),
        })

        print("Seeded 3 moderation reports successfully.")

if __name__ == "__main__":
    asyncio.run(seed_reports())
