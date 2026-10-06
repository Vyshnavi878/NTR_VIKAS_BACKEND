"""add interview scheduling columns

Revision ID: 55809c7ebb0f
Revises: f1e2d3c4b5a6
Create Date: 2026-10-06 12:02:50.084754

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '55809c7ebb0f'
down_revision: Union[str, Sequence[str], None] = 'f1e2d3c4b5a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('interviews', sa.Column('scheduled_date', sa.String(length=50), nullable=True))
    op.add_column('interviews', sa.Column('start_time', sa.String(length=50), nullable=True))
    op.add_column('interviews', sa.Column('end_time', sa.String(length=50), nullable=True))
    op.add_column('interviews', sa.Column('timezone', sa.String(length=50), server_default='Asia/Kolkata', nullable=False))
    op.add_column('interviews', sa.Column('format', sa.String(length=50), server_default='ONLINE', nullable=False))
    op.add_column('interviews', sa.Column('venue', sa.String(length=255), nullable=True))
    op.add_column('interviews', sa.Column('interviewer_panel', sa.Text(), nullable=True))
    op.add_column('interviews', sa.Column('agenda_notes', sa.Text(), nullable=True))
    op.add_column('interviews', sa.Column('completed_at', sa.DateTime(), nullable=True))
    op.add_column('interviews', sa.Column('cancelled_at', sa.DateTime(), nullable=True))
    op.add_column('interviews', sa.Column('rescheduled_from_id', sa.String(length=50), nullable=True))
    op.add_column('interviews', sa.Column('cancellation_reason', sa.Text(), nullable=True))
    op.add_column('interviews', sa.Column('created_by', sa.String(length=150), nullable=True))
    op.create_index(op.f('ix_interviews_rescheduled_from_id'), 'interviews', ['rescheduled_from_id'], unique=False)
    op.create_index(op.f('ix_interviews_scheduled_date'), 'interviews', ['scheduled_date'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_interviews_scheduled_date'), table_name='interviews')
    op.drop_index(op.f('ix_interviews_rescheduled_from_id'), table_name='interviews')
    op.drop_column('interviews', 'created_by')
    op.drop_column('interviews', 'cancellation_reason')
    op.drop_column('interviews', 'rescheduled_from_id')
    op.drop_column('interviews', 'cancelled_at')
    op.drop_column('interviews', 'completed_at')
    op.drop_column('interviews', 'agenda_notes')
    op.drop_column('interviews', 'interviewer_panel')
    op.drop_column('interviews', 'venue')
    op.drop_column('interviews', 'format')
    op.drop_column('interviews', 'timezone')
    op.drop_column('interviews', 'end_time')
    op.drop_column('interviews', 'start_time')
    op.drop_column('interviews', 'scheduled_date')

