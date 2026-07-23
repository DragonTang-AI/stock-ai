"""P1: agent marketplace — 积分系统 + 交易员市场

Revision ID: p1_agent_marketplace
Revises: p0f2_multi_schema
Create Date: 2026-07-22 00:00:00

新增:
- agent schema
- agent.agent_traders: 官方交易员
- agent.user_agents: 用户已雇佣交易员（含雇佣状态、管理模式）
- agent.points_transactions: 积分流水
- agent.agent_performances: 交易员历史表现（周期快照）
- public.user_points: 用户积分余额
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "p1_agent_marketplace"
down_revision: Union[str, None] = "p0f2_multi_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Schema ──
    op.execute("CREATE SCHEMA IF NOT EXISTS agent")

    # ── public.user_points ──
    op.create_table(
        "user_points",
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("balance", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("total_earned", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("total_spent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # ── agent.agent_traders ──
    op.create_table(
        "agent_traders",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("code_name", sa.String(32), nullable=False),        # 镇岳/逐光/千机/逆川/守一
        sa.Column("tag", sa.String(32), nullable=False),               # 价值猎手/成长先锋/量化大师/逆向猎手/全能管家
        sa.Column("avatar_url", sa.String(512), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),           # 简介
        sa.Column("strategy_detail", sa.Text(), nullable=True),        # 策略详情
        sa.Column("masters", sa.String(256), nullable=False),          # 师承大师
        sa.Column("hire_price_points", sa.Integer(), nullable=False, default=0),  # 雇佣所需积分
        sa.Column("profit_share_pct", sa.Numeric(4, 2), nullable=False, default=0), # 盈利分成比例
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("sort_order", sa.Integer(), nullable=False, default=0),
        sa.Column("annual_return", sa.Numeric(8, 2), nullable=True),  # 年化收益
        sa.Column("max_drawdown", sa.Numeric(8, 2), nullable=True),   # 最大回撤
        sa.Column("sharpe_ratio", sa.Numeric(6, 2), nullable=True),   # 夏普比率
        sa.Column("win_rate", sa.Numeric(5, 2), nullable=True),       # 胜率
        sa.Column("total_trades", sa.Integer(), nullable=True),       # 历史总交易数
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        schema="agent",
    )

    # ── agent.user_agents ──
    op.create_table(
        "user_agents",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("agent_id", sa.String(32), sa.ForeignKey("agent.agent_traders.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="active"),   # active / paused / expired
        sa.Column("management_mode", sa.String(16), nullable=False, server_default="advisory"),  # advisory / full_managed
        sa.Column("allocated_capital", sa.Numeric(16, 2), nullable=True),  # 分配给该交易员的资金
        sa.Column("current_pnl", sa.Numeric(16, 2), nullable=True, server_default="0"),
        sa.Column("hired_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        schema="agent",
    )
    op.create_index("ix_agent_user_agents_user_status", "user_agents", ["user_id", "status"], schema="agent")
    op.create_unique_constraint("uq_user_agent_active", "user_agents", ["user_id", "agent_id", "status"], schema="agent")

    # ── agent.points_transactions ──
    op.create_table(
        "points_transactions",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("amount", sa.Integer(), nullable=False),               # 正=收入, 负=支出
        sa.Column("balance_after", sa.Integer(), nullable=False),
        sa.Column("tx_type", sa.String(32), nullable=False),             # register_bonus / hire_agent / profit_share / daily_checkin / admin_grant
        sa.Column("reference_id", sa.String(128), nullable=True),        # 关联实体 ID
        sa.Column("description", sa.String(256), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), index=True),
        schema="agent",
    )

    # ── agent.agent_performances ──
    op.create_table(
        "agent_performances",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column("agent_id", sa.String(32), sa.ForeignKey("agent.agent_traders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("period", sa.String(16), nullable=False),              # daily / weekly / monthly / yearly
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("return_pct", sa.Numeric(8, 4), nullable=False),
        sa.Column("benchmark_return_pct", sa.Numeric(8, 4), nullable=True),
        sa.Column("alpha", sa.Numeric(8, 4), nullable=True),
        sa.Column("max_drawdown", sa.Numeric(8, 4), nullable=True),
        sa.Column("sharpe_ratio", sa.Numeric(6, 2), nullable=True),
        sa.Column("win_rate", sa.Numeric(5, 2), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        schema="agent",
    )
    op.create_index("ix_agent_performances_agent_period", "agent_performances", ["agent_id", "period", "period_end"], schema="agent")


def downgrade() -> None:
    op.drop_table("agent_performances", schema="agent")
    op.drop_table("points_transactions", schema="agent")
    op.drop_table("user_agents", schema="agent")
    op.drop_table("agent_traders", schema="agent")
    op.drop_table("user_points")
    op.execute("DROP SCHEMA IF EXISTS agent CASCADE")
