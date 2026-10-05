"""add job enhancements and job_skills table

Revision ID: f1e2d3c4b5a6
Revises: a1b2c3d4e5f6
Create Date: 2026-10-05 21:05:00.000000

"""
from typing import Sequence, Union
from datetime import datetime, timezone
import uuid
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column


# revision identifiers, used by Alembic.
revision: str = 'f1e2d3c4b5a6'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add enhancement columns to jobs table
    op.add_column('jobs', sa.Column('job_number', sa.String(length=50), nullable=True))
    op.add_column('jobs', sa.Column('company_id', sa.String(length=50), nullable=True))
    op.add_column('jobs', sa.Column('created_by', sa.String(length=150), nullable=True))
    op.add_column('jobs', sa.Column('salary_min', sa.Integer(), nullable=True))
    op.add_column('jobs', sa.Column('salary_max', sa.Integer(), nullable=True))
    op.add_column('jobs', sa.Column('salary_currency', sa.String(length=10), server_default='INR', nullable=True))
    op.add_column('jobs', sa.Column('responsibilities', sa.Text(), nullable=True))
    op.add_column('jobs', sa.Column('requirements', sa.Text(), nullable=True))
    op.add_column('jobs', sa.Column('qualifications', sa.Text(), nullable=True))
    op.add_column('jobs', sa.Column('posted_at', sa.DateTime(), nullable=True))
    op.add_column('jobs', sa.Column('closed_at', sa.DateTime(), nullable=True))
    op.add_column('jobs', sa.Column('approved_by', sa.String(length=150), nullable=True))
    op.add_column('jobs', sa.Column('approved_at', sa.DateTime(), nullable=True))
    op.add_column('jobs', sa.Column('rejection_reason', sa.Text(), nullable=True))

    op.create_index(op.f('ix_jobs_job_number'), 'jobs', ['job_number'], unique=False)
    op.create_index(op.f('ix_jobs_company_id'), 'jobs', ['company_id'], unique=False)

    # 2. Create job_skills table
    op.create_table(
        'job_skills',
        sa.Column('id', sa.String(length=50), nullable=False),
        sa.Column('job_id', sa.String(length=50), nullable=False),
        sa.Column('skill_name', sa.String(length=100), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_job_skills_id'), 'job_skills', ['id'], unique=False)
    op.create_index(op.f('ix_job_skills_job_id'), 'job_skills', ['job_id'], unique=False)
    op.create_index(op.f('ix_job_skills_skill_name'), 'job_skills', ['skill_name'], unique=False)

    # 3. Data Migration: Update existing jobs with job_number, company_id, and details
    conn = op.get_bind()

    # Update job-101
    conn.execute(sa.text("""
        UPDATE jobs
        SET job_number = 'JOB-101',
            company_id = recruiter_id,
            salary_min = 1600000,
            salary_max = 2400000,
            salary = '₹16,00,000 - ₹24,00,000 / year',
            responsibilities = '• Architect and implement performant React UI components.\\n• Collaborate with product designers and backend API engineers.\\n• Mentor junior frontend developers and uphold testing standards.',
            requirements = '• 4+ years of hands-on React & TypeScript development.\\n• Deep knowledge of state management, bundling, and browser rendering optimization.\\n• Strong testing practices with Jest & React Testing Library.',
            qualifications = 'Bachelor\\'s Degree in Computer Science or equivalent practical experience.',
            posted_at = '2026-08-15 10:00:00'
        WHERE job_id = 'job-101' OR job_id = 'JOB-101'
    """))

    # Update job-102
    conn.execute(sa.text("""
        UPDATE jobs
        SET job_number = 'JOB-102',
            company_id = recruiter_id,
            salary_min = 1400000,
            salary_max = 2200000,
            salary = '₹14,00,000 - ₹22,00,000 / year',
            responsibilities = '• Build scalable API gateways and asynchronous task workers.\\n• Optimize database queries and caching layers in Redis.\\n• Deploy containerized services on AWS ECS & Kubernetes.',
            requirements = '• 3+ years experience with Python, FastAPI or Django.\\n• Strong database schema design skills in PostgreSQL.\\n• Experience with Docker, CI/CD pipelines, and AWS services.',
            qualifications = 'Bachelor\\'s Degree in IT / Computer Science.',
            posted_at = '2026-08-18 11:30:00'
        WHERE job_id = 'job-102' OR job_id = 'JOB-102'
    """))

    # Update job-103
    conn.execute(sa.text("""
        UPDATE jobs
        SET job_number = 'JOB-103',
            company_id = recruiter_id,
            status = 'CLOSED',
            closed_at = '2026-09-01 18:00:00',
            salary_min = 2000000,
            salary_max = 3000000,
            salary = '₹20,00,000 - ₹30,00,000 / year',
            responsibilities = '• Manage Terraform modules and GitOps pipelines in ArgoCD.\\n• Monitor telemetry across Prometheus, Grafana, and Datadog.\\n• Automate zero-downtime deployment pipelines.',
            requirements = '• Strong experience with AWS, Kubernetes, Terraform, and Docker.',
            qualifications = 'Bachelor\\'s Degree in Engineering.',
            posted_at = '2026-08-20 09:15:00'
        WHERE job_id = 'job-103' OR job_id = 'JOB-103'
    """))

    # Update job-104
    conn.execute(sa.text("""
        UPDATE jobs
        SET job_number = 'JOB-104',
            company_id = recruiter_id,
            status = 'PENDING',
            salary_min = 1800000,
            salary_max = 2600000,
            salary = '₹18,00,000 - ₹26,00,000 / year',
            responsibilities = '• Train, fine-tune, and deploy transformer models.\\n• Optimize model inference latency for edge devices.',
            requirements = '• PyTorch, TensorFlow, Hugging Face, Python, Vector DBs.',
            qualifications = 'Master\\'s or Bachelor\\'s in CS / AI.',
            posted_at = '2026-08-24 14:00:00'
        WHERE job_id = 'job-104' OR job_id = 'JOB-104'
    """))

    # Check and insert job-105 if not present
    res_105 = conn.execute(sa.text("SELECT id FROM jobs WHERE job_id = 'job-105' OR job_id = 'JOB-105'")).fetchone()
    if not res_105:
        # Get recruiter id for ABC Technologies
        rec = conn.execute(sa.text("SELECT id, company_name FROM recruiter_profiles LIMIT 1")).fetchone()
        rec_id = rec[0] if rec else '0d4407a6-2b51-4848-a92f-7b593d42c871'
        comp_name = rec[1] if rec else 'ABC Technologies Pvt Ltd'
        job_105_id = 'job-105-seed-uuid'
        conn.execute(sa.text(f"""
            INSERT INTO jobs (
                id, job_id, job_number, recruiter_id, company_id, company_name,
                title, department, job_type, work_mode, location, experience,
                salary, salary_min, salary_max, salary_currency, openings,
                status, description, responsibilities, requirements, qualifications,
                skills, deadline, created_at, updated_at
            ) VALUES (
                '{job_105_id}', 'job-105', 'JOB-105', '{rec_id}', '{rec_id}', '{comp_name}',
                'Associate Product Marketing Lead', 'Marketing & Growth', 'Full-time', 'On-site',
                'Bengaluru, Karnataka', '1-3 years', '₹8,00,000 - ₹12,00,000 / year', 800000, 1200000, 'INR', 1,
                'DRAFT', 'Draft position for B2B product marketing and campaign analytics.',
                '• Create collateral, case studies, and product release notes.',
                '• 2+ years B2B product marketing experience.',
                'MBA or Bachelor in Marketing/Communications.',
                'Product Marketing, Content Strategy, B2B Marketing, Growth Marketing', '2026-10-01',
                '2026-08-26 10:00:00', '2026-08-26 10:00:00'
            )
        """))

    # 4. Populate job_skills for all jobs
    job_skills_map = {
        'job-101': ['React.js', 'TypeScript', 'Next.js', 'Node.js', 'PostgreSQL', 'Docker'],
        'job-102': ['Python', 'FastAPI', 'PostgreSQL', 'Docker', 'AWS', 'Redis', 'Microservices'],
        'job-103': ['Kubernetes', 'AWS', 'Terraform', 'Docker', 'CI/CD', 'Prometheus'],
        'job-104': ['PyTorch', 'Python', 'Machine Learning', 'NLP', 'TensorFlow', 'LLMs'],
        'job-105': ['Product Marketing', 'Content Strategy', 'B2B Marketing', 'Growth Marketing'],
    }

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    for jid, skills in job_skills_map.items():
        row = conn.execute(sa.text(f"SELECT id FROM jobs WHERE job_id = '{jid}' OR job_number = '{jid.upper()}'")).fetchone()
        if row:
            db_job_id = row[0]
            for s in skills:
                skill_id = f"skill-{uuid.uuid4().hex[:10]}"
                conn.execute(sa.text(f"""
                    INSERT INTO job_skills (id, job_id, skill_name, created_at)
                    VALUES ('{skill_id}', '{db_job_id}', '{s}', '{now_str}')
                """))

    # 5. Populate candidate applications & interviews to match pipeline counts
    # JOB-101: 78 Applicants, 14 Shortlisted, 5 Interviews
    # JOB-102: 45 Applicants, 9 Shortlisted, 4 Interviews
    # JOB-103: 32 Applicants, 6 Shortlisted, 2 Interviews
    # JOB-104: 12 Applicants, 3 Shortlisted, 1 Interview
    # JOB-105: 0 Applicants, 0 Shortlisted, 0 Interviews
    cand_row = conn.execute(sa.text("SELECT id, user_id FROM candidate_profiles LIMIT 1")).fetchone()
    if cand_row:
        cand_id = cand_row[0]
        # Target counts: (job_id_str, total_apps, shortlisted_apps, interviews_count)
        targets = [
            ('job-101', 78, 14, 5, 'Senior Frontend Engineer (React / TypeScript)'),
            ('job-102', 45, 9, 4, 'Senior Python & Cloud Backend Developer'),
            ('job-103', 32, 6, 2, 'DevOps & Cloud Infrastructure Specialist'),
            ('job-104', 12, 3, 1, 'AI / ML Engineer — Computer Vision & NLP'),
        ]

        for target_jid, total_apps, num_shortlisted, num_interviews, jtitle in targets:
            # Check existing count
            current_apps = conn.execute(sa.text(f"SELECT COUNT(*) FROM candidate_applications WHERE job_id = '{target_jid}'")).scalar() or 0
            to_add_apps = total_apps - current_apps

            # Insert applications
            for i in range(to_add_apps):
                app_seq = current_apps + i + 1
                app_id = f"app-{target_jid}-{app_seq}-{uuid.uuid4().hex[:6]}"
                app_num = f"APP-{target_jid.upper()}-{app_seq:04d}"
                # Set status as SHORTLISTED for the first num_shortlisted, APPLIED for the rest
                app_status = 'SHORTLISTED' if (i < num_shortlisted) else 'APPLIED'
                conn.execute(sa.text(f"""
                    INSERT INTO candidate_applications (
                        id, application_number, candidate_profile_id, job_id,
                        job_title, company_name, location, employment_type,
                        work_mode, application_type, source, status, applied_date,
                        applied_at, created_at, updated_at
                    ) VALUES (
                        '{app_id}', '{app_num}', '{cand_id}', '{target_jid}',
                        '{jtitle}', 'ABC Technologies Pvt Ltd', 'Bengaluru, Karnataka',
                        'Full-time', 'Hybrid', 'Direct Job Application',
                        'NTR Vikasa Job Portal Direct', '{app_status}', '2026-08-25',
                        '{now_str}', '{now_str}', '{now_str}'
                    )
                """))

            # Populate interviews
            current_ints = conn.execute(sa.text(f"SELECT COUNT(*) FROM interviews WHERE job_id = '{target_jid}'")).scalar() or 0
            to_add_ints = num_interviews - current_ints
            for j in range(to_add_ints):
                int_seq = current_ints + j + 1
                int_id = f"int-{target_jid}-{int_seq}-{uuid.uuid4().hex[:6]}"
                int_num = f"INTV-{target_jid.upper()}-{int_seq:03d}"
                conn.execute(sa.text(f"""
                    INSERT INTO interviews (
                        id, interview_number, recruiter_id, candidate_profile_id,
                        job_id, candidate_name, candidate_email, job_title,
                        round_name, interview_type, scheduled_at, meeting_platform,
                        status, created_at, updated_at
                    ) VALUES (
                        '{int_id}', '{int_num}', '0d4407a6-2b51-4848-a92f-7b593d42c871',
                        '{cand_id}', '{target_jid}', 'Candidate {int_seq}',
                        'candidate{int_seq}@example.com', '{jtitle}',
                        'Technical Round 1', 'Online (Google Meet)', '{now_str}',
                        'Google Meet', 'SCHEDULED', '{now_str}', '{now_str}'
                    )
                """))


def downgrade() -> None:
    op.drop_table('job_skills')
    op.drop_index(op.f('ix_jobs_company_id'), table_name='jobs')
    op.drop_index(op.f('ix_jobs_job_number'), table_name='jobs')
    op.drop_column('jobs', 'rejection_reason')
    op.drop_column('jobs', 'approved_at')
    op.drop_column('jobs', 'approved_by')
    op.drop_column('jobs', 'closed_at')
    op.drop_column('jobs', 'posted_at')
    op.drop_column('jobs', 'qualifications')
    op.drop_column('jobs', 'requirements')
    op.drop_column('jobs', 'responsibilities')
    op.drop_column('jobs', 'salary_currency')
    op.drop_column('jobs', 'salary_max')
    op.drop_column('jobs', 'salary_min')
    op.drop_column('jobs', 'created_by')
    op.drop_column('jobs', 'company_id')
    op.drop_column('jobs', 'job_number')
