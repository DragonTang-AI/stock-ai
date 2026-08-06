"""
risk_manager.py — 风控规则

在信号生成后、写入 signals 表之前执行风控过滤：
- 单票仓位上限：不超过总资金的 30%
- 单日亏损熔断：当日亏损超过 5% 时暂停该交易员
- T+1 规则：当日买入的股票当日不可卖出
- 最大持仓数：单个交易员最多同时持有 5 只股票
"""
from __future__ import annotations

from datetime import date, datetime, timezone, timedelta
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import AgentPortfolio, AgentSignal, AgentConfig
from app.services.agent_config_service import DEFAULTS as CONFIG_DEFAULTS


def _beijing_today() -> date:
    """P2-15: 显式按北京时间计算"今日"，避免与 PG UTC 边界错位"""
    return (datetime.now(timezone.utc) + timedelta(hours=8)).date()


async def check_risk(
    db: AsyncSession,
    hire_id: int,
    candidate_signals: list[dict],
    total_capital: float | None = None,
    config: AgentConfig | None = None,
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
    capital = total_capital or (
        float(config.allocated_capital)
        if config and config.allocated_capital
        else CONFIG_DEFAULTS["allocated_capital"]
    )
    passed = []
    rejected = []

    today = _beijing_today()

    # P1: 从配置读取风控参数
    max_position_pct = (config.max_position_pct / 100.0) if config and config.max_position_pct else CONFIG_DEFAULTS["max_position_pct"] / 100.0
    loss_stop_pct = (config.loss_stop_pct / 100.0) if config and config.loss_stop_pct else CONFIG_DEFAULTS["loss_stop_pct"] / 100.0
    max_position_count = config.max_position_count if config and config.max_position_count else CONFIG_DEFAULTS["max_position_count"]
    t1_enabled = config.t1_enabled if config is not None else CONFIG_DEFAULTS["t1_enabled"]

    # 1. 检查单日亏损熔断
    circuit_broken = await _check_daily_loss_circuit(db, hire_id, today, loss_stop_pct)
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
        if t1_enabled and action == "sell" and symbol in today_bought:
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
                if current_count >= max_position_count:
                    rejected.append({
                        **sig,
                        "reject_reason": "持仓数已达上限 {} 只".format(max_position_count),
                    })
                    continue

        # ── 单票仓位上限检查（仅买入时）──
        if action == "buy":
            estimated_value = quantity * price
            if capital > 0 and (estimated_value / capital) > max_position_pct:
                rejected.append({
                    **sig,
                    "reject_reason": "单票仓位 {}% 超过上限 {:.0f}%".format(
                        round(estimated_value / capital * 100, 1),
                        max_position_pct * 100,
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
    db: AsyncSession, hire_id: int, today: date, loss_stop_pct: float = 0.05
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
        return loss_pct >= loss_stop_pct
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
        # P2-15: 用北京时间对应的 UTC 时间范围过滤，避免 func.date 与 UTC 边界错位
        start_utc = datetime(today.year, today.month, today.day, tzinfo=timezone.utc) - timedelta(hours=8)
        end_utc = start_utc + timedelta(days=1)
        result = await db.execute(
            select(AgentSignal.symbol).where(
                and_(
                    AgentSignal.hire_id == hire_id,
                    AgentSignal.action == "buy",
                    AgentSignal.created_at >= start_utc,
                    AgentSignal.created_at < end_utc,
                    AgentSignal.exec_status.in_(["confirmed", "auto_executed"]),
                )
            ).distinct()
        )
        return {row[0] for row in result.fetchall()}
    except Exception:
        return set()
