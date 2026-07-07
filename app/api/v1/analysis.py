"""
app.api.v1.analysis.py — 智能投资助手路由

端点：
- GET  /diagnose          全面试仓诊断
- GET  /diagnose/{symbol} 单只持仓诊断
- POST /chat/context      构建问答上下文（供 LLM 使用）
- GET  /market/temperature 大盘温度计
"""
import logging
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.user import User
from app.api.v1.auth import get_current_user
from app.schemas.advisor import PortfolioDiagnosisResponse, ChatContextResponse, ChatRequest
from app.services.advisor import diagnose_portfolio, build_chat_context, _get_market_temperature
from app.services.market import fetch_stock_detail

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/diagnose", response_model=PortfolioDiagnosisResponse)
async def get_portfolio_diagnosis(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    全面持仓诊断

    返回：
    - summary: 账户总览（资产/盈亏/胜率/现金比例）
    - positions: 逐只持仓诊断（评级/信号/建议动作）
    - risks: 风险项列表（集中度/行业/亏损/胜率）
    - suggestions: 操作建议清单（按优先级排序）
    - market_temperature: 大盘温度（上证/深证/创业板）
    - disclaimer: 免责声明
    """
    try:
        result = await diagnose_portfolio(db, current_user)
        return {"success": True, "data": result}
    except Exception as e:
        logger.error(f"持仓诊断失败: {e}", exc_info=True)
        return {"success": False, "data": None, "error": str(e)}


@router.get("/diagnose/{symbol}", response_model=PortfolioDiagnosisResponse)
async def diagnose_single_stock(
    symbol: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    单只股票诊断（不需持仓，任意股票均可）

    返回该股票的技术面分析：
    - 行情数据
    - RSI / MACD / 布林带 / 均线
    - 技术信号列表
    - 评级
    """
    try:
        detail = await fetch_stock_detail(symbol)
        if not detail:
            return {"success": False, "data": None, "error": f"未找到 {symbol}"}

        # 复用信号逻辑
        from app.services.advisor import _diagnose_single_position
        from app.models.trading import Position
        from decimal import Decimal

        # 构造一个临时 Position 对象
        fake_pos = Position(
            symbol=symbol,
            name=detail.get("name", symbol),
            quantity=100,
            cost_price=Decimal(str(detail.get("price", 0))),
            market_price=Decimal(str(detail.get("price", 0))),
            market_value=Decimal(str(detail.get("price", 0) * 100)),
            profit=Decimal("0"),
            profit_pct=Decimal("0"),
            cost_amount=Decimal(str(detail.get("price", 0) * 100)),
        )

        diag = await _diagnose_single_position(fake_pos, detail.get("price", 0) * 100)

        return {
            "success": True,
            "data": {
                "stock": {
                    "symbol": symbol,
                    "name": detail.get("name"),
                    "price": detail.get("price"),
                    "change_pct": detail.get("change_pct"),
                    "pe_ratio": detail.get("pe_ratio"),
                    "market_cap": detail.get("market_cap"),
                },
                "indicators": diag.get("indicators"),
                "signals": diag.get("signals"),
                "rating": diag.get("rating"),
                "rating_text": diag.get("rating_text"),
                "confidence": diag.get("confidence"),
                "action": diag.get("action"),
            },
        }
    except Exception as e:
        logger.error(f"单股诊断失败 {symbol}: {e}", exc_info=True)
        return {"success": False, "data": None, "error": str(e)}


@router.post("/chat/context", response_model=ChatContextResponse)
async def get_chat_context(
    req: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    构建智能问答上下文

    前端调用此接口获取结构化上下文，然后连同用户问题一起发给 LLM，
    LLM 基于上下文给出个性化回答。

    上下文包含：
    - 用户持仓概览
    - 风险项
    - 操作建议
    - 大盘温度
    - 问题中提到的股票详情
    """
    try:
        ctx = await build_chat_context(db, current_user, req.question)
        return {"success": True, "data": ctx}
    except Exception as e:
        logger.error(f"构建问答上下文失败: {e}", exc_info=True)
        return {"success": False, "data": None, "error": str(e)}


@router.get("/market/temperature")
async def get_market_temperature(
    current_user: User = Depends(get_current_user),
):
    """
    大盘温度计

    返回上证指数、深证成指、创业板指的涨跌情况及温度等级。
    """
    temp = await _get_market_temperature()
    return {"success": True, "data": temp}
