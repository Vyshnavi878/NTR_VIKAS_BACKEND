"""add_job_mela_page_settings_table

Revision ID: 16a745366e1f
Revises: 6d07b9e6917a
Create Date: 2026-10-11 12:56:39.834326

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '16a745366e1f'
down_revision: Union[str, Sequence[str], None] = '6d07b9e6917a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('job_mela_page_settings',
    sa.Column('id', sa.String(length=50), nullable=False),
    sa.Column('hero_badge', sa.String(length=255), nullable=False),
    sa.Column('hero_heading', sa.String(length=255), nullable=False),
    sa.Column('hero_description', sa.Text(), nullable=False),
    sa.Column('updated_by', sa.String(length=150), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('job_mela_page_settings')

