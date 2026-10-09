"""add_job_mela_requests_openings_and_fields

Revision ID: c95a435f3460
Revises: 861fb3227351
Create Date: 2026-10-09 15:15:37.681255

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = 'c95a435f3460'
down_revision: Union[str, Sequence[str], None] = '861fb3227351'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Create job_mela_requests table
    op.create_table(
        'job_mela_requests',
        sa.Column('id', sa.String(length=50), nullable=False),
        sa.Column('request_number', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('organizer', sa.String(length=255), nullable=False),
        sa.Column('company_id', sa.String(length=50), nullable=True),
        sa.Column('contact_person', sa.String(length=150), nullable=True),
        sa.Column('contact_email', sa.String(length=150), nullable=True),
        sa.Column('contact_phone', sa.String(length=50), nullable=True),
        sa.Column('proposed_date', sa.String(length=50), nullable=False),
        sa.Column('start_time', sa.String(length=50), nullable=True),
        sa.Column('end_time', sa.String(length=50), nullable=True),
        sa.Column('venue', sa.String(length=255), nullable=False),
        sa.Column('city', sa.String(length=100), nullable=False),
        sa.Column('district', sa.String(length=100), nullable=True),
        sa.Column('state', sa.String(length=100), nullable=True),
        sa.Column('location', sa.String(length=255), nullable=True),
        sa.Column('address', sa.String(length=500), nullable=True),
        sa.Column('expected_capacity', sa.Integer(), nullable=True),
        sa.Column('vacancies_count', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=50), server_default='PENDING', nullable=False),
        sa.Column('admin_reviewer_id', sa.String(length=50), nullable=True),
        sa.Column('reviewer_name', sa.String(length=150), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('linked_job_mela_id', sa.String(length=50), nullable=True),
        sa.Column('participating_companies_data', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['admin_reviewer_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['company_id'], ['recruiter_profiles.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['linked_job_mela_id'], ['job_melas.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_job_mela_requests_city'), 'job_mela_requests', ['city'], unique=False)
    op.create_index(op.f('ix_job_mela_requests_id'), 'job_mela_requests', ['id'], unique=False)
    op.create_index(op.f('ix_job_mela_requests_organizer'), 'job_mela_requests', ['organizer'], unique=False)
    op.create_index(op.f('ix_job_mela_requests_proposed_date'), 'job_mela_requests', ['proposed_date'], unique=False)
    op.create_index(op.f('ix_job_mela_requests_request_number'), 'job_mela_requests', ['request_number'], unique=True)
    op.create_index(op.f('ix_job_mela_requests_status'), 'job_mela_requests', ['status'], unique=False)
    op.create_index(op.f('ix_job_mela_requests_title'), 'job_mela_requests', ['title'], unique=False)

    # 2. Create job_mela_job_openings table
    op.create_table(
        'job_mela_job_openings',
        sa.Column('id', sa.String(length=50), nullable=False),
        sa.Column('job_mela_id', sa.String(length=50), nullable=False),
        sa.Column('participation_id', sa.String(length=50), nullable=True),
        sa.Column('job_title', sa.String(length=255), nullable=False),
        sa.Column('vacancies', sa.Integer(), nullable=False),
        sa.Column('qualification', sa.String(length=255), nullable=True),
        sa.Column('experience', sa.String(length=255), nullable=True),
        sa.Column('salary_range', sa.String(length=255), nullable=True),
        sa.Column('location_stall', sa.String(length=255), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['job_mela_id'], ['job_melas.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['participation_id'], ['job_mela_company_participations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_job_mela_job_openings_id'), 'job_mela_job_openings', ['id'], unique=False)
    op.create_index(op.f('ix_job_mela_job_openings_job_mela_id'), 'job_mela_job_openings', ['job_mela_id'], unique=False)
    op.create_index(op.f('ix_job_mela_job_openings_participation_id'), 'job_mela_job_openings', ['participation_id'], unique=False)

    # 3. Add columns to job_mela_company_participations
    op.add_column('job_mela_company_participations', sa.Column('custom_company_name', sa.String(length=255), nullable=True))
    op.add_column('job_mela_company_participations', sa.Column('recruiter_name', sa.String(length=150), nullable=True))
    op.add_column('job_mela_company_participations', sa.Column('position', sa.String(length=255), nullable=True))
    op.add_column('job_mela_company_participations', sa.Column('qualification', sa.String(length=255), nullable=True))
    op.add_column('job_mela_company_participations', sa.Column('experience', sa.String(length=255), nullable=True))
    op.add_column('job_mela_company_participations', sa.Column('salary', sa.String(length=255), nullable=True))
    op.add_column('job_mela_company_participations', sa.Column('vacancies', sa.Integer(), server_default='15', nullable=False))
    op.add_column('job_mela_company_participations', sa.Column('location', sa.String(length=255), nullable=True))
    op.add_column('job_mela_company_participations', sa.Column('notes', sa.Text(), nullable=True))
    op.alter_column('job_mela_company_participations', 'company_id',
               existing_type=mysql.VARCHAR(length=50),
               nullable=True)

    # 4. Add columns to job_melas
    op.add_column('job_melas', sa.Column('state', sa.String(length=100), server_default='Andhra Pradesh', nullable=True))
    op.add_column('job_melas', sa.Column('address', sa.String(length=500), nullable=True))
    op.add_column('job_melas', sa.Column('organizer', sa.String(length=255), nullable=True))
    op.add_column('job_melas', sa.Column('client_name', sa.String(length=255), nullable=True))
    op.add_column('job_melas', sa.Column('client_id', sa.String(length=50), nullable=True))
    op.add_column('job_melas', sa.Column('client_contact_person', sa.String(length=150), nullable=True))
    op.add_column('job_melas', sa.Column('client_contact_phone', sa.String(length=50), nullable=True))
    op.add_column('job_melas', sa.Column('origin', sa.String(length=50), server_default='ADMIN_CREATED', nullable=False))
    op.add_column('job_melas', sa.Column('request_id', sa.String(length=50), nullable=True))
    op.add_column('job_melas', sa.Column('registration_start_date', sa.String(length=50), nullable=True))
    op.add_column('job_melas', sa.Column('eligible_mandals', sa.Text(), nullable=True))
    op.add_column('job_melas', sa.Column('eligible_villages', sa.Text(), nullable=True))
    op.add_column('job_melas', sa.Column('eligible_qualifications', sa.Text(), nullable=True))
    op.create_index(op.f('ix_job_melas_origin'), 'job_melas', ['origin'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_job_melas_origin'), table_name='job_melas')
    op.drop_column('job_melas', 'eligible_qualifications')
    op.drop_column('job_melas', 'eligible_villages')
    op.drop_column('job_melas', 'eligible_mandals')
    op.drop_column('job_melas', 'registration_start_date')
    op.drop_column('job_melas', 'request_id')
    op.drop_column('job_melas', 'origin')
    op.drop_column('job_melas', 'client_contact_phone')
    op.drop_column('job_melas', 'client_contact_person')
    op.drop_column('job_melas', 'client_id')
    op.drop_column('job_melas', 'client_name')
    op.drop_column('job_melas', 'organizer')
    op.drop_column('job_melas', 'address')
    op.drop_column('job_melas', 'state')

    op.alter_column('job_mela_company_participations', 'company_id',
               existing_type=mysql.VARCHAR(length=50),
               nullable=False)
    op.drop_column('job_mela_company_participations', 'notes')
    op.drop_column('job_mela_company_participations', 'location')
    op.drop_column('job_mela_company_participations', 'vacancies')
    op.drop_column('job_mela_company_participations', 'salary')
    op.drop_column('job_mela_company_participations', 'experience')
    op.drop_column('job_mela_company_participations', 'qualification')
    op.drop_column('job_mela_company_participations', 'position')
    op.drop_column('job_mela_company_participations', 'recruiter_name')
    op.drop_column('job_mela_company_participations', 'custom_company_name')

    op.drop_index(op.f('ix_job_mela_job_openings_participation_id'), table_name='job_mela_job_openings')
    op.drop_index(op.f('ix_job_mela_job_openings_job_mela_id'), table_name='job_mela_job_openings')
    op.drop_index(op.f('ix_job_mela_job_openings_id'), table_name='job_mela_job_openings')
    op.drop_table('job_mela_job_openings')

    op.drop_index(op.f('ix_job_mela_requests_title'), table_name='job_mela_requests')
    op.drop_index(op.f('ix_job_mela_requests_status'), table_name='job_mela_requests')
    op.drop_index(op.f('ix_job_mela_requests_request_number'), table_name='job_mela_requests')
    op.drop_index(op.f('ix_job_mela_requests_proposed_date'), table_name='job_mela_requests')
    op.drop_index(op.f('ix_job_mela_requests_organizer'), table_name='job_mela_requests')
    op.drop_index(op.f('ix_job_mela_requests_id'), table_name='job_mela_requests')
    op.drop_index(op.f('ix_job_mela_requests_city'), table_name='job_mela_requests')
    op.drop_table('job_mela_requests')
