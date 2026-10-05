"""add recruiter_support_requests table

Revision ID: c4d8123ef901
Revises: 67155c451a18
Create Date: 2026-10-05 19:25:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4d8123ef901'
down_revision: Union[str, Sequence[str], None] = '67155c451a18'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'recruiter_support_requests',
        sa.Column('id', sa.String(length=50), nullable=False),
        sa.Column('ticket_number', sa.String(length=50), nullable=False),
        sa.Column('recruiter_id', sa.String(length=50), nullable=False),
        sa.Column('company_name', sa.String(length=200), nullable=False),
        sa.Column('recruiter_name', sa.String(length=150), nullable=False),
        sa.Column('registered_email', sa.String(length=150), nullable=False),
        sa.Column('issue_category', sa.String(length=100), nullable=False),
        sa.Column('subject', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('priority', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.Column('closed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['recruiter_id'], ['recruiter_profiles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_recruiter_support_requests_id'), 'recruiter_support_requests', ['id'], unique=False)
    op.create_index(op.f('ix_recruiter_support_requests_ticket_number'), 'recruiter_support_requests', ['ticket_number'], unique=True)
    op.create_index(op.f('ix_recruiter_support_requests_recruiter_id'), 'recruiter_support_requests', ['recruiter_id'], unique=False)
    op.create_index(op.f('ix_recruiter_support_requests_issue_category'), 'recruiter_support_requests', ['issue_category'], unique=False)
    op.create_index(op.f('ix_recruiter_support_requests_status'), 'recruiter_support_requests', ['status'], unique=False)
    op.create_index(op.f('ix_recruiter_support_requests_created_at'), 'recruiter_support_requests', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_recruiter_support_requests_created_at'), table_name='recruiter_support_requests')
    op.drop_index(op.f('ix_recruiter_support_requests_status'), table_name='recruiter_support_requests')
    op.drop_index(op.f('ix_recruiter_support_requests_issue_category'), table_name='recruiter_support_requests')
    op.drop_index(op.f('ix_recruiter_support_requests_recruiter_id'), table_name='recruiter_support_requests')
    op.drop_index(op.f('ix_recruiter_support_requests_ticket_number'), table_name='recruiter_support_requests')
    op.drop_index(op.f('ix_recruiter_support_requests_id'), table_name='recruiter_support_requests')
    op.drop_table('recruiter_support_requests')
