"""P2: agent console — 交易信号 + 交易员持仓

Revision ID: p2_agent_console
Revises: p1_agent_marketplace
Create Date: 2026-07-23 00:00:00

新增:
- agent.agent_signals: 交易信号表
- agent.agent_portfolios: 交易员持仓表
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "p2_agent_console"
down_revision: Union[str, None] = "p1_agent_marketplace"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── agent.agent_signals ──
    op.create_table(
        "agent_signals",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column("hire_id", sa.Integer(), sa.ForeignKey("agent.user_agents.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("trader_id", sa.String(32), sa.ForeignKey("agent.agent_traders.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("symbol", sa.String(16), nullable=False),
        sa.Column("symbol_name", sa.String(64), nullable=False),
        sa.Column("action", sa.String(8), nullable=False),  # buy / sell
        sa.Column("price", sa.Numeric(12, 2), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, default=100),
        sa.Column("confidence", sa.Integer(), nullable=False, default=50),
        sa.Column("reasoning", sa.Text(), nullable=True),
        sa.Column("exec_status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        schema="agent",
    )
    op.create_index("ix_agent_signals_hire_status", "agent_signals", ["hire_id", "exec_status"], schema="agent")
    op.create_index("ix_agent_signals_user", "agent_signals", ["user_id", "created_at"], schema="agent")

    # ── agent.agent_portfolios ──
    op.create_table(
        "agent_portfolios",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column("hire_id", sa.Integer(), sa.ForeignKey("agent.user_agents.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("trader_id", sa.String(32), sa.ForeignKey("agent.agent_traders.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("symbol", sa.String(16), nullable=False),
        sa.Column("symbol_name", sa.String(64), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, default=0),
        sa.Column("avg_cost", sa.Numeric(12, 2), nullable=False, default=0),
        sa.Column("current_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("market_value", sa.Numeric(16, 2), nullable=True),
        sa.Column("unrealized_pnl", sa.Numeric(16, 2), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        schema="agent",
    )
    op.create_index("ix_agent_portfolios_hire", "agent_portfolios", ["hire_id", "symbol"], schema="agent")


def downgrade() -> None:
    op.drop_table("agent_portfolios", schema="agent")
    op.drop_table("agent_signals", schema="agent")
