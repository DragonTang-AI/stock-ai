"""P1-F4: K线唯一约束 + signal_id 类型修复
Revision ID: p1f4_kline_unique
"""
from alembic import op

revision = "p1f4_kline_unique"
down_revision = "p1f3_hosted_trading"
branch_labels = None
depends_on = None


def upgrade():
    # ── 1. market.kline_daily 唯一约束 + 索引 ──
    op.execute("""
        ALTER TABLE market.kline_daily
        ADD CONSTRAINT uk_kline_symbol_date_market
        UNIQUE (symbol, trade_date, market);
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_kline_symbol_date
        ON market.kline_daily (symbol, trade_date DESC);
    """)

    # ── 2. 稳定性修复：hosted_logs.signal_id UUID → VARCHAR(36) ──
    # 后端 HostedLogItem.signal_id 是 Optional[str]，但 DB 列是 UUID 类型，
    # 触发时传字符串 signal_id 被隐式转换，后续查询可能报错。统一为 varchar(36)。
    op.execute("""
        ALTER TABLE public.hosted_logs
        ALTER COLUMN signal_id TYPE varchar(36)
        USING signal_id::text;
    """)


def downgrade():
    op.execute("""
        ALTER TABLE public.hosted_logs
        ALTER COLUMN signal_id TYPE uuid
        USING signal_id::uuid;
    """)
    op.execute("""
        DROP INDEX IF EXISTS ix_kline_symbol_date;
    """)
    op.execute("""
        ALTER TABLE market.kline_daily
        DROP CONSTRAINT IF EXISTS uk_kline_symbol_date_market;
    """)
