"""add_platform_settings_table

Revision ID: 33bffd9f54a4
Revises: 49db463f5f52
Create Date: 2026-10-08 14:58:47.550797

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '33bffd9f54a4'
down_revision: Union[str, Sequence[str], None] = '49db463f5f52'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('platform_settings',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('platform_display_name', sa.String(length=255), nullable=False),
    sa.Column('primary_support_email', sa.String(length=255), nullable=False),
    sa.Column('grievance_redressal_email', sa.String(length=255), nullable=False),
    sa.Column('mandatory_recruiter_legal_verification', sa.Boolean(), nullable=False),
    sa.Column('pre_publish_job_moderation_queue', sa.Boolean(), nullable=False),
    sa.Column('strict_zero_fee_candidate_rule', sa.Boolean(), nullable=False),
    sa.Column('platform_maintenance_mode', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.Column('updated_by', sa.String(length=150), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('platform_settings')
