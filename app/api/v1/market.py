"""
app/api/v1/market.py — 行情路由（真实 AkShare 实现）
公开行情数据，无需登录即可访问
"""
from fastapi import APIRouter, Depends, Query
from typing import List, Optional
from app.models.user import User
from app.api.v1.auth import get_current_user_optional
import logging
from app.core.exceptions import AppException
from app.schemas.market import QuoteItem, QuoteResponse, KLineItem, KLineResponse, StockDetailResponse
from app.services import market as market_service

logger = logging.getLogger(__name__)

router = APIRouter()


def _normalize_symbol(symbol: str) -> str:
    """
    标准化股票代码格式。
    支持: sh600519 / sz000001 / 600519.SH / 000001.SZ / hk00700 / 00700.HK → 600519.SH / 000001.SZ / 00700.HK
    """
    s = symbol.strip().upper()
    # 如果已经是标准格式 (如 600519.SH / 00700.HK)，直接返回
    if "." in s:
        return s
    # 处理 sh600519 / sz000001 / hk00700 格式
    if s.startswith("SH"):
        return s[2:] + ".SH"
    if s.startswith("SZ"):
        return s[2:] + ".SZ"
    if s.startswith("HK"):
        return s[2:] + ".HK"
    # 6 开头默认上海，其他默认深圳
    if s.startswith("6"):
        return s + ".SH"
    return s + ".SZ"


# 默认股票池：热门 A 股（未传 symbols 时返回）
DEFAULT_SYMBOLS = [
    "600519.SH",  # 贵州茅台
    "000001.SZ",  # 平安银行
    "600276.SH",  # 恒瑞医药
    "000858.SZ",  # 五粮液
    "601318.SH",  # 中国平安
    "000333.SZ",  # 美的集团
    "600036.SH",  # 招商银行
    "000651.SZ",  # 格力电器
    "601012.SH",  # 隆基绿能
    "300750.SZ",  # 宁德时代
]


@router.get("/quotes", response_model=QuoteResponse)
async def get_quotes(
    symbols: str = Query(
        None,
        description="逗号分隔的股票代码，如 600519.SH,000001.SZ。不传则返回默认热门股票池",
    ),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """
    获取实时行情报价（公开接口，无需登录）。

    Args:
        symbols: 逗号分隔的股票代码，如 "600519.SH,000001.SZ" 或 "sh600519,sz000001"。
                 不传则返回默认热门股票池。

    Returns:
        行情数据列表
    """
    if not symbols or not symbols.strip():
        symbol_list = DEFAULT_SYMBOLS
    else:
        symbol_list = [_normalize_symbol(s) for s in symbols.split(",")]
    quotes = await market_service.fetch_realtime_quotes(symbol_list)
    return {"success": True, "data": quotes}


@router.get("/kline/{symbol}", response_model=KLineResponse)
async def get_kline(
    symbol: str,
    period: str = Query("daily", description="周期：daily/weekly/monthly"),
    count: int = Query(100, description="返回条数"),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """
    获取 K 线历史数据（公开接口，无需登录）。

    Args:
        symbol: 股票代码，如 "600519.SH" 或 "sh600519"
        period: 周期，"daily"/"weekly"/"monthly"
        count: 返回条数（默认 100）

    Returns:
        K 线数据列表
    """
    normalized = _normalize_symbol(symbol)
    klines = await market_service.fetch_kline(normalized, period=period, count=count)
    return {"success": True, "symbol": normalized, "period": period, "data": klines}


@router.get("/detail/{symbol}", response_model=StockDetailResponse)
async def get_stock_detail(
    symbol: str,
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """
    获取股票详情（公开接口，无需登录）。

    返回实时行情 + K 线（日/周） + 均线技术指标。
    用于行情详情页（点击股票卡片跳转）。

    Args:
        symbol: 股票代码，如 "600519.SH" 或 "sh600519"

    Returns:
        行情 + K 线 + 均线数据
    """
    normalized = _normalize_symbol(symbol)
    try:
        detail = await market_service.fetch_stock_detail(normalized)
        return {"success": True, "data": detail, "message": ""}
    except AppException:
        raise
    except Exception as e:
        logger.error(f"Stock detail failed: {e}", exc_info=True)
        raise AppException(code="DETAIL_FAILED", message=f"获取详情失败: {e}", status_code=500)


@router.get("/indices")
async def get_indices(market: str = Query("A", description="市场：A=沪深指数 / HK=港股指数")):
    """大盘指数"""
    if market.upper() == "HK":
        from app.services.market import fetch_hk_indices
        data = await fetch_hk_indices()
        return {"success": True, "market": "HK", "data": data}
    return {"success": True, "market": "A", "data": [
        {"symbol": "000001.SH", "name": "上证指数", "price": 3350.53, "change_pct": 0.51},
        {"symbol": "399001.SZ", "name": "深证成指", "price": 10823.17, "change_pct": 0.83},
        {"symbol": "399006.SZ", "name": "创业板指", "price": 2215.39, "change_pct": 1.26},
    ]}

@router.get("/rules/{market}")
async def get_market_rules(market: str):
    """市场交易规则"""
    m = market.upper()
    if m == "HK":
        return {"success": True, "data": {
            "market": "HK",
            "lot_size": None,  # 港股每手股数因股而异
            "price_limit_pct": None,  # 港股无涨跌停限制
            "commission_rate": 0.0003,
            "min_commission": 15,
            "stamp_tax_rate": 0.0013,
            "stamp_tax_side": "BOTH",  # 买卖双向征收
            "settlement": "T+2",
            "trading_hours": {
                "morning": "09:30-12:00",
                "afternoon": "13:00-16:00",
            },
            "trading_currency": "HKD",
        }}
    return {"success": True, "data": {
        "market": "A",
        "lot_size": 100,
        "price_limit_pct": 10,
        "commission_rate": 0.00025,
        "min_commission": 5,
        "stamp_tax_rate": 0.001,
        "stamp_tax_side": "SELL",
        "settlement": "T+1",
        "trading_hours": {
            "morning": "09:30-11:30",
            "afternoon": "13:00-15:00",
        },
        "trading_currency": "CNY",
    }}

from app.schemas.market import RankResponse
import aiohttp
import json
import re as re_mod


@router.get("/ranking", response_model=RankResponse)
async def get_ranking(
    type: str = Query("gainers", description="排行类型: gainers(涨幅榜) / losers(跌幅榜) / hot(热门榜)"),
    limit: int = Query(20, ge=5, le=50, description="返回条数"),
    market: str = Query("A", description="市场：A=A股 / HK=港股"),
):
    """
    获取市场排行榜（公开接口，无需登录）。

    - A 股：全市场（东方财富/腾讯公开 HTTP API）
    - 港股：腾讯 API 热门池（恒指+国企+科技+热门中概）
    """
    from app.services.market import fetch_ranking

    data = await fetch_ranking(rank_type=type, limit=limit, market=market)
    return {"success": True, "type": type, "market": market.upper(), "data": data, "meta": {}}


# ─────────── 股票搜索 API（腾讯 smartbox，支持 A 股 + 港股） ───────────

SMARTBOX_URL = "https://smartbox.gtimg.cn/s3/"


@router.get("/search")
async def search_stocks(
    q: str = Query(..., description="搜索关键词，股票名称或代码"),
    limit: int = Query(20, ge=1, le=50, description="返回条数"),
):
    """
    搜索股票（公开接口，无需登录）。

    调用腾讯 smartbox 搜索 API，按名称或代码模糊匹配，覆盖 A 股 + 港股。
    返回: [{code, symbol, name, market, price, change_pct}]
    """
    import urllib.parse
    import json as json_mod

    if not q or not q.strip():
        return {"success": True, "data": [], "query": q}

    try:
        encoded = urllib.parse.quote(q.strip())
        url = f"{SMARTBOX_URL}?v=2&q={encoded}&t=all"
        timeout = aiohttp.ClientTimeout(total=5)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://gu.qq.com",
            }) as resp:
                raw_bytes = await resp.read()
    except Exception:
        return {"success": True, "data": [], "query": q, "note": "搜索服务暂时不可用"}

    raw = raw_bytes.decode("utf-8", errors="ignore")

    # smartbox 返回: v_hint="sh~000847~腾讯济安~txja~ZS^hk~00700~腾讯控股~txkg~GP^..."
    # 条目以 ^ 分隔，字段以 ~ 分隔：[0]=市场(sh/sz/hk) [1]=代码 [2]=名称 [3]=拼音 [4]=类型(GP股票/ZS指数/QZ权证)
    results = []
    try:
        match = re_mod.search(r'v_hint="(.+?)"', raw)
        if match:
            for item_str in match.group(1).split("^"):
                parts = item_str.split("~")
                if len(parts) < 5:
                    continue
                market_prefix = parts[0].lower()
                code = parts[1]
                name = parts[2]
                item_type = parts[4].upper()

                # 只保留股票类型（GP），指数(ZS)不纳入股票搜索结果
                if item_type != "GP":
                    continue
                # 仅 A 股 + 港股，过滤美股
                if market_prefix not in ("sh", "sz", "hk"):
                    continue

                if market_prefix == "hk":
                    symbol = code + ".HK"
                    market = "HK"
                elif market_prefix == "sh":
                    symbol = code + ".SH"
                    market = "A"
                else:
                    symbol = code + ".SZ"
                    market = "A"

                results.append({
                    "code": code,
                    "symbol": symbol,
                    "name": name,
                    "market": market,
                    "price": None,
                    "change_pct": None,
                })
                if len(results) >= limit:
                    break
    except Exception:
        pass

    return {"success": True, "data": results, "query": q}