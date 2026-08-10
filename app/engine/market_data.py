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
    {"symbol": "600036", "name": "招商银行"},
    {"symbol": "600519", "name": "贵州茅台"},
    {"symbol": "000858", "name": "五粮液"},
    {"symbol": "300750", "name": "宁德时代"},
    {"symbol": "002594", "name": "比亚迪"},
    {"symbol": "601318", "name": "中国平安"},
    {"symbol": "600900", "name": "长江电力"},
    {"symbol": "000333", "name": "美的集团"},
    {"symbol": "603259", "name": "药明康德"},
    {"symbol": "688981", "name": "中芯国际"},
]

# Phase 3: 港股候选池（试点 15 只）
HK_STOCK_POOL: list[dict[str, str]] = [
    {"symbol": "00700.HK", "name": "腾讯控股"},
    {"symbol": "09988.HK", "name": "阿里巴巴"},
    {"symbol": "01810.HK", "name": "小米集团"},
    {"symbol": "00941.HK", "name": "中国移动"},
    {"symbol": "09618.HK", "name": "京东集团"},
    {"symbol": "09999.HK", "name": "网易"},
    {"symbol": "02318.HK", "name": "中国平安"},
    {"symbol": "01299.HK", "name": "友邦保险"},
    {"symbol": "00388.HK", "name": "港交所"},
    {"symbol": "00005.HK", "name": "汇丰控股"},
    {"symbol": "02020.HK", "name": "安踏体育"},
    {"symbol": "00175.HK", "name": "吉利汽车"},
    {"symbol": "00981.HK", "name": "中芯国际"},
    {"symbol": "02269.HK", "name": "药明生物"},
    {"symbol": "01093.HK", "name": "石药集团"},
]


def get_ticker_map() -> dict[str, str]:
    """获取 symbol → name 映射（A+H 两市）"""
    m = {s["symbol"]: s["name"] for s in HOT_A_STOCKS}
    m.update({s["symbol"]: s["name"] for s in HK_STOCK_POOL})
    return m


async def get_stock_list(db: AsyncSession, limit: int = 10, markets: list[str] | None = None) -> list[dict[str, str]]:
    """
    返回股票列表作为分析候选池（A+H 混合）。

    Args:
        db: 数据库会话（保留参数，待 stocks 表后使用）
        limit: 返回数量上限
        markets: 市场筛选，默认 ["A", "HK"]；传 ["HK"] 仅港股
    """
    if markets is None:
        markets = ["A", "HK"]

    pool: list[dict[str, str]] = []
    if "A" in markets:
        pool.extend(HOT_A_STOCKS)
    if "HK" in markets:
        pool.extend(HK_STOCK_POOL)

    # 信号生成数量有限（Yahoo Finance 限流），多市场时优先交叉采样
    if "A" in markets and "HK" in markets:
        a_size = (limit + 1) // 2
        hk_size = limit - a_size
        return HOT_A_STOCKS[:a_size] + HK_STOCK_POOL[:hk_size]
    return pool[:limit]


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


def _is_hk(symbol: str) -> bool:
    """判断 symbol 是否为港股（以 .HK 结尾）"""
    return symbol.upper().endswith(".HK")


async def get_batch_prices(symbols: list[str]) -> dict[str, dict]:
    """批量获取实时价格（A 股走新浪，港股走腾讯）"""
    results: dict[str, dict] = {}
    a_symbols = [s for s in symbols if not _is_hk(s)]
    hk_symbols = [s for s in symbols if _is_hk(s)]

    # A 股：新浪逐个并发
    if a_symbols:
        tasks = [get_realtime_price(s) for s in a_symbols]
        prices = await asyncio.gather(*tasks, return_exceptions=True)
        for sym, price in zip(a_symbols, prices):
            if isinstance(price, dict) and price:
                results[sym] = price

    # 港股：腾讯批量接口
    if hk_symbols:
        try:
            from app.integrations.market_data.tencent import fetch_hk_quotes
            # 格式转换：00700.HK → hk00700
            hk_codes = ["hk{}".format(s.split(".")[0]) for s in hk_symbols]
            quotes = await fetch_hk_quotes(hk_codes)
            for q in quotes:
                # 腾讯返回的 code 格式为 hk00700，反向映射
                sym = "{}.HK".format(q.code.replace("hk", "", 1))
                if sym in hk_symbols:
                    results[sym] = {
                        "symbol": sym,
                        "name": q.name,
                        "open": q.open,
                        "prev_close": q.prev_close,
                        "price": q.price,
                        "high": q.high,
                        "low": q.low,
                        "volume": q.volume,
                        "amount": q.amount,
                        "market": "HK",
                    }
        except Exception:
            pass  # 港股行情失败不阻塞

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
