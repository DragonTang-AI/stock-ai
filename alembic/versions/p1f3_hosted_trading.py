"""P1-F3: AI托管设置 + 托管日志表
Revision ID: p1f3_hosted_trading
"""
from alembic import op

revision = "p1f3_hosted_trading"
down_revision = "p0f2_multi_schema"
branch_labels = None
depends_on = None


def upgrade():
    # 托管设置（每用户一条）
    op.execute("""
        CREATE TABLE IF NOT EXISTS public.hosted_settings (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id INTEGER NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
            mode VARCHAR(10) NOT NULL DEFAULT 'MANUAL',
            max_position_ratio REAL,
            max_single_trade_ratio REAL,
            min_confidence INTEGER,
            enabled_at TIMESTAMPTZ,
            disabled_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW(),
            CONSTRAINT hosted_settings_user_unique UNIQUE (user_id)
        )
    """)
    # 托管执行日志
    op.execute("""
        CREATE TABLE IF NOT EXISTS public.hosted_logs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id INTEGER NOT NULL,
            signal_id UUID,
            order_id INTEGER,
            action VARCHAR(10) NOT NULL,
            symbol VARCHAR(20),
            target_price REAL,
            qty INTEGER,
            reason TEXT,
            status VARCHAR(10) NOT NULL,
            error TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    # accounts 表加 mode 列
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema='public' AND table_name='accounts' AND column_name='mode'
            ) THEN
                ALTER TABLE public.accounts ADD COLUMN mode VARCHAR(10) DEFAULT 'MANUAL';
            END IF;
        END $$;
    """)
    # orders 表加 signal_id 列
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema='public' AND table_name='orders' AND column_name='signal_id'
            ) THEN
                ALTER TABLE public.orders ADD COLUMN signal_id VARCHAR(36);
            END IF;
        END $$;
    """)
    # alembic 版本
    op.execute("""
        INSERT INTO public.alembic_version (version_num) VALUES ('p1f3_hosted_trading')
        ON CONFLICT DO NOTHING
    """)


def downgrade():
    op.execute("ALTER TABLE public.orders DROP COLUMN IF EXISTS signal_id")
    op.execute("DROP TABLE IF EXISTS public.hosted_logs")
    op.execute("DROP TABLE IF EXISTS public.hosted_settings")
    op.execute("ALTER TABLE public.accounts DROP COLUMN IF EXISTS mode")
