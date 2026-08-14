"""daily picks dual engine (factor + committee_llm) + pick_tracking

Revision ID: daily_llm_dual_engine
Revises: 14f5cc35bc1e
Create Date: 2026-08-14 10:30:00
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "daily_llm_dual_engine"
down_revision: Union[str, None] = "14f5cc35bc1e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    # ── daily_picks: 加 engine 列（默认 factor，兼容存量记录） ──
    op.add_column(
        "daily_picks",
        sa.Column("engine", sa.String(32), nullable=False, server_default="factor", comment="生成引擎: factor/committee_llm"),
    )

    # ── 唯一约束升级为 (trade_date, market, engine) ──
    op.drop_constraint("uq_daily_picks_date_market", "daily_picks", type_="unique")
    op.create_unique_constraint(
        "uq_daily_picks_date_market_engine",
        "daily_picks",
        ["trade_date", "market", "engine"],
    )

    # ── pick_tracking: 每日推荐逐票追踪（回测闭环数据源） ──
    op.create_table(
        "pick_tracking",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("trade_date", sa.String(16), nullable=False, comment="推荐生成日 YYYY-MM-DD"),
        sa.Column("market", sa.String(8), nullable=False, default="A"),
        sa.Column("engine", sa.String(32), nullable=False, comment="factor/committee_llm"),
        sa.Column("symbol", sa.String(32), nullable=False),
        sa.Column("symbol_name", sa.String(64), nullable=True),
        sa.Column("action", sa.String(16), nullable=True),
        sa.Column("confidence", sa.Integer(), nullable=True),
        sa.Column("entry_price", sa.Numeric(12, 4), nullable=True, comment="入场价(回测回填)"),
        sa.Column("t5_return", sa.Numeric(12, 4), nullable=True, comment="T+5 收益率 %"),
        sa.Column("t5_benchmark_return", sa.Numeric(12, 4), nullable=True, comment="T+5 基准收益率 %(A:沪深300/HK:恒指)"),
        sa.Column("t20_return", sa.Numeric(12, 4), nullable=True, comment="T+20 收益率 %"),
        sa.Column("t20_benchmark_return", sa.Numeric(12, 4), nullable=True, comment="T+20 基准收益率 %"),
        sa.Column("backtest_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("trade_date", "market", "engine", "symbol", name="uq_pick_tracking_date_market_engine_symbol"),
    )
    op.create_index("ix_pick_tracking_trade_date", "pick_tracking", ["trade_date"])
    op.create_index("ix_pick_tracking_engine", "pick_tracking", ["engine"])


def downgrade() -> None:
    op.drop_index("ix_pick_tracking_engine", table_name="pick_tracking")
    op.drop_index("ix_pick_tracking_trade_date", table_name="pick_tracking")
    op.drop_table("pick_tracking")
    op.drop_constraint("uq_daily_picks_date_market_engine", "daily_picks", type_="unique")
    op.create_unique_constraint("uq_daily_picks_date_market", "daily_picks", ["trade_date", "market"])
    op.drop_column("daily_picks", "engine")
