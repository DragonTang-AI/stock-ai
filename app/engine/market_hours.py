"""
market_hours.py — A股/港股交易时段判断
"""
from datetime import datetime, time as dt_time, timezone, timedelta


def _now_bj() -> datetime:
    """当前北京时间"""
    return datetime.now(timezone.utc) + timedelta(hours=8)


def is_market_hours() -> bool:
    """判断当前是否为 A 股交易时段（周一至周五 9:30-11:30, 13:00-15:00）"""
    now_bj = _now_bj()
    if now_bj.weekday() >= 5:
        return False
    t = now_bj.time()
    return (dt_time(9, 30) <= t <= dt_time(11, 30)) or (dt_time(13, 0) <= t <= dt_time(15, 0))


def is_hk_market_hours() -> bool:
    """
    判断当前是否为港股交易时段（周一至周五 9:30-12:00, 13:00-16:00）。

    注：港股有午间休市（12:00-13:00）和香港公众假期休市，
    假期日历首期不纳入（周末已排除）。
    """
    now_bj = _now_bj()
    if now_bj.weekday() >= 5:
        return False
    t = now_bj.time()
    return (dt_time(9, 30) <= t <= dt_time(12, 0)) or (dt_time(13, 0) <= t <= dt_time(16, 0))


def is_any_market_hours() -> bool:
    """任一市场处于交易时段（A 股或港股）"""
    return is_market_hours() or is_hk_market_hours()
