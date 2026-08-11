"""
market_hours.py — A股/港股交易时段判断（含假期过滤）
"""
from datetime import datetime, time as dt_time, timezone, timedelta
from app.engine.holiday_calendar import is_a_share_holiday, is_hk_holiday


def _now_bj() -> datetime:
    """当前北京时间"""
    return datetime.now(timezone.utc) + timedelta(hours=8)


def _today_bj_date():
    """当前北京日期"""
    return _now_bj().date()


def is_market_hours() -> bool:
    """判断当前是否为 A 股交易时段（交易日 9:30-11:30, 13:00-15:00）"""
    now_bj = _now_bj()
    # 周末
    if now_bj.weekday() >= 5:
        return False
    # 节假日（含调休补班检测）
    if is_a_share_holiday(_today_bj_date()):
        return False
    t = now_bj.time()
    return (dt_time(9, 30) <= t <= dt_time(11, 30)) or (dt_time(13, 0) <= t <= dt_time(15, 0))


def is_hk_market_hours() -> bool:
    """判断当前是否为港股交易时段（交易日 9:30-12:00, 13:00-16:00）"""
    now_bj = _now_bj()
    if now_bj.weekday() >= 5:
        return False
    if is_hk_holiday(_today_bj_date()):
        return False
    t = now_bj.time()
    return (dt_time(9, 30) <= t <= dt_time(12, 0)) or (dt_time(13, 0) <= t <= dt_time(16, 0))


def is_any_market_hours() -> bool:
    """任一市场处于交易时段（A 股或港股）"""
    return is_market_hours() or is_hk_market_hours()
