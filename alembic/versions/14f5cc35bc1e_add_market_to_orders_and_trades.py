"""add market to orders and trades
Revision ID: 14f5cc35bc1e
Revises: p2_agent_console
Create Date: 2026-08-07 19:30:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '14f5cc35bc1e'
down_revision: Union[str, None] = 'p2_agent_console'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('orders', sa.Column('market', sa.String(length=10), nullable=False, server_default='A', comment='市场：A / HK'))
    op.add_column('trades', sa.Column('market', sa.String(length=10), nullable=False, server_default='A', comment='市场：A / HK'))


def downgrade() -> None:
    op.drop_column('trades', 'market')
    op.drop_column('orders', 'market')
