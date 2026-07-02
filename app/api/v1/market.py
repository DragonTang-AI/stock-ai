"""
app/api/v1/market.py — 行情路由（真实 AkShare 实现）
"""
from fastapi import APIRouter, Depends, Query
from typing import List
from app.models.user import User
from app.api.v1.auth import get_current_user
from app.schemas.market import QuoteItem, QuoteResponse, KLineItem, KLineResponse
from app.services import market as market_service

router = APIRouter()


@router.get("/quotes", response_model=QuoteResponse)
async def get_quotes(
    symbols: str = Query(..., description="逗号分隔的股票代码，如 600519.SH,000001.SZ"),
    current_user: User = Depends(get_current_user),
):
    """
    获取实时行情报价。

    Args:
        symbols: 逗号分隔的股票代码，如 "600519.SH,000001.SZ"

    Returns:
        行情数据列表
    """
    symbol_list = [s.strip() for s in symbols.split(",")]
    quotes = await market_service.fetch_realtime_quotes(symbol_list)
    return {"success": True, "data": quotes}


@router.get("/kline/{symbol}", response_model=KLineResponse)
async def get_kline(
    symbol: str,
    period: str = Query("daily", description="周期：daily/weekly/monthly"),
    count: int = Query(100, description="返回条数"),
    current_user: User = Depends(get_current_user),
):
    """
    获取 K 线历史数据。

    Args:
        symbol: 股票代码，如 "600519.SH"
        period: 周期，"daily"/"weekly"/"monthly"
        count: 返回条数（默认 100）

    Returns:
        K 线数据列表
    """
    klines = await market_service.fetch_kline(symbol, period=period, count=count)
    return {"success": True, "symbol": symbol, "period": period, "data": klines}
