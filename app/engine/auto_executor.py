"""
auto_executor.py — 信号自动执行引擎

全托管模式：自动执行高置信度信号（下单 + 更新持仓）
建议模式：信号入库为 pending，由前端展示
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import AgentSignal, AgentPortfolio, UserAgent, AgentTrader, AgentConfig
from app.services import trading as trading_service
from app.schemas.trading import OrderRequest
from app.core.exceptions import AppException
from app.engine.market_hours import is_market_hours
from app.services.agent_config_service import DEFAULTS as CONFIG_DEFAULTS

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


async def auto_execute_signals(
    db: AsyncSession,
    hire_id: int,
    user_id: int,
    signals: list[dict],
    management_mode: str,
    config: AgentConfig | None = None,
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
        return await _auto_execute(db, hire_id, user_id, signals, config)
    else:
        # 建议模式：全部保持 pending，等待用户确认
        return {"executed": [], "failed": [], "pending": signals, "mode": "advisory"}


async def _auto_execute(
    db: AsyncSession,
    hire_id: int,
    user_id: int,
    signals: list[dict],
    config: AgentConfig | None = None,
) -> dict[str, Any]:
    """全托管模式：自动执行高置信度信号"""
    if not signals:
        return {"executed": [], "failed": [], "pending": [], "mode": "full_managed"}

    # P1: 从配置读取置信度阈值和最大执行数
    confidence_threshold = config.auto_exec_confidence if config and config.auto_exec_confidence else CONFIG_DEFAULTS["auto_exec_confidence"]
    max_exec = config.max_auto_exec_per_round if config and config.max_auto_exec_per_round else CONFIG_DEFAULTS["max_auto_exec_per_round"]

    # 按置信度降序排列
    executable = [
        s for s in signals
        if s["action"] in ("buy", "sell")
        and s.get("confidence", 0) >= confidence_threshold
    ]
    executable.sort(key=lambda x: x.get("confidence", 0), reverse=True)
    executable = executable[:max_exec]

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
                .values(exec_status="auto_executed", updated_at=datetime.now(timezone.utc))
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
    qty = signal.get("quantity", 100)
    # A股交易单位：买入向上取整到整手(100股)，卖出向下取整到整手，最少1手
    if signal["action"] == "sell":
        lot_qty = max(100, (qty // 100) * 100)
    else:
        lot_qty = max(100, ((qty + 99) // 100) * 100)

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
        # 构造与 hosted_engine 一致的 signal_id 格式，保证落款可正确关联交易员
        sig_id = (
            f"sig_{user_id}_{trading_symbol}_{int(datetime.now(timezone.utc).timestamp())}"
            if signal.get("id") else None
        )
        order_result = await trading_service.place_order(
            db=db,
            user=user_stub,
            req=order_req,
            fallback_price=float(signal.get("price", 0)),
            signal_id=sig_id,
        )

        await _update_portfolio(
            db, hire_id, user_id, signal, signal.get("trader_id", ""),
            order_result.filled_price, order_result.filled_quantity
        )

        if signal.get("id"):
            s = await db.get(AgentSignal, signal["id"])
            if s:
                s.exec_status = "auto_executed"
                s.updated_at = datetime.now(timezone.utc)

        await db.commit()
        return {
            "success": True,
            "order_id": order_result.id,
            "filled_price": order_result.filled_price,
            "filled_quantity": order_result.filled_quantity,
        }

    except AppException as e:
        logger.warning("真实下单失败，标记信号为 failed（不模拟、不误标已执行）: %s", e.message)
        if signal.get("id"):
            s = await db.get(AgentSignal, signal["id"])
            if s:
                s.exec_status = "failed"
                s.updated_at = datetime.now(timezone.utc)
                await db.commit()
        return {"success": False, "error": str(e.message)}
    except Exception as e:
        logger.warning("下单异常，标记信号为 failed（不模拟、不误标已执行）: %s", str(e))
        if signal.get("id"):
            s = await db.get(AgentSignal, signal["id"])
            if s:
                s.exec_status = "failed"
                s.updated_at = datetime.now(timezone.utc)
                await db.commit()
        return {"success": False, "error": str(e)}


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
