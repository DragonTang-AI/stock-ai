"""P0-F2: create auth/trading/analysis schemas + tables

Revision ID: p0f2_multi_schema
Revises: a5a6407db4fd
Create Date: 2026-07-06 00:00:00

继承生产现有迁移历史 (a5a6407db4fd = users表)
目标: 创建 auth/trading/analysis/market schemas 及对应表

Schema 说明:
- public: 保持现状(users等原有表)
- market: kline_daily 行情数据
- analysis: AI报告/信号审计/通用审计日志(JSONB)
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "p0f2_multi_schema"
down_revision: Union[str, None] = "a5a6407db4fd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Schemas ──
    op.execute("CREATE SCHEMA IF NOT EXISTS market")
    op.execute("CREATE SCHEMA IF NOT EXISTS analysis")

    # ── market.kline_daily ──
    op.create_table(
        "kline_daily",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("symbol", sa.String(32), nullable=False),
        sa.Column("trade_date", sa.String(32), nullable=False),
        sa.Column("market", sa.String(8), nullable=False),
        sa.Column("open", sa.Numeric(12, 4), nullable=False),
        sa.Column("high", sa.Numeric(12, 4), nullable=False),
        sa.Column("low", sa.Numeric(12, 4), nullable=False),
        sa.Column("close", sa.Numeric(12, 4), nullable=False),
        sa.Column("volume", sa.Numeric(20, 4), nullable=False),
        sa.Column("amount", sa.Numeric(20, 4), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        schema="market",
    )
    op.create_index(
        "ix_market_kline_daily_symbol_trade_date",
        "kline_daily",
        ["symbol", "trade_date"],
        unique=True,
        schema="market",
    )

    # ── analysis.daily_reports ──
    op.create_table(
        "daily_reports",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False, index=True),
        sa.Column("report_type", sa.String(32), nullable=False),
        sa.Column("content", sa.JSONB(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("generated_at", sa.String(64), nullable=False, index=True),
        sa.Column("created_at", sa.String(64), nullable=False),
        sa.Column("updated_at", sa.String(64), nullable=False),
        schema="analysis",
    )

    # ── analysis.signal_audit ──
    op.create_table(
        "signal_audit",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column("signal_id", sa.String(64), nullable=False, index=True),
        sa.Column("user_id", sa.Integer(), nullable=True, index=True),
        sa.Column("symbol", sa.String(20), nullable=True),
        sa.Column("action", sa.String(16), nullable=False),
        sa.Column("confidence", sa.Integer(), nullable=True),
        sa.Column("signal_json", sa.JSONB(), nullable=False),
        sa.Column("check_result", sa.JSONB(), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, index=True),
        sa.Column("reject_reason", sa.Text(), nullable=True),
        sa.Column("order_id", sa.String(64), nullable=True),
        sa.Column("executed_at", sa.String(64), nullable=True),
        sa.Column("created_at", sa.String(64), nullable=False, index=True),
        schema="analysis",
    )

    # ── analysis.audit_log ──
    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column("event", sa.String(32), nullable=False, index=True),
        sa.Column("user_id", sa.Integer(), nullable=True, index=True),
        sa.Column("symbol", sa.String(20), nullable=True),
        sa.Column("risk_level", sa.String(8), nullable=False),
        sa.Column("service", sa.String(32), nullable=True),
        sa.Column("build_commit", sa.String(64), nullable=True),
        sa.Column("is_audit_mode", sa.Boolean(), nullable=False),
        sa.Column("details", sa.JSONB(), nullable=True),
        sa.Column("timestamp", sa.String(64), nullable=False, index=True),
        schema="analysis",
    )


def downgrade() -> None:
    op.drop_table("audit_log", schema="analysis")
    op.drop_table("signal_audit", schema="analysis")
    op.drop_table("daily_reports", schema="analysis")
    op.drop_index("ix_market_kline_daily_symbol_trade_date", table_name="kline_daily", schema="market")
    op.drop_table("kline_daily", schema="market")
    op.execute("DROP SCHEMA IF EXISTS analysis")
    op.execute("DROP SCHEMA IF EXISTS market")
