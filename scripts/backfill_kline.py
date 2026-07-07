"""
scripts/backfill_kline.py — 一次性回填 K 线历史数据（P1-F4）

用途：
- 首次部署后，给存量标的补 250 个交易日历史 K 线
- 定时任务上线前的初始化

用法：
    cd /data/stockai/backend
    source /data/stockai/venv/bin/activate
    python scripts/backfill_kline.py --days 250 --concurrency 5

注意：
- 134 只标的 × 250 根 ≈ 33500 行，耗时约 20~40 分钟（受新浪限流影响）
- 支持断点续传：已存在的 (symbol, trade_date) 会 OnConflict 覆盖，重复跑安全
"""
import argparse
import asyncio
import logging

from app.tasks.kline_scheduler import run_daily_kline_collection, KLINE_DAYS, CONCURRENCY


async def main():
    parser = argparse.ArgumentParser(description="回填 K 线历史数据")
    parser.add_argument("--days", type=int, default=KLINE_DAYS, help="回溯交易日数（默认 250）")
    parser.add_argument("--concurrency", type=int, default=CONCURRENCY, help="并发数（默认 5）")
    args = parser.parse_args()

    # 覆盖模块级参数
    import app.tasks.kline_scheduler as ks
    ks.KLINE_DAYS = args.days
    ks.CONCURRENCY = args.concurrency

    logging.info(f"开始回填：days={args.days}, concurrency={args.concurrency}")
    result = await run_daily_kline_collection(days=args.days)
    logging.info(f"回填完成：{result}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
