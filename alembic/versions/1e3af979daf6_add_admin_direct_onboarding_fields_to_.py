"""add admin direct onboarding fields to recruiter profiles

Revision ID: 1e3af979daf6
Revises: c95a435f3460
Create Date: 2026-10-09 16:03:45.882725

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = '1e3af979daf6'
down_revision: Union[str, Sequence[str], None] = 'c95a435f3460'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('recruiter_profiles', sa.Column('company_type', sa.String(length=100), nullable=True))
    op.add_column('recruiter_profiles', sa.Column('district', sa.String(length=100), nullable=True))
    op.add_column('recruiter_profiles', sa.Column('mandal', sa.String(length=100), nullable=True))
    op.add_column('recruiter_profiles', sa.Column('village', sa.String(length=100), nullable=True))
    op.add_column('recruiter_profiles', sa.Column('onboarded_by_admin_id', sa.String(length=50), nullable=True))
    op.add_column('recruiter_profiles', sa.Column('onboarded_by_role', sa.String(length=50), nullable=True))
    op.alter_column('recruiter_profiles', 'incorporation_document_path',
               existing_type=mysql.VARCHAR(length=500),
               nullable=True)
    op.alter_column('recruiter_profiles', 'recruiter_authorization_document_path',
               existing_type=mysql.VARCHAR(length=500),
               nullable=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column('recruiter_profiles', 'recruiter_authorization_document_path',
               existing_type=mysql.VARCHAR(length=500),
               nullable=False)
    op.alter_column('recruiter_profiles', 'incorporation_document_path',
               existing_type=mysql.VARCHAR(length=500),
               nullable=False)
    op.drop_column('recruiter_profiles', 'onboarded_by_role')
    op.drop_column('recruiter_profiles', 'onboarded_by_admin_id')
    op.drop_column('recruiter_profiles', 'village')
    op.drop_column('recruiter_profiles', 'mandal')
    op.drop_column('recruiter_profiles', 'district')
    op.drop_column('recruiter_profiles', 'company_type')
