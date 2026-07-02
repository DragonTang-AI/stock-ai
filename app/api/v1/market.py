"""
app/api/v1/market.py — 行情路由（Phase 2 实现）
"""
from fastapi import APIRouter, Depends
from app.models.user import User
from app.api.v1.auth import get_current_user

router = APIRouter()


@router.get("/quotes")
async def get_quotes(
    symbols: str = "600519.SH,000001.SZ",
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    获取行情报价。

    Args:
        symbols: 逗号分隔的股票代码，如 "600519.SH,000001.SZ"

    Returns:
        行情数据列表
    """
    # TODO: Phase 2 实现，接入 AkShare
    return {
        "success": True,
        "data": [
            {"symbol": "600519.SH", "name": "贵州茅台", "price": 0.0, "change_pct": 0.0},
            {"symbol": "000001.SZ", "name": "平安银行", "price": 0.0, "change_pct": 0.0},
        ],
        "note": "Phase 2 实现",
    }


@router.get("/kline/{symbol}")
async def get_kline(
    symbol: str,
    period: str = "daily",
    current_user: User = Depends(get_current_user),
) -> dict:
    """K线数据（占位，Phase 2 实现）"""
    return {"success": True, "symbol": symbol, "note": "Phase 2 实现", "data": []}
