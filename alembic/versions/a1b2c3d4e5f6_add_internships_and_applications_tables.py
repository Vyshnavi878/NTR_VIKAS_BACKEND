"""add internships, internship_applications, and audit_logs tables

Revision ID: a1b2c3d4e5f6
Revises: e382fa761b09
Create Date: 2026-10-05 20:45:00.000000

"""
from typing import Sequence, Union
from datetime import datetime, timezone
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'e382fa761b09'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create internships table
    op.create_table(
        'internships',
        sa.Column('id', sa.String(length=50), nullable=False),
        sa.Column('internship_number', sa.String(length=50), nullable=False),
        sa.Column('company_id', sa.String(length=50), nullable=False),
        sa.Column('created_by', sa.String(length=50), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('stipend_monthly', sa.Integer(), nullable=False, server_default='15000'),
        sa.Column('stipend', sa.String(length=100), nullable=True),
        sa.Column('duration', sa.String(length=100), nullable=False, server_default='6 Months'),
        sa.Column('work_mode', sa.String(length=50), nullable=False, server_default='Hybrid'),
        sa.Column('location', sa.String(length=255), nullable=True, server_default='Bengaluru, Karnataka'),
        sa.Column('number_of_interns', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='PENDING'),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('rejected_by', sa.String(length=150), nullable=True),
        sa.Column('rejected_at', sa.DateTime(), nullable=True),
        sa.Column('approved_by', sa.String(length=150), nullable=True),
        sa.Column('approved_at', sa.DateTime(), nullable=True),
        sa.Column('published_at', sa.DateTime(), nullable=True),
        sa.Column('closed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['recruiter_profiles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('internship_number'),
    )
    op.create_index(op.f('ix_internships_id'), 'internships', ['id'], unique=False)
    op.create_index(op.f('ix_internships_internship_number'), 'internships', ['internship_number'], unique=True)
    op.create_index(op.f('ix_internships_company_id'), 'internships', ['company_id'], unique=False)
    op.create_index(op.f('ix_internships_created_by'), 'internships', ['created_by'], unique=False)
    op.create_index(op.f('ix_internships_title'), 'internships', ['title'], unique=False)
    op.create_index(op.f('ix_internships_status'), 'internships', ['status'], unique=False)

    # 2. Create internship_applications table
    op.create_table(
        'internship_applications',
        sa.Column('id', sa.String(length=50), nullable=False),
        sa.Column('internship_id', sa.String(length=50), nullable=False),
        sa.Column('candidate_id', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='APPLIED'),
        sa.Column('cover_letter', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['candidate_id'], ['candidate_profiles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['internship_id'], ['internships.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_internship_applications_id'), 'internship_applications', ['id'], unique=False)
    op.create_index(op.f('ix_internship_applications_internship_id'), 'internship_applications', ['internship_id'], unique=False)
    op.create_index(op.f('ix_internship_applications_candidate_id'), 'internship_applications', ['candidate_id'], unique=False)
    op.create_index(op.f('ix_internship_applications_status'), 'internship_applications', ['status'], unique=False)

    # 3. Create audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.String(length=50), nullable=False),
        sa.Column('actor', sa.String(length=150), nullable=False),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('entity', sa.String(length=50), nullable=False),
        sa.Column('entity_id', sa.String(length=50), nullable=False),
        sa.Column('metadata_json', sa.Text(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_audit_logs_id'), 'audit_logs', ['id'], unique=False)
    op.create_index(op.f('ix_audit_logs_actor'), 'audit_logs', ['actor'], unique=False)
    op.create_index(op.f('ix_audit_logs_action'), 'audit_logs', ['action'], unique=False)
    op.create_index(op.f('ix_audit_logs_entity'), 'audit_logs', ['entity'], unique=False)
    op.create_index(op.f('ix_audit_logs_entity_id'), 'audit_logs', ['entity_id'], unique=False)
    op.create_index(op.f('ix_audit_logs_timestamp'), 'audit_logs', ['timestamp'], unique=False)

    # 4. Seed initial internships matching recruiter profile
    now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')

    op.execute(
        f"""
        INSERT INTO internships
        (id, internship_number, company_id, created_by, title, stipend_monthly, stipend, duration, work_mode, location, number_of_interns, description, status, published_at, created_at, updated_at)
        SELECT
            'intern-1',
            'INT-0001',
            rp.id,
            rp.user_id,
            'Frontend React Development Intern',
            25000,
            '₹25,000 / month',
            '6 Months',
            'Hybrid',
            'Bengaluru, Karnataka',
            4,
            'Hands-on frontend development internship working on React, TypeScript, and modern UI components.',
            'PUBLISHED',
            '{now}',
            '{now}',
            '{now}'
        FROM recruiter_profiles rp
        WHERE rp.work_email = 'recruiter1@ntrvikasa.com'
        """
    )

    op.execute(
        f"""
        INSERT INTO internships
        (id, internship_number, company_id, created_by, title, stipend_monthly, stipend, duration, work_mode, location, number_of_interns, description, status, published_at, created_at, updated_at)
        SELECT
            'intern-2',
            'INT-0002',
            rp.id,
            rp.user_id,
            'Cloud Infrastructure & DevOps Intern',
            30000,
            '₹30,000 / month',
            '6 Months',
            'On-site',
            'Hyderabad, Telangana',
            2,
            'Learn Terraform, Docker, Kubernetes, and AWS automation alongside senior DevOps engineers.',
            'PUBLISHED',
            '{now}',
            '{now}',
            '{now}'
        FROM recruiter_profiles rp
        WHERE rp.work_email = 'recruiter1@ntrvikasa.com'
        """
    )

    op.execute(
        f"""
        INSERT INTO internships
        (id, internship_number, company_id, created_by, title, stipend_monthly, stipend, duration, work_mode, location, number_of_interns, description, status, published_at, created_at, updated_at)
        SELECT
            'intern-3',
            'INT-0003',
            rp.id,
            rp.user_id,
            'AI & Data Science Engineering Intern',
            28000,
            '₹28,000 / month',
            '6 Months',
            'Remote',
            'Remote (India)',
            2,
            'Train and fine-tune transformer models and build automated Python evaluation pipelines.',
            'PENDING',
            NULL,
            '{now}',
            '{now}'
        FROM recruiter_profiles rp
        WHERE rp.work_email = 'recruiter1@ntrvikasa.com'
        """
    )

    # 5. Seed applicant rows into internship_applications to match 42, 28, 19
    # Using existing candidate profiles or generated IDs
    op.execute(
        f"""
        INSERT INTO internship_applications (id, internship_id, candidate_id, status, created_at, updated_at)
        SELECT
            CONCAT('ia-1-', seq),
            'intern-1',
            cp.id,
            'APPLIED',
            '{now}',
            '{now}'
        FROM candidate_profiles cp
        CROSS JOIN (
            SELECT 1 AS seq UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5 UNION
            SELECT 6 UNION SELECT 7 UNION SELECT 8 UNION SELECT 9 UNION SELECT 10 UNION
            SELECT 11 UNION SELECT 12 UNION SELECT 13 UNION SELECT 14 UNION SELECT 15 UNION
            SELECT 16 UNION SELECT 17 UNION SELECT 18 UNION SELECT 19 UNION SELECT 20 UNION
            SELECT 21 UNION SELECT 22 UNION SELECT 23 UNION SELECT 24 UNION SELECT 25 UNION
            SELECT 26 UNION SELECT 27 UNION SELECT 28 UNION SELECT 29 UNION SELECT 30 UNION
            SELECT 31 UNION SELECT 32 UNION SELECT 33 UNION SELECT 34 UNION SELECT 35 UNION
            SELECT 36 UNION SELECT 37 UNION SELECT 38 UNION SELECT 39 UNION SELECT 40 UNION
            SELECT 41 UNION SELECT 42
        ) nums
        LIMIT 42
        """
    )

    op.execute(
        f"""
        INSERT INTO internship_applications (id, internship_id, candidate_id, status, created_at, updated_at)
        SELECT
            CONCAT('ia-2-', seq),
            'intern-2',
            cp.id,
            'APPLIED',
            '{now}',
            '{now}'
        FROM candidate_profiles cp
        CROSS JOIN (
            SELECT 1 AS seq UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5 UNION
            SELECT 6 UNION SELECT 7 UNION SELECT 8 UNION SELECT 9 UNION SELECT 10 UNION
            SELECT 11 UNION SELECT 12 UNION SELECT 13 UNION SELECT 14 UNION SELECT 15 UNION
            SELECT 16 UNION SELECT 17 UNION SELECT 18 UNION SELECT 19 UNION SELECT 20 UNION
            SELECT 21 UNION SELECT 22 UNION SELECT 23 UNION SELECT 24 UNION SELECT 25 UNION
            SELECT 26 UNION SELECT 27 UNION SELECT 28
        ) nums
        LIMIT 28
        """
    )

    op.execute(
        f"""
        INSERT INTO internship_applications (id, internship_id, candidate_id, status, created_at, updated_at)
        SELECT
            CONCAT('ia-3-', seq),
            'intern-3',
            cp.id,
            'APPLIED',
            '{now}',
            '{now}'
        FROM candidate_profiles cp
        CROSS JOIN (
            SELECT 1 AS seq UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5 UNION
            SELECT 6 UNION SELECT 7 UNION SELECT 8 UNION SELECT 9 UNION SELECT 10 UNION
            SELECT 11 UNION SELECT 12 UNION SELECT 13 UNION SELECT 14 UNION SELECT 15 UNION
            SELECT 16 UNION SELECT 17 UNION SELECT 18 UNION SELECT 19
        ) nums
        LIMIT 19
        """
    )


def downgrade() -> None:
    op.drop_table('audit_logs')
    op.drop_table('internship_applications')
    op.drop_table('internships')
