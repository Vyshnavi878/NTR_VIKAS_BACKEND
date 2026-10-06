"""add job mela registrations and fields

Revision ID: d8291fe930a1
Revises: 7c705b6a9362
Create Date: 2026-10-06 17:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd8291fe930a1'
down_revision: Union[str, Sequence[str], None] = '7c705b6a9362'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add extra columns to job_melas
    op.add_column('job_melas', sa.Column('created_by_role', sa.String(length=50), server_default='ADMIN', nullable=False))
    op.add_column('job_melas', sa.Column('company_id', sa.String(length=50), nullable=True))
    op.add_column('job_melas', sa.Column('image_url', sa.String(length=500), nullable=True))
    op.add_column('job_melas', sa.Column('flyer_url', sa.String(length=500), nullable=True))
    op.add_column('job_melas', sa.Column('registration_deadline', sa.String(length=50), nullable=True))
    op.add_column('job_melas', sa.Column('max_capacity', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_job_melas_company_id', 'job_melas', 'recruiter_profiles', ['company_id'], ['id'], ondelete='SET NULL')

    # 2. Create job_mela_registrations table
    op.create_table(
        'job_mela_registrations',
        sa.Column('id', sa.String(length=50), nullable=False),
        sa.Column('job_mela_id', sa.String(length=50), nullable=False),
        sa.Column('candidate_profile_id', sa.String(length=50), nullable=False),
        sa.Column('pass_id', sa.String(length=100), nullable=False),
        sa.Column('status', sa.String(length=50), server_default='CONFIRMED', nullable=False),
        sa.Column('gate_number', sa.String(length=100), server_default='Gate 2 (General Fast-Track)', nullable=False),
        sa.Column('time_slot', sa.String(length=100), server_default='Morning Session (09:00 AM - 01:00 PM)', nullable=False),
        sa.Column('qr_data', sa.String(length=255), nullable=True),
        sa.Column('application_id', sa.String(length=50), nullable=True),
        sa.Column('registered_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['candidate_profile_id'], ['candidate_profiles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['job_mela_id'], ['job_melas.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('pass_id', name='uq_mela_pass_id'),
        sa.UniqueConstraint('job_mela_id', 'candidate_profile_id', name='uq_mela_candidate_registration')
    )
    op.create_index(op.f('ix_job_mela_registrations_id'), 'job_mela_registrations', ['id'], unique=False)
    op.create_index(op.f('ix_job_mela_registrations_job_mela_id'), 'job_mela_registrations', ['job_mela_id'], unique=False)
    op.create_index(op.f('ix_job_mela_registrations_candidate_profile_id'), 'job_mela_registrations', ['candidate_profile_id'], unique=False)
    op.create_index(op.f('ix_job_mela_registrations_pass_id'), 'job_mela_registrations', ['pass_id'], unique=True)
    op.create_index(op.f('ix_job_mela_registrations_status'), 'job_mela_registrations', ['status'], unique=False)
    op.create_index(op.f('ix_job_mela_registrations_application_id'), 'job_mela_registrations', ['application_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_job_mela_registrations_application_id'), table_name='job_mela_registrations')
    op.drop_index(op.f('ix_job_mela_registrations_status'), table_name='job_mela_registrations')
    op.drop_index(op.f('ix_job_mela_registrations_pass_id'), table_name='job_mela_registrations')
    op.drop_index(op.f('ix_job_mela_registrations_candidate_profile_id'), table_name='job_mela_registrations')
    op.drop_index(op.f('ix_job_mela_registrations_job_mela_id'), table_name='job_mela_registrations')
    op.drop_index(op.f('ix_job_mela_registrations_id'), table_name='job_mela_registrations')
    op.drop_table('job_mela_registrations')

    op.drop_constraint('fk_job_melas_company_id', 'job_melas', type_='foreignkey')
    op.drop_column('job_melas', 'max_capacity')
    op.drop_column('job_melas', 'registration_deadline')
    op.drop_column('job_melas', 'flyer_url')
    op.drop_column('job_melas', 'image_url')
    op.drop_column('job_melas', 'company_id')
    op.drop_column('job_melas', 'created_by_role')
