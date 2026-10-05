"""add job_melas and company participations

Revision ID: e382fa761b09
Revises: d719fa9921b0
Create Date: 2026-10-05 20:30:00.000000

"""
from typing import Sequence, Union
from datetime import datetime, timezone
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e382fa761b09'
down_revision: Union[str, Sequence[str], None] = 'd719fa9921b0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create job_melas table
    op.create_table(
        'job_melas',
        sa.Column('id', sa.String(length=50), nullable=False),
        sa.Column('mela_number', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('event_date', sa.String(length=50), nullable=False),
        sa.Column('start_time', sa.String(length=50), nullable=True, server_default='09:00 AM'),
        sa.Column('end_time', sa.String(length=50), nullable=True, server_default='05:30 PM'),
        sa.Column('venue', sa.String(length=255), nullable=False),
        sa.Column('city', sa.String(length=100), nullable=False),
        sa.Column('district', sa.String(length=100), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='PUBLISHED'),
        sa.Column('created_by', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('mela_number'),
    )
    op.create_index(op.f('ix_job_melas_id'), 'job_melas', ['id'], unique=False)
    op.create_index(op.f('ix_job_melas_mela_number'), 'job_melas', ['mela_number'], unique=True)
    op.create_index(op.f('ix_job_melas_title'), 'job_melas', ['title'], unique=False)
    op.create_index(op.f('ix_job_melas_event_date'), 'job_melas', ['event_date'], unique=False)
    op.create_index(op.f('ix_job_melas_city'), 'job_melas', ['city'], unique=False)
    op.create_index(op.f('ix_job_melas_district'), 'job_melas', ['district'], unique=False)
    op.create_index(op.f('ix_job_melas_status'), 'job_melas', ['status'], unique=False)

    # 2. Create job_mela_company_participations table
    op.create_table(
        'job_mela_company_participations',
        sa.Column('id', sa.String(length=50), nullable=False),
        sa.Column('job_mela_id', sa.String(length=50), nullable=False),
        sa.Column('company_id', sa.String(length=50), nullable=False),
        sa.Column('openings', sa.Text(), nullable=True),
        sa.Column('target_hires', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='PENDING'),
        sa.Column('booth_number', sa.String(length=100), nullable=True),
        sa.Column('booth_location', sa.String(length=255), nullable=True),
        sa.Column('registered_at', sa.DateTime(), nullable=False),
        sa.Column('approved_at', sa.DateTime(), nullable=True),
        sa.Column('approved_by', sa.String(length=150), nullable=True),
        sa.Column('rejected_at', sa.DateTime(), nullable=True),
        sa.Column('rejected_by', sa.String(length=150), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['recruiter_profiles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['job_mela_id'], ['job_melas.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('job_mela_id', 'company_id', name='uq_mela_company_participation'),
    )
    op.create_index(op.f('ix_job_mela_company_participations_id'), 'job_mela_company_participations', ['id'], unique=False)
    op.create_index(op.f('ix_job_mela_company_participations_job_mela_id'), 'job_mela_company_participations', ['job_mela_id'], unique=False)
    op.create_index(op.f('ix_job_mela_company_participations_company_id'), 'job_mela_company_participations', ['company_id'], unique=False)
    op.create_index(op.f('ix_job_mela_company_participations_status'), 'job_mela_company_participations', ['status'], unique=False)

    # 3. Seed canonical Job Melas
    now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    melas = [
        ("mela-1", "MELA-AP-01", "Bengaluru Mega IT & Cloud Career Expo 2026", "BIEC Exhibition Grounds, Tumkur Road, Hall 3", "Bengaluru", "Karnataka", "2026-09-18", "09:00 AM", "06:00 PM", "PUBLISHED"),
        ("mela-2", "MELA-AP-02", "AP Mega IT & Engineering Job Mela 2026", "AU Convention Center, Beach Road", "Visakhapatnam", "Visakhapatnam", "2026-10-05", "09:00 AM", "05:30 PM", "PUBLISHED"),
        ("mela-3", "MELA-AP-03", "Vijayawada Capital Region Mega Career Mela 2026", "Swarna Bharathi Indoor Stadium, MG Road", "Vijayawada", "NTR", "2026-10-12", "09:00 AM", "06:00 PM", "PUBLISHED"),
        ("mela-4", "MELA-AP-04", "Tirupati Rayalaseema Tech & Skills Summit", "SV University Auditorium Complex", "Tirupati", "Tirupati", "2026-10-19", "09:30 AM", "05:00 PM", "PUBLISHED"),
        ("mela-5", "MELA-AP-05", "Guntur & Amaravati District Employment Drive", "Acharya Nagarjuna University Campus Grounds", "Guntur", "Guntur", "2026-10-25", "09:00 AM", "05:00 PM", "PUBLISHED"),
        ("mela-6", "MELA-AP-06", "Hyderabad Cyberabad Tech Talent Fair 2026", "HITEX Exhibition Center, Hitec City, Hall 2", "Hyderabad", "Telangana", "2026-11-02", "09:00 AM", "06:00 PM", "PUBLISHED"),
        ("mela-7", "MELA-AP-07", "Kakinada Godavari Coastal IT Job Drive", "JNTU Kakinada Indoor Sports Arena", "Kakinada", "Kakinada", "2026-11-09", "09:30 AM", "05:30 PM", "PUBLISHED"),
        ("mela-8", "MELA-AP-08", "Kurnool District Youth Career Summit 2026", "Rayalaseema University Multi-Purpose Hall", "Kurnool", "Kurnool", "2026-11-15", "09:00 AM", "05:00 PM", "PUBLISHED"),
        ("mela-9", "MELA-AP-09", "Nellore Coastal Tech & Engineering Fair", "V.R. High School Grounds, Trunk Road", "Nellore", "Nellore", "2026-11-22", "09:00 AM", "05:00 PM", "PUBLISHED"),
        ("mela-10", "MELA-AP-10", "Anantapur District Skills & Placement Expo", "JNTU Anantapur College of Engineering Grounds", "Anantapur", "Anantapur", "2026-11-29", "09:00 AM", "05:00 PM", "PUBLISHED"),
        ("mela-11", "MELA-AP-11", "Rajahmundry Godavari Tech Job Expo 2026", "GIET University Campus Convention Center", "Rajahmundry", "East Godavari", "2026-12-05", "09:30 AM", "05:30 PM", "PUBLISHED"),
        ("mela-12", "MELA-AP-12", "Kadapa District Employment & Skill Drive", "YSR Engineering College Stadium Complex", "Kadapa", "YSR", "2026-12-12", "09:00 AM", "05:00 PM", "PUBLISHED"),
        ("mela-13", "MELA-AP-13", "Visakhapatnam IT & FinTech Job Fair 2026", "Andhra University Convention Hall, Vizag", "Visakhapatnam", "Visakhapatnam", "2026-10-18", "09:00 AM", "05:30 PM", "PUBLISHED"),
        ("mela-14", "MELA-AP-14", "Tirupati Rayalaseema Mega Employment Drive", "SV University Indoor Stadium, Tirupati", "Tirupati", "Tirupati", "2026-10-22", "09:30 AM", "05:00 PM", "PUBLISHED"),
        ("mela-15", "MELA-AP-15", "Guntur & Amaravati Skills & Tech Expo", "Acharya Nagarjuna University Open Grounds", "Guntur", "Guntur", "2026-10-28", "09:00 AM", "05:00 PM", "PUBLISHED"),
    ]

    for m_id, num, title, venue, city, dist, dt, st, et, stat in melas:
        op.execute(
            f"INSERT INTO job_melas (id, mela_number, title, venue, city, district, event_date, start_time, end_time, status, created_at, updated_at) "
            f"VALUES ('{m_id}', '{num}', '{title}', '{venue}', '{city}', '{dist}', '{dt}', '{st}', '{et}', '{stat}', '{now}', '{now}')"
        )

    # 4. Seed participations for Recruiter 1 (ABC Technologies)
    # Check if recruiter profile exists in recruiter_profiles
    op.execute(
        f"""
        INSERT INTO job_mela_company_participations
        (id, job_mela_id, company_id, openings, target_hires, status, booth_number, booth_location, registered_at, approved_at, approved_by, created_at, updated_at)
        SELECT
            CONCAT('part-', m.id),
            m.id,
            rp.id,
            'Senior Frontend Engineer, Python Cloud Developer, DevOps Specialist',
            20,
            CASE
                WHEN m.id IN ('mela-2', 'mela-7', 'mela-9', 'mela-11') THEN 'PENDING'
                ELSE 'APPROVED'
            END,
            CASE
                WHEN m.id = 'mela-1' THEN 'Booth B-14 (Hall 3, Premium Corporate Stall)'
                WHEN m.id = 'mela-3' THEN 'Booth A-08 (Main Pavilion)'
                WHEN m.id = 'mela-4' THEN 'Booth C-03 (IT Wing)'
                WHEN m.id = 'mela-5' THEN 'Booth B-05 (Corporate Enclosure)'
                WHEN m.id = 'mela-6' THEN 'Booth H-12 (Enterprise Hall)'
                WHEN m.id = 'mela-8' THEN 'Booth D-02 (Technology Pavilion)'
                WHEN m.id = 'mela-10' THEN 'Booth E-07 (Main Arena)'
                WHEN m.id = 'mela-12' THEN 'Booth F-04 (Corporate Stall)'
                ELSE NULL
            END,
            CASE
                WHEN m.id IN ('mela-1', 'mela-3', 'mela-4', 'mela-5', 'mela-6', 'mela-8', 'mela-10', 'mela-12') THEN 'Corporate Pavilion'
                ELSE NULL
            END,
            '{now}',
            CASE
                WHEN m.id NOT IN ('mela-2', 'mela-7', 'mela-9', 'mela-11', 'mela-13', 'mela-14', 'mela-15') THEN '{now}'
                ELSE NULL
            END,
            CASE
                WHEN m.id NOT IN ('mela-2', 'mela-7', 'mela-9', 'mela-11', 'mela-13', 'mela-14', 'mela-15') THEN 'admin1@ntrvikasa.com'
                ELSE NULL
            END,
            '{now}',
            '{now}'
        FROM job_melas m
        CROSS JOIN recruiter_profiles rp
        WHERE rp.work_email = 'recruiter1@ntrvikasa.com'
          AND m.id IN ('mela-1', 'mela-2', 'mela-3', 'mela-4', 'mela-5', 'mela-6', 'mela-7', 'mela-8', 'mela-9', 'mela-10', 'mela-11', 'mela-12')
        """
    )


def downgrade() -> None:
    op.drop_table('job_mela_company_participations')
    op.drop_table('job_melas')
