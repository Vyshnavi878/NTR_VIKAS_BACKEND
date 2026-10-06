"""add result and company_name to interviews

Revision ID: e4f5a6b7c8d9
Revises: d8291fe930a1
Create Date: 2026-10-06 17:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e4f5a6b7c8d9'
down_revision: Union[str, Sequence[str], None] = 'd8291fe930a1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('interviews', sa.Column('company_name', sa.String(length=200), nullable=True))
    op.add_column('interviews', sa.Column('result', sa.String(length=50), nullable=True))


def downgrade() -> None:
    op.drop_column('interviews', 'result')
    op.drop_column('interviews', 'company_name')
