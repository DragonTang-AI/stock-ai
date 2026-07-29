"""
market_hours.py — A股/港股交易时段判断
"""
from datetime import datetime, time as dt_time, timezone, timedelta


def is_market_hours() -> bool:
    """判断当前是否为 A 股交易时段（周一至周五 9:30-11:30, 13:00-15:00）"""
    now_utc = datetime.now(timezone.utc)
    now_bj = now_utc + timedelta(hours=8)
    if now_bj.weekday() >= 5:
        return False
    t = now_bj.time()
    return (dt_time(9, 30) <= t <= dt_time(11, 30)) or (dt_time(13, 0) <= t <= dt_time(15, 0))
