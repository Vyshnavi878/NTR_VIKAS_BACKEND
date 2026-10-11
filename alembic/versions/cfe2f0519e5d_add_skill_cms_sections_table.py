"""add_skill_cms_sections_table

Revision ID: cfe2f0519e5d
Revises: 16a745366e1f
Create Date: 2026-10-11 13:25:51.993323

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cfe2f0519e5d'
down_revision: Union[str, Sequence[str], None] = '16a745366e1f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('skill_cms_sections',
    sa.Column('section_key', sa.String(length=50), nullable=False),
    sa.Column('title', sa.String(length=255), nullable=True),
    sa.Column('content', sa.Text(), nullable=False),
    sa.Column('updated_by', sa.String(length=150), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('section_key')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('skill_cms_sections')

