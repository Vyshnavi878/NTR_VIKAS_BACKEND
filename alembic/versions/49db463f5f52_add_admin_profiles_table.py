"""add admin profiles table

Revision ID: 49db463f5f52
Revises: e4f5a6b7c8d9
Create Date: 2026-10-08 14:24:38.740042

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '49db463f5f52'
down_revision: Union[str, Sequence[str], None] = 'e4f5a6b7c8d9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'admin_profiles',
        sa.Column('id', sa.String(length=50), nullable=False),
        sa.Column('user_id', sa.String(length=50), nullable=False),
        sa.Column('full_name', sa.String(length=150), nullable=False),
        sa.Column('designation', sa.String(length=150), nullable=True),
        sa.Column('contact_phone', sa.String(length=20), nullable=True),
        sa.Column('department', sa.String(length=255), nullable=True),
        sa.Column('profile_image_url', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_admin_profiles_id'), 'admin_profiles', ['id'], unique=False)
    op.create_index(op.f('ix_admin_profiles_user_id'), 'admin_profiles', ['user_id'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_admin_profiles_user_id'), table_name='admin_profiles')
    op.drop_index(op.f('ix_admin_profiles_id'), table_name='admin_profiles')
    op.drop_table('admin_profiles')

