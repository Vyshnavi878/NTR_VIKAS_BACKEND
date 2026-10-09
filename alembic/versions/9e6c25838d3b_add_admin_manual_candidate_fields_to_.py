"""add admin manual candidate fields to candidate profiles

Revision ID: 9e6c25838d3b
Revises: 1e3af979daf6
Create Date: 2026-10-09 17:10:07.145584

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9e6c25838d3b'
down_revision: Union[str, Sequence[str], None] = '1e3af979daf6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('candidate_profiles', sa.Column('gender', sa.String(length=20), nullable=True, server_default='Male'))
    op.add_column('candidate_profiles', sa.Column('placement_status', sa.String(length=50), nullable=True, server_default='NOT_PLACED'))
    op.add_column('candidate_profiles', sa.Column('placed_company', sa.String(length=200), nullable=True))
    op.add_column('candidate_profiles', sa.Column('placed_role', sa.String(length=150), nullable=True))
    op.add_column('candidate_profiles', sa.Column('placed_salary', sa.String(length=100), nullable=True))
    op.add_column('candidate_profiles', sa.Column('placed_date', sa.String(length=50), nullable=True))
    op.add_column('candidate_profiles', sa.Column('onboarded_by_admin_id', sa.String(length=50), nullable=True))
    op.add_column('candidate_profiles', sa.Column('custom_referrer', sa.String(length=200), nullable=True))
    op.add_column('candidate_profiles', sa.Column('aadhaar_hash', sa.String(length=64), nullable=True))
    op.create_index('ix_candidate_profiles_placement_status', 'candidate_profiles', ['placement_status'], unique=False)
    op.create_index('ix_candidate_profiles_aadhaar_hash', 'candidate_profiles', ['aadhaar_hash'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_candidate_profiles_aadhaar_hash', table_name='candidate_profiles')
    op.drop_index('ix_candidate_profiles_placement_status', table_name='candidate_profiles')
    op.drop_column('candidate_profiles', 'aadhaar_hash')
    op.drop_column('candidate_profiles', 'custom_referrer')
    op.drop_column('candidate_profiles', 'onboarded_by_admin_id')
    op.drop_column('candidate_profiles', 'placed_date')
    op.drop_column('candidate_profiles', 'placed_salary')
    op.drop_column('candidate_profiles', 'placed_role')
    op.drop_column('candidate_profiles', 'placed_company')
    op.drop_column('candidate_profiles', 'placement_status')
    op.drop_column('candidate_profiles', 'gender')
