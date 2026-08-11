"""
holiday_calendar.py — A股/港股假期日历

- A股假期：依赖 chinese-calendar 包（准确处理农历假期和调休）
- 港股假期：维护 JSON 配置文件，每年更新
"""
import json
import os
from datetime import date, datetime, timezone, timedelta

# ========================= A 股假期 =========================

def is_a_share_holiday(d: date) -> bool:
    """判断某日是否为 A 股休市日（非交易日）。
    工作日=周一至周五且非节假日且非调休补班日。
    chinese-calendar 包直接返回 is_workday。
    """
    try:
        from chinese_calendar import is_workday
        # chinese-calendar 的 is_workday 已处理节假日和补班
        return not is_workday(d)
    except ImportError:
        # fallback: 仅按周末判断
        return d.weekday() >= 5


# ========================= 港股假期 =========================

_HK_CALENDAR_FILE = os.path.join(os.path.dirname(__file__), "hk_holidays.json")
_HK_HOLIDAYS_CACHE: set[str] | None = None


def _load_hk_holidays() -> set[str]:
    """加载港股假期日期集合（ISO 格式字符串）。"""
    global _HK_HOLIDAYS_CACHE
    if _HK_HOLIDAYS_CACHE is not None:
        return _HK_HOLIDAYS_CACHE
    try:
        with open(_HK_CALENDAR_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        _HK_HOLIDAYS_CACHE = set(data.get("holidays", []))
    except (FileNotFoundError, json.JSONDecodeError):
        _HK_HOLIDAYS_CACHE = set()
    return _HK_HOLIDAYS_CACHE


def is_hk_holiday(d: date) -> bool:
    """判断某日是否为港股休市日（周末或香港公众假期）。"""
    if d.weekday() >= 5:
        return True
    holidays = _load_hk_holidays()
    return d.isoformat() in holidays


# ========================= 联合查询 =========================

def is_trading_day_a() -> bool:
    """今天是否为 A 股交易日。"""
    today = datetime.now(timezone.utc).date() + timedelta(hours=8)  # 北京时间
    return not is_a_share_holiday(today)


def is_trading_day_hk() -> bool:
    """今天是否为港股交易日。"""
    today = datetime.now(timezone.utc).date() + timedelta(hours=8)
    return not is_hk_holiday(today)
