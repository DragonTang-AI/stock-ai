"""
risk_manager.py — 风控规则

在信号生成后、写入 signals 表之前执行风控过滤：
- 单票仓位上限：不超过总资金的 30%
- 单日亏损熔断：当日亏损超过 5% 时暂停该交易员
- T+1 规则：当日买入的股票当日不可卖出
- 最大持仓数：单个交易员最多同时持有 5 只股票
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import AgentPortfolio, AgentSignal


# ── 风控参数 ──

MAX_POSITION_PCT = 0.30         # 单票仓位上限 30%
DAILY_LOSS_CIRCUIT_PCT = 0.05   # 单日亏损熔断线 5%
MAX_POSITION_COUNT = 5          # 最大持仓数
T1_ENABLED = True               # T+1 规则
TOTAL_CAPITAL = 100000.0        # 默认总资金（从 hire 配置读取）


async def check_risk(
    db: AsyncSession,
    hire_id: int,
    candidate_signals: list[dict],
    total_capital: float | None = None,
) -> tuple[list[dict], list[dict]]:
    """
    对候选信号执行风控过滤

    Args:
        db: 数据库会话
        hire_id: 雇佣关系 ID
        candidate_signals: 候选信号列表
        total_capital: 总资金（默认 100000）

    Returns:
        (passed_signals, rejected_signals)
        passed_signals: 通过风控的信号
        rejected_signals: 被拒绝的信号（含拒绝原因）
    """
    capital = total_capital or TOTAL_CAPITAL
    passed = []
    rejected = []

    today = date.today()

    # 1. 检查单日亏损熔断
    circuit_broken = await _check_daily_loss_circuit(db, hire_id, today)
    if circuit_broken:
        for sig in candidate_signals:
            rejected.append({**sig, "reject_reason": "单日亏损超过 5%，已触发熔断"})
        return passed, rejected

    # 2. 获取当前持仓
    positions = await _get_current_positions(db, hire_id)

    # 3. 获取今日买入的股票（T+1 规则）
    today_bought = await _get_today_bought_symbols(db, hire_id, today)

    # 4. 逐个过滤信号
    for sig in candidate_signals:
        symbol = sig.get("symbol", "")
        action = sig.get("action", "").lower()
        quantity = sig.get("quantity", 0)
        price = sig.get("price", 0) or 10.0  # 兜底价格

        # ── T+1 规则：当日买入的股票不可卖出 ──
        if T1_ENABLED and action == "sell" and symbol in today_bought:
            rejected.append({
                **sig,
                "reject_reason": "T+1 规则：当日买入的股票不可卖出（{}）".format(symbol),
            })
            continue

        # ── 最大持仓数检查（仅买入时）──
        if action == "buy":
            current_count = len(positions)
            # 新买入的不算重复计数
            if symbol not in positions:
                if current_count >= MAX_POSITION_COUNT:
                    rejected.append({
                        **sig,
                        "reject_reason": "持仓数已达上限 {} 只".format(MAX_POSITION_COUNT),
                    })
                    continue

        # ── 单票仓位上限检查（仅买入时）──
        if action == "buy":
            estimated_value = quantity * price
            if capital > 0 and (estimated_value / capital) > MAX_POSITION_PCT:
                rejected.append({
                    **sig,
                    "reject_reason": "单票仓位 {}% 超过上限 30%".format(
                        round(estimated_value / capital * 100, 1)
                    ),
                })
                continue

        # ── 卖出持仓检查 ──
        if action == "sell":
            pos = positions.get(symbol)
            if not pos:
                rejected.append({
                    **sig,
                    "reject_reason": "未持有 {}，无法卖出".format(symbol),
                })
                continue
            if quantity > pos.get("quantity", 0):
                rejected.append({
                    **sig,
                    "reject_reason": "卖出数量 {} 超过持仓 {}（{}）".format(
                        quantity, pos.get("quantity", 0), symbol
                    ),
                })
                continue

        passed.append(sig)

    return passed, rejected


async def _check_daily_loss_circuit(
    db: AsyncSession, hire_id: int, today: date
) -> bool:
    """检查是否触发单日亏损熔断"""
    try:
        result = await db.execute(
            select(
                func.coalesce(func.sum(AgentPortfolio.unrealized_pnl), 0),
                func.coalesce(func.sum(AgentPortfolio.market_value), 0),
            ).where(
                AgentPortfolio.hire_id == hire_id,
            )
        )
        row = result.one()
        total_pnl = float(row[0])
        total_value = float(row[1])

        if total_value <= 0:
            return False

        loss_pct = abs(total_pnl) / total_value if total_pnl < 0 else 0
        return loss_pct >= DAILY_LOSS_CIRCUIT_PCT
    except Exception:
        return False


async def _get_current_positions(
    db: AsyncSession, hire_id: int
) -> dict[str, dict]:
    """获取当前活跃持仓"""
    try:
        result = await db.execute(
            select(AgentPortfolio).where(
                AgentPortfolio.hire_id == hire_id,
            )
        )
        positions = {}
        for p in result.scalars().all():
            positions[p.symbol] = {
                "symbol": p.symbol,
                "quantity": p.quantity or 0,
                "cost_price": float(p.avg_cost or 0),
            }
        return positions
    except Exception:
        return {}


async def _get_today_bought_symbols(
    db: AsyncSession, hire_id: int, today: date
) -> set[str]:
    """获取今日买入的股票代码集合（T+1 规则）"""
    try:
        result = await db.execute(
            select(AgentSignal.symbol).where(
                and_(
                    AgentSignal.hire_id == hire_id,
                    AgentSignal.action == "buy",
                    func.date(AgentSignal.created_at) == today,
                    AgentSignal.exec_status.in_(["confirmed", "auto_executed"]),
                )
            ).distinct()
        )
        return {row[0] for row in result.fetchall()}
    except Exception:
        return set()
