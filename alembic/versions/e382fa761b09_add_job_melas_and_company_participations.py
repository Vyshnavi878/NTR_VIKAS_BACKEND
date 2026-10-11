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




def downgrade() -> None:
    op.drop_table('job_mela_company_participations')
    op.drop_table('job_melas')
