"""
auto_executor.py — 信号自动执行引擎

全托管模式：自动执行高置信度信号（下单 + 更新持仓）
建议模式：信号入库为 pending，由前端展示
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import AgentSignal, AgentPortfolio, UserAgent, AgentTrader
from app.services import trading as trading_service
from app.schemas.trading import OrderRequest
from app.core.exceptions import AppException
from app.engine.market_hours import is_market_hours

logger = logging.getLogger(__name__)


def _normalize_to_trading_symbol(raw_symbol: str) -> str:
    s = raw_symbol.strip()
    if '.' in s:
        return s.upper()
    if s.startswith('6'):
        return f'{s}.SH'
    elif s.startswith(('0', '3')):
        return f'{s}.SZ'
    elif s.startswith(('4', '8')):
        return f'{s}.BJ'
    return s.upper()


def _round_to_lot(quantity: int) -> int:
    return max(100, (quantity // 100) * 100)


# 全托管模式下自动执行的置信度阈值
AUTO_EXEC_CONFIDENCE_THRESHOLD = 50
# 每次最多自动执行的信号数
MAX_AUTO_EXEC_SIGNALS = 2


async def auto_execute_signals(
    db: AsyncSession,
    hire_id: int,
    user_id: int,
    signals: list[dict],
    management_mode: str,
) -> dict[str, Any]:
    """
    自动执行信号

    Returns:
        {"executed": [...], "pending": [...], "failed": [...], "mode": "..."}
    """
    # 非交易时段不执行
    if not is_market_hours():
        logger.warning("非交易时段，跳过自动执行 hire=%d", hire_id)
        return {"executed": [], "failed": [], "pending": signals, "mode": "full_managed", "skipped_reason": "非交易时段"}

    if management_mode == "full_managed":
        return await _auto_execute(db, hire_id, user_id, signals)
    else:
        # 建议模式：全部保持 pending，等待用户确认
        return {"executed": [], "failed": [], "pending": signals, "mode": "advisory"}


async def _auto_execute(
    db: AsyncSession,
    hire_id: int,
    user_id: int,
    signals: list[dict],
) -> dict[str, Any]:
    """全托管模式：自动执行高置信度信号"""
    if not signals:
        return {"executed": [], "failed": [], "pending": [], "mode": "full_managed"}

    # 按置信度降序排列
    executable = [
        s for s in signals
        if s["action"] in ("buy", "sell")
        and s.get("confidence", 0) >= AUTO_EXEC_CONFIDENCE_THRESHOLD
    ]
    executable.sort(key=lambda x: x.get("confidence", 0), reverse=True)
    executable = executable[:MAX_AUTO_EXEC_SIGNALS]

    executed = []
    failed = []

    for sig in executable:
        try:
            result = await _execute_single_signal(db, hire_id, user_id, sig)
            if result["success"]:
                executed.append({**sig, "order_result": result})
                logger.info(
                    "全托管自动执行: hire=%d symbol=%s action=%s conf=%d%%",
                    hire_id, sig["symbol"], sig["action"], sig["confidence"]
                )
            else:
                failed.append({**sig, "error": result.get("error", "未知错误")})
        except Exception as e:
            failed.append({**sig, "error": str(e)})
            logger.error("全托管自动执行异常: hire=%d symbol=%s %s", hire_id, sig["symbol"], str(e))

    # 更新已执行信号状态
    if executed:
        exec_ids = [s["id"] for s in executed if s.get("id")]
        if exec_ids:
            from sqlalchemy import update as sa_update
            await db.execute(
                sa_update(AgentSignal)
                .where(AgentSignal.id.in_(exec_ids))
                .values(exec_status="auto_executed", updated_at=datetime.utcnow())
            )

    pending = [s for s in signals if s not in executable]
    await db.commit()

    return {
        "executed": executed,
        "failed": failed,
        "pending": pending,
        "mode": "full_managed",
    }


async def _execute_single_signal(
    db: AsyncSession,
    hire_id: int,
    user_id: int,
    signal: dict,
) -> dict[str, Any]:
    """执行单条信号：下单 + 更新持仓"""
    trading_symbol = _normalize_to_trading_symbol(signal["symbol"])
    lot_qty = _round_to_lot(signal.get("quantity", 100))

    try:
        order_req = OrderRequest(
            symbol=trading_symbol,
            side=signal["action"],
            quantity=lot_qty,
            price=float(signal.get("price", 0)),
            order_type="market",
        )
        # Fast user stub
        user_stub = type("User", (), {"id": user_id})()
        order_result = await trading_service.place_order(
            db=db,
            user=user_stub,
            req=order_req,
            fallback_price=float(signal.get("price", 0)),
        )

        await _update_portfolio(
            db, hire_id, user_id, signal, signal.get("trader_id", ""),
            order_result.filled_price, order_result.filled_quantity
        )

        if signal.get("id"):
            s = await db.get(AgentSignal, signal["id"])
            if s:
                s.exec_status = "auto_executed"
                s.updated_at = datetime.utcnow()

        await db.commit()
        return {
            "success": True,
            "order_id": order_result.id,
            "filled_price": order_result.filled_price,
            "filled_quantity": order_result.filled_quantity,
        }

    except AppException as e:
        logger.info("真实下单失败，使用模拟执行: %s", e.message)
        await _simulate_execution(db, hire_id, user_id, signal)
        return {"success": True, "simulated": True, "reason": str(e.message)}
    except Exception as e:
        logger.warning("下单异常，使用模拟执行: %s", str(e))
        await _simulate_execution(db, hire_id, user_id, signal)
        return {"success": True, "simulated": True, "reason": str(e)}


async def _simulate_execution(
    db: AsyncSession,
    hire_id: int,
    user_id: int,
    signal: dict,
):
    """模拟执行：直接更新持仓"""
    price = float(signal.get("price", 0))
    quantity = signal.get("quantity", 100)
    trader_id = signal.get("trader_id", "")

    await _update_portfolio(db, hire_id, user_id, signal, trader_id, price, quantity)

    if signal.get("id"):
        s = await db.get(AgentSignal, signal["id"])
        if s:
            s.exec_status = "auto_executed"
            s.updated_at = datetime.utcnow()

    await db.commit()


async def _update_portfolio(
    db: AsyncSession,
    hire_id: int,
    user_id: int,
    signal: dict,
    trader_id: str,
    price: float,
    quantity: int,
):
    """更新持仓"""
    pf_result = await db.execute(
        select(AgentPortfolio).where(
            and_(
                AgentPortfolio.hire_id == hire_id,
                AgentPortfolio.symbol == signal["symbol"],
            )
        )
    )
    portfolio = pf_result.scalar_one_or_none()

    if signal["action"] == "buy":
        if portfolio:
            total_cost = float(portfolio.avg_cost) * portfolio.quantity + price * quantity
            portfolio.quantity += quantity
            portfolio.avg_cost = total_cost / portfolio.quantity
            portfolio.current_price = price
            portfolio.market_value = price * portfolio.quantity
            portfolio.unrealized_pnl = portfolio.market_value - float(portfolio.avg_cost) * portfolio.quantity
        else:
            portfolio = AgentPortfolio(
                hire_id=hire_id,
                trader_id=trader_id,
                user_id=user_id,
                symbol=signal["symbol"],
                symbol_name=signal.get("name", signal["symbol"]),
                quantity=quantity,
                avg_cost=price,
                current_price=price,
                market_value=price * quantity,
                unrealized_pnl=0,
            )
            db.add(portfolio)

    elif signal["action"] == "sell" and portfolio:
        if portfolio.quantity >= quantity:
            portfolio.quantity -= quantity
            if portfolio.quantity == 0:
                await db.delete(portfolio)
            else:
                portfolio.current_price = price
                portfolio.market_value = price * portfolio.quantity
                portfolio.unrealized_pnl = portfolio.market_value - float(portfolio.avg_cost) * portfolio.quantity
