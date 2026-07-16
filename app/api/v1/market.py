"""
app/api/v1/market.py — 行情路由（真实 AkShare 实现）
公开行情数据，无需登录即可访问
"""
from fastapi import APIRouter, Depends, Query
from typing import List, Optional
from app.models.user import User
from app.api.v1.auth import get_current_user_optional
from app.core.exceptions import AppException
from app.schemas.market import QuoteItem, QuoteResponse, KLineItem, KLineResponse, StockDetailResponse
from app.services import market as market_service

router = APIRouter()


def _normalize_symbol(symbol: str) -> str:
    """
    标准化股票代码格式。
    支持: sh600519 / sz000001 / 600519.SH / 000001.SZ → 600519.SH / 000001.SZ
    """
    s = symbol.strip().upper()
    # 如果已经是标准格式 (如 600519.SH)，直接返回
    if "." in s:
        return s
    # 处理 sh600519 / sz000001 格式
    if s.startswith("SH"):
        return s[2:] + ".SH"
    if s.startswith("SZ"):
        return s[2:] + ".SZ"
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
        raise AppException(code="DETAIL_FAILED", message=f"获取详情失败: {e}", status_code=500)


@router.get("/indices")
async def get_indices():
    """大盘指数（占位桩）"""
    return {"success": True, "data": [
        {"symbol": "000001.SH", "name": "上证指数", "price": 3350.53, "change_pct": 0.51},
        {"symbol": "399001.SZ", "name": "深证成指", "price": 10823.17, "change_pct": 0.83},
        {"symbol": "399006.SZ", "name": "创业板指", "price": 2215.39, "change_pct": 1.26},
    ]}

@router.get("/rules/{market}")
async def get_market_rules(market: str):
    """市场交易规则"""
    return {"success": True, "data": {
        "market": market.upper(),
        "lot_size": 100,
        "price_limit_pct": 10,
        "commission_rate": 0.00025,
        "min_commission": 5,
        "stamp_tax_rate": 0.001,
        "stamp_tax_side": "SELL",
        "settlement": "T+1",
    }}
