"""
signal_generator.py — 信号生成器

将 Phase 2 的模拟信号生成器升级为真实引擎驱动：
- 获取某个活跃雇佣关系 → 确定该交易员的策略 → 映射到对应的 ai-hedge-fund agents
- 信号生成流程：获取热门A股列表 → 调用 ai-hedge-fund 分析 → 解析结果 → 风控过滤 → 写入 agent_signals 表
- 如果 ai-hedge-fund 不可用，fallback 到模拟信号（保持 Phase 2 功能不变）
"""
from __future__ import annotations

import asyncio
import logging
import random
from datetime import date, datetime
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import AgentTrader, UserAgent, AgentSignal
from app.engine import hedge_fund_client, market_data, risk_manager

logger = logging.getLogger(__name__)


# ── Phase 2 模拟信号股市理由池（兼容现有 fallback）──

MOCK_REASONS_BUY = [
    "MACD 金叉形成，短期动能强劲，建议逢低建仓",
    "PE 处于历史低位，安全边际充足，价值凸显",
    "北向资金持续流入，机构看好后市表现",
    "突破 60 日均线压制，技术形态转好",
    "行业景气度回升，龙头受益确定性高",
    "财报超预期，盈利能力持续改善",
    "底部放量反弹，资金进场迹象明显",
    "政策利好催化，板块轮动机会显现",
]

MOCK_REASONS_SELL = [
    "KDJ 高位死叉，短期回调压力增大，建议减仓",
    "估值已偏离基本面，泡沫风险累积",
    "主力资金持续流出，高位派发迹象明显",
    "跌破关键支撑位，止损纪律触发",
    "行业政策收紧，盈利预期下调",
    "季报不及预期，增速放缓趋势确立",
    "高位缩量震荡，上攻动能衰竭",
]


async def generate_signals(
    db: AsyncSession,
    hire_id: int,
    user_id: int,
    force_real: bool = False,
) -> dict[str, Any]:
    """
    为一个雇佣关系生成交易信号

    Args:
        db: 数据库会话
        hire_id: 雇佣关系 ID
        user_id: 用户 ID
        force_real: 强制使用真实引擎（忽略 fallback）

    Returns:
        {
            "signals": [...],
            "source": "ai_hedge_fund" | "mock",
            "rejected_count": int,
            "error": str | None,
        }
    """
    # 1. 获取雇佣关系和交易员信息
    result = await db.execute(
        select(UserAgent, AgentTrader).join(
            AgentTrader, AgentTrader.id == UserAgent.agent_id
        ).where(
            and_(UserAgent.id == hire_id, UserAgent.user_id == user_id)
        )
    )
    row = result.one_or_none()
    if not row:
        return {"signals": [], "source": "mock", "rejected_count": 0, "error": "雇佣关系不存在"}

    hire, trader = row
    if hire.status != "active":
        return {"signals": [], "source": "mock", "rejected_count": 0, "error": "雇佣关系非活跃状态"}

    # 2. 确定使用的 agents（trader.id 即策略代码，如 value_hunter）
    strategy = trader.id or "value_hunter"
    agents = hedge_fund_client.get_agents_for_strategy(strategy)

    # 3. 获取股票池
    stock_list = await market_data.get_stock_list(db, limit=20)
    tickers = [s["symbol"] for s in stock_list[:10]]  # 最多分析 10 只
    ticker_map = {s["symbol"]: s["name"] for s in stock_list}

    # 4. 判断使用真实引擎还是 mock
    use_real = force_real or await hedge_fund_client.is_available()

    if use_real:
        logger.info("使用 ai-hedge-fund 真实引擎，策略=%s agents=%s", strategy, agents)
        return await _generate_real_signals(
            db, hire_id, user_id, trader.id, tickers, agents, ticker_map
        )
    else:
        logger.info("使用 mock 模拟信号，策略=%s", strategy)
        return await _generate_mock_signals(
            db, hire_id, user_id, trader.id, tickers, ticker_map
        )


async def _generate_real_signals(
    db: AsyncSession,
    hire_id: int,
    user_id: int,
    trader_id: str,
    tickers: list[str],
    agents: list[str],
    ticker_map: dict[str, str],
) -> dict[str, Any]:
    """使用 ai-hedge-fund 真实引擎生成信号"""
    errors = []

    try:
        # 调用 ai-hedge-fund 分析
        result = await hedge_fund_client.analyze(
            tickers=tickers,
            agents=agents,
        )

        if not result["success"]:
            # 真实引擎失败，fallback 到 mock
            logger.warning("ai-hedge-fund 分析失败: %s，切换到 mock", result.get("error"))
            return await _generate_mock_signals(db, hire_id, user_id, trader_id, tickers, ticker_map)

        decisions = result.get("decisions", [])
        if not decisions:
            logger.info("ai-hedge-fund 未产生交易决策，切换 mock")
            return await _generate_mock_signals(db, hire_id, user_id, trader_id, tickers, ticker_map)

        # 解析 decisions → 信号
        candidate_signals = []
        for d in decisions:
            sig = hedge_fund_client.parse_decision_to_signal(d, ticker_map)
            if sig:
                candidate_signals.append(sig)

        if not candidate_signals:
            return await _generate_mock_signals(db, hire_id, user_id, trader_id, tickers, ticker_map)

        # 补充实时价格
        prices = await market_data.get_batch_prices([s["symbol"] for s in candidate_signals])
        for sig in candidate_signals:
            if sig["symbol"] in prices:
                sig["price"] = prices[sig["symbol"]]["price"]

        # 风控过滤
        passed, rejected = await risk_manager.check_risk(db, hire_id, candidate_signals)

        # 写入信号
        today = date.today()
        saved_signals = []
        for sig in passed:
            db_signal = AgentSignal(
                hire_id=hire_id,
                trader_id=trader_id,
                user_id=user_id,
                symbol=sig["symbol"],
                symbol_name=sig.get("name", sig["symbol"]),
                action=sig["action"],
                price=sig["price"],
                quantity=sig["quantity"],
                confidence=sig["confidence"],
                reasoning=sig.get("reasoning", ""),
                exec_status="auto_executed",
                created_at=datetime.now(),
            )
            db.add(db_signal)
            saved_signals.append(sig)

        await db.commit()

        return {
            "signals": saved_signals,
            "source": "ai_hedge_fund",
            "rejected_count": len(rejected),
            "error": None,
        }

    except Exception as e:
        logger.exception("真实引擎信号生成异常")
        return await _generate_mock_signals(db, hire_id, user_id, trader_id, tickers, ticker_map)


async def _generate_mock_signals(
    db: AsyncSession,
    hire_id: int,
    user_id: int,
    trader_id: str,
    tickers: list[str],
    ticker_map: dict[str, str],
) -> dict[str, Any]:
    """使用模拟信号（Phase 2 兼容）"""
    count = random.randint(1, 3)
    num_stocks = min(count, len(tickers))
    if num_stocks == 0:
        return {"signals": [], "source": "mock", "rejected_count": 0, "error": None}

    selected = random.sample(tickers, num_stocks)

    candidate_signals = []
    for symbol in selected:
        action = random.choice(["buy", "sell"])
        base_price = random.uniform(10, 500)
        price = round(base_price, 2)
        quantity = random.choice([100, 200, 300, 500])
        confidence = random.randint(40, 95)

        if action == "buy":
            reasoning = random.choice(MOCK_REASONS_BUY)
        else:
            reasoning = random.choice(MOCK_REASONS_SELL)

        candidate_signals.append({
            "symbol": symbol,
            "name": ticker_map.get(symbol, symbol),
            "action": action,
            "price": price,
            "quantity": quantity,
            "confidence": confidence,
            "reasoning": reasoning,
        })

    # 补充实时价格（mock 模式下也尽量拉取）
    try:
        prices = await market_data.get_batch_prices([s["symbol"] for s in candidate_signals])
        for sig in candidate_signals:
            if sig["symbol"] in prices:
                sig["price"] = prices[sig["symbol"]]["price"]
    except Exception:
        pass

    # 风控过滤
    passed, rejected = await risk_manager.check_risk(db, hire_id, candidate_signals)

    # 写入信号
    saved_signals = []
    for sig in passed:
        db_signal = AgentSignal(
            hire_id=hire_id,
            trader_id=trader_id,
            user_id=user_id,
            symbol=sig["symbol"],
            symbol_name=sig.get("name", sig["symbol"]),
            action=sig["action"],
            price=sig["price"],
            quantity=sig["quantity"],
            confidence=sig["confidence"],
            reasoning=sig.get("reasoning", ""),
            exec_status="auto_executed",
            created_at=datetime.now(),
        )
        db.add(db_signal)
        saved_signals.append(sig)

    await db.commit()

    return {
        "signals": saved_signals,
        "source": "mock",
        "rejected_count": len(rejected),
        "error": None,
    }
