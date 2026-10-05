"""add source to candidate_applications

Revision ID: d719fa9921b0
Revises: c4d8123ef901
Create Date: 2026-10-05 19:46:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd719fa9921b0'
down_revision: Union[str, Sequence[str], None] = 'c4d8123ef901'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'candidate_applications',
        sa.Column(
            'source',
            sa.String(length=100),
            nullable=False,
            server_default='NTR Vikasa Job Portal Direct',
        ),
    )
    op.create_index(
        op.f('ix_candidate_applications_source'),
        'candidate_applications',
        ['source'],
        unique=False,
    )
    # Populate existing rows appropriately
    op.execute(
        "UPDATE candidate_applications SET source = 'NTR Vikasa Mega Job Melas' "
        "WHERE mela_id IS NOT NULL OR application_type LIKE '%Mela%'"
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_candidate_applications_source'), table_name='candidate_applications')
    op.drop_column('candidate_applications', 'source')
