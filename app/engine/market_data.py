"""
market_data.py — A 股数据适配器

为 ai-hedge-fund 提供 A 股数据（ai-hedge-fund 原生是美股）。
优先使用后端已有的行情数据接口（sina 数据源），获取实时价格。
从 stocks 表获取股票列表作为分析候选池。
"""
from __future__ import annotations

import asyncio
from datetime import date, datetime
from typing import Any

import httpx
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db


# ── 热门 A 股股票池（Phase 2 原有的 + 扩展）──

HOT_A_STOCKS: list[dict[str, str]] = [
    {"symbol": "600519", "name": "贵州茅台"},
    {"symbol": "300750", "name": "宁德时代"},
    {"symbol": "002594", "name": "比亚迪"},
    {"symbol": "000858", "name": "五粮液"},
    {"symbol": "601318", "name": "中国平安"},
    {"symbol": "000333", "name": "美的集团"},
    {"symbol": "600036", "name": "招商银行"},
    {"symbol": "002475", "name": "立讯精密"},
    {"symbol": "300059", "name": "东方财富"},
    {"symbol": "601012", "name": "隆基绿能"},
    {"symbol": "600276", "name": "恒瑞医药"},
    {"symbol": "002415", "name": "海康威视"},
    {"symbol": "300124", "name": "汇川技术"},
    {"symbol": "600900", "name": "长江电力"},
    {"symbol": "002371", "name": "北方华创"},
    {"symbol": "300274", "name": "阳光电源"},
    {"symbol": "601899", "name": "紫金矿业"},
    {"symbol": "600809", "name": "山西汾酒"},
    {"symbol": "300760", "name": "迈瑞医疗"},
    {"symbol": "002142", "name": "宁波银行"},
]


def get_ticker_map() -> dict[str, str]:
    """获取 symbol → name 映射"""
    return {s["symbol"]: s["name"] for s in HOT_A_STOCKS}


async def get_stock_list(db: AsyncSession, limit: int = 30) -> list[dict[str, str]]:
    """
    从 stocks 表获取股票列表作为分析候选池。
    如果 stocks 表为空，回退到 HOT_A_STOCKS。
    """
    try:
        result = await db.execute(
            text(
                "SELECT DISTINCT code, name FROM stocks "
                "WHERE status='active' AND code IS NOT NULL "
                "ORDER BY code LIMIT :limit"
            ),
            {"limit": limit},
        )
        rows = result.fetchall()
        if rows:
            return [{"symbol": row[0], "name": row[1] or row[0]} for row in rows]
    except Exception:
        pass

    return HOT_A_STOCKS[:limit]


async def get_realtime_price(symbol: str) -> dict[str, Any] | None:
    """
    通过新浪接口获取 A 股实时行情

    Returns:
        {"price": float, "change_pct": float, "volume": int, ...} or None
    """
    # 确定市场前缀：sh=上海, sz=深圳
    if symbol.startswith("6"):
        sina_code = "sh{}".format(symbol)
    elif symbol.startswith(("0", "3")):
        sina_code = "sz{}".format(symbol)
    else:
        return None

    url = "http://hq.sinajs.cn/list={}".format(sina_code)
    headers = {"Referer": "http://finance.sina.com.cn"}

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            text_data = resp.text

        # 新浪返回格式：var hq_str_sh600519="名称,今开,昨收,现价,最高,最低,..."
        if '="' not in text_data:
            return None

        data_str = text_data.split('="')[1].rstrip('";\n')
        fields = data_str.split(",")

        if len(fields) < 10 or fields[3] == "0.000":
            return None

        return {
            "symbol": symbol,
            "name": fields[0],
            "open": float(fields[1]) if fields[1] else 0,
            "prev_close": float(fields[2]) if fields[2] else 0,
            "price": float(fields[3]) if fields[3] else 0,
            "high": float(fields[4]) if fields[4] else 0,
            "low": float(fields[5]) if fields[5] else 0,
            "volume": int(float(fields[8])) if fields[8] else 0,
            "amount": float(fields[9]) if fields[9] else 0,
        }
    except Exception:
        return None


async def get_batch_prices(symbols: list[str]) -> dict[str, dict]:
    """批量获取实时价格"""
    results = {}
    # 新浪接口不支持批量，逐个获取但并发
    tasks = [get_realtime_price(s) for s in symbols]
    prices = await asyncio.gather(*tasks, return_exceptions=True)
    for sym, price in zip(symbols, prices):
        if isinstance(price, dict) and price:
            results[sym] = price
    return results


async def build_market_context(
    symbols: list[str],
) -> dict[str, Any]:
    """
    构建 ai-hedge-fund 所需的市场上下文数据

    包含：
    - 实时价格
    - 涨跌幅
    - 股票名称映射
    """
    prices = await get_batch_prices(symbols)
    ticker_map = get_ticker_map()

    context = {
        "prices": {},
        "ticker_map": ticker_map,
        "timestamp": datetime.now().isoformat(),
    }

    for sym in symbols:
        if sym in prices:
            p = prices[sym]
            context["prices"][sym] = {
                "name": p.get("name", ticker_map.get(sym, sym)),
                "price": p.get("price", 0),
                "change_pct": (
                    round((p["price"] - p["prev_close"]) / p["prev_close"] * 100, 2)
                    if p.get("prev_close") and p.get("price")
                    else 0
                ),
                "volume": p.get("volume", 0),
            }
        else:
            context["prices"][sym] = {
                "name": ticker_map.get(sym, sym),
                "price": 0,
                "change_pct": 0,
                "volume": 0,
            }

    return context
