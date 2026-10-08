"""add audit log target and metadata columns

Revision ID: 51db14676fd4
Revises: 33bffd9f54a4
Create Date: 2026-10-08 15:13:51.164452

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '51db14676fd4'
down_revision: Union[str, Sequence[str], None] = '33bffd9f54a4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('audit_logs', sa.Column('target_name', sa.String(length=255), nullable=True))
    op.add_column('audit_logs', sa.Column('result', sa.String(length=50), nullable=True))
    op.add_column('audit_logs', sa.Column('ip_address', sa.String(length=50), nullable=True))
    op.add_column('audit_logs', sa.Column('user_agent', sa.String(length=255), nullable=True))
    op.create_index(op.f('ix_audit_logs_result'), 'audit_logs', ['result'], unique=False)
    op.create_index(op.f('ix_audit_logs_target_name'), 'audit_logs', ['target_name'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_audit_logs_target_name'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_result'), table_name='audit_logs')
    op.drop_column('audit_logs', 'user_agent')
    op.drop_column('audit_logs', 'ip_address')
    op.drop_column('audit_logs', 'result')
    op.drop_column('audit_logs', 'target_name')
