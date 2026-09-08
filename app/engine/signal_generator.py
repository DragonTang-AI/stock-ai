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
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import AgentTrader, UserAgent, AgentSignal, AgentPortfolio
from app.engine import hedge_fund_client, market_data, risk_manager

logger = logging.getLogger(__name__)


# P0-3: 单轮信号落库上限（按置信度取 Top-N），防止信号流噪音堆积
SIGNAL_SAVE_LIMIT = 5


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

    strategy = trader.id or "value_hunter"
    agents = hedge_fund_client.get_agents_for_strategy(strategy)

    # P1: 从 agent_configs 读取 ticker 限制和风控参数
    from app.services.agent_config_service import get_agent_config, DEFAULTS as CONFIG_DEFAULTS
    agent_config = await get_agent_config(db, hire_id)
    ticker_limit = agent_config.analyze_ticker_limit if agent_config and agent_config.analyze_ticker_limit is not None else CONFIG_DEFAULTS.get("analyze_ticker_limit", 10)

    # 3. 动态股票池（P2-03 整改：接腾讯行情接口）
    # 3.1 读取人格偏好与风控过滤参数（agent_configs，回退 hire）
    style = str(getattr(agent_config, "trading_style", None) or getattr(hire, "trading_style", None) or "steady")
    exclude_st = bool(getattr(agent_config, "exclude_st", getattr(hire, "exclude_st", True)))
    min_avg_amount = float(getattr(agent_config, "min_avg_amount", None) or getattr(hire, "min_avg_amount", None) or 0)
    mcap_min = getattr(agent_config, "market_cap_min", None)
    if mcap_min is None:
        mcap_min = getattr(hire, "market_cap_min", None)
    mcap_max = getattr(agent_config, "market_cap_max", None)
    if mcap_max is None:
        mcap_max = getattr(hire, "market_cap_max", None)
    mcap_min = float(mcap_min) if mcap_min is not None else None
    mcap_max = float(mcap_max) if mcap_max is not None else None
    cfg_markets = getattr(agent_config, "markets", None)
    hire_markets = cfg_markets if cfg_markets else (getattr(hire, "markets", None) or [])
    markets: list[str] = []
    for m in (hire_markets if isinstance(hire_markets, (list, dict)) else []):
        if isinstance(m, dict):
            m = m.get("name") or m.get("market") or ""
        markets.append("HK" if "港" in str(m) else "A")
    if not markets:
        markets = ["A", "HK"]

    # 3.2 拉取动态候选（A 股腾讯排行，港股腾讯行情池），失败 fallback 静态池
    a_candidates: list[dict[str, Any]] = []
    h_candidates: list[dict[str, str]] = []
    pool_source = "static"
    try:
        if "A" in markets:
            a_candidates = await market_data.fetch_tencent_rank_quotes(
                count=max(ticker_limit * 4, 40)
            )
        if "HK" in markets:
            try:
                from app.integrations.market_data.tencent import fetch_hk_ranking
                hk_quotes = await fetch_hk_ranking(limit=max(ticker_limit * 2, 20))
                h_candidates = [{"symbol": q.symbol, "name": q.name} for q in hk_quotes if getattr(q, "symbol", None)]
            except Exception:
                h_candidates = []
            if not h_candidates:
                h_candidates = list(market_data.HK_STOCK_POOL)
        pool_source = "dynamic" if (a_candidates or h_candidates) else "static"
    except Exception:
        logger.exception("腾讯动态池获取异常")

    # 3.3 A 股：过滤 + 人格风格排序（trading_style 参与选股）
    a_filtered: list[dict[str, str]] = []
    for q in a_candidates:
        name = str(q.get("name", ""))
        if exclude_st and ("ST" in name.upper() or "退" in name):
            continue
        if min_avg_amount > 0 and float(q.get("amount") or 0) < min_avg_amount:
            continue
        if mcap_min is not None and float(q.get("market_cap") or 0) < mcap_min:
            continue
        if mcap_max is not None and float(q.get("market_cap") or 0) > mcap_max:
            continue
        a_filtered.append({"symbol": str(q["symbol"]), "name": name})
    a_filtered = _rank_by_style(a_candidates, a_filtered, style)
    if not a_filtered and "A" in markets:
        a_filtered = [s for s in market_data.HOT_A_STOCKS if not (exclude_st and ("ST" in s["name"].upper() or "退" in s["name"]))]

    # 3.4 限制抽样：人格筛选后从候选中随机抽样，避免固定取前5只
    sample_n = min(5, max(1, ticker_limit))
    tickers: list[str] = []
    ticker_map: dict[str, str] = {}
    if "HK" in markets and h_candidates:
        hk_n = min(len(h_candidates), max(1, sample_n // 3))
        hk_pick = random.sample(h_candidates, hk_n)
        a_n = min(len(a_filtered), sample_n - hk_n)
        a_pick = random.sample(a_filtered, a_n) if a_n > 0 else []
        for s in a_pick + hk_pick:
            tickers.append(s["symbol"])
            ticker_map[s["symbol"]] = s["name"]
    elif a_filtered:
        a_n = min(len(a_filtered), sample_n)
        for s in random.sample(a_filtered, a_n):
            tickers.append(s["symbol"])
            ticker_map[s["symbol"]] = s["name"]

    # P2-04b: 强制并入当前持仓，确保大师组合能对持仓标的做加/减仓决策
    # （候选池原本只取行情排行 Top N，持仓股未必在候选内，持仓决策形同虚设）
    try:
        pos_rows = (
            await db.execute(
                select(AgentPortfolio.symbol, AgentPortfolio.symbol_name).where(
                    AgentPortfolio.hire_id == hire_id, AgentPortfolio.quantity > 0
                )
            )
        ).all()
        for _sym, _sname in pos_rows:
            if _sym and _sym not in tickers:
                tickers.append(_sym)
                ticker_map.setdefault(_sym, _sname or _sym)
        if pos_rows:
            logger.info("持仓并入候选池 +%d 只: %s", len(pos_rows), tickers)
    except Exception as _e:  # noqa: BLE001
        logger.warning("持仓并入候选池失败: %s", _e)

    if not tickers:
        return {"signals": [], "source": "mock", "rejected_count": 0, "error": "动态池为空，无候选股票"}

    # P1: 风控总资金（config 已在前面获取）
    total_capital = (
        float(agent_config.allocated_capital)
        if agent_config and agent_config.allocated_capital
        else float(hire.allocated_capital) if hire.allocated_capital
        else CONFIG_DEFAULTS["allocated_capital"]
    )

    # 4. 判断使用真实引擎还是 mock
    use_real = force_real or await hedge_fund_client.is_available()

    logger.info("信号生成 use_real=%s tickers=%s", use_real, tickers)
    if use_real:
        logger.info("使用 ai-hedge-fund 真实引擎，策略=%s agents=%s", strategy, agents)
        return await _generate_real_signals(
            db, hire_id, user_id, trader.id, tickers, agents, ticker_map, total_capital, agent_config=agent_config
        )
    else:
        logger.info("使用 mock 模拟信号（演示模式），策略=%s", strategy)
        return await _generate_mock_signals(
            db, hire_id, user_id, trader.id, tickers, ticker_map, total_capital, agent_config=agent_config
        )


def _rank_by_style(
    candidates: list[dict[str, Any]],
    filtered: list[dict[str, str]],
    style: str,
) -> list[dict[str, str]]:
    """
    按交易人格（trading_style）对动态候选排序：
    - aggressive  激进：动量优先（涨幅/换手率）
    - value       价值：低 PE（剔除亏损）优先
    - steady      稳健：大盘蓝筹（市值大、波动温和）优先
    - growth      成长：中高涨幅 + 成交活跃
    - balanced    均衡：维持腾讯默认成交额排序
    只对 filtered 中的股票排序，返回排好序的 symbol/name 列表。
    """
    if not filtered:
        return filtered
    q_by_symbol = {q.get("symbol"): q for q in candidates}

    def getf(sym: str, key: str, default: float = 0.0) -> float:
        try:
            return float((q_by_symbol.get(sym) or {}).get(key, default) or default)
        except (TypeError, ValueError):
            return default

    style = (style or "balanced").lower()
    if style == "aggressive":
        filtered = sorted(filtered, key=lambda s: getf(s["symbol"], "change_pct"), reverse=True)
    elif style == "value":
        def pe_key(s):
            pe = getf(s["symbol"], "pe_ttm")
            return (1, pe) if pe > 0 else (2, 999999.0)   # 正 PE 优先，其次绝对值小
        filtered = sorted(filtered, key=pe_key)
    elif style == "steady":
        filtered = sorted(filtered, key=lambda s: getf(s["symbol"], "market_cap"), reverse=True)
    elif style == "growth":
        filtered = sorted(filtered, key=lambda s: (getf(s["symbol"], "change_pct", -10) * 0.6 + getf(s["symbol"], "turnover_rate") * 0.4), reverse=True)
    # balanced / 其它：保持腾讯成交额排序
    return filtered


def _is_hk_symbol(symbol: str) -> bool:
    """判断是否为港股 symbol"""
    return symbol.upper().endswith(".HK")


def _round_lot_quantity(action: str, qty: int, symbol: str = "") -> int:
    """交易单位取整：A股100股/手，港股按lot_size计算。买入向上取整，卖出向下取整，最少1手。"""
    qty = int(qty or 100)

    # 港股按实际每手股数取整
    if symbol.upper().endswith(".HK"):
        try:
            from app.services.hk_lot_size import get_lot_size
            code = symbol.replace(".HK", "").replace(".hk", "")
            lot = get_lot_size(code) or 100
        except Exception:
            lot = 100

        if action == "sell":
            return max(lot, (qty // lot) * lot)
        return max(lot, ((qty + lot - 1) // lot) * lot)

    # A 股：100 股/手
    if action == "sell":
        return max(100, (qty // 100) * 100)
    return max(100, ((qty + 99) // 100) * 100)


async def _generate_real_signals(
    db: AsyncSession,
    hire_id: int,
    user_id: int,
    trader_id: str,
    tickers: list[str],
    agents: list[str],
    ticker_map: dict[str, str],
    total_capital: float = 100000,
    agent_config=None,
) -> dict[str, Any]:
    """使用 ai-hedge-fund 真实引擎生成信号"""
    errors = []

    try:
        # P2-04: 读取真实持仓，注入分析链路 → 大师组合基于持仓决策加/减仓
        from app.engine.risk_manager import _get_current_positions
        positions_raw = await _get_current_positions(db, hire_id)
        positions: dict[str, dict[str, Any]] = {}
        held_value = 0.0
        for sym, p in positions_raw.items():
            qty = int(p.get("quantity") or 0)
            cost = float(p.get("cost_price") or 0)
            positions[sym] = {
                "long": qty,
                "short": 0,
                "long_cost_basis": cost,
                "short_cost_basis": 0.0,
                "short_margin_used": 0.0,
            }
            held_value += qty * cost
        portfolio_override = {
            "cash": max(0.0, total_capital - held_value),
            "equity": total_capital,
            "positions": positions,
        }
        logger.info("P2-04 持仓注入 hire=%s positions=%d cash=%.2f equity=%.2f", hire_id, len(positions), portfolio_override["cash"], total_capital)

        # 调用 ai-hedge-fund 分析
        result = await hedge_fund_client.analyze(
            tickers=tickers,
            agents=agents,
            portfolio_override=portfolio_override,
        )

        if not result["success"]:
            # 真实引擎失败，fallback 到 mock
            logger.warning("ai-hedge-fund 分析失败: %s，切换到 mock", result.get("error"))
            return await _generate_mock_signals(db, hire_id, user_id, trader_id, tickers, ticker_map, total_capital, agent_config=agent_config)

        decisions = result.get("decisions", {})
        logger.info("DEBUG decisions type=%s len=%s value=%s", type(decisions).__name__, len(decisions) if hasattr(decisions, "__len__") else "N/A", str(decisions)[:500])
        if not decisions:
            # P0-3c: 引擎理性无决策（震荡/观望）→ 返回空，禁止 mock 顶替，保证信号流真实
            logger.info("ai-hedge-fund 无交易决策，返回空信号（真实观望）")
            return {"signals": [], "source": "ai_hedge_fund", "rejected_count": 0, "error": "engine_no_decisions"}

        # 解析 decisions → 信号
        # decisions 格式：{"ticker": {"action": "buy", "quantity": 100, ...}, ...}
        candidate_signals = []
        if isinstance(decisions, dict):
            for ticker, d in decisions.items():
                if isinstance(d, dict):
                    d["ticker"] = ticker  # 注入 ticker 字段供解析
                    sig = hedge_fund_client.parse_decision_to_signal(d, ticker_map)
                    logger.info("DEBUG ticker=%s action=%s sig=%s", ticker, d.get("action"), sig)
                    if sig:
                        candidate_signals.append(sig)
        else:
            for d in decisions:
                sig = hedge_fund_client.parse_decision_to_signal(d, ticker_map)
                if sig:
                    candidate_signals.append(sig)

        logger.info("DEBUG candidate_signals count=%s", len(candidate_signals))
        if not candidate_signals:
            # P0-3c: 引擎决策解析后无可交易信号（观望/hold/动作非法）→ 返回空，禁止 mock 顶替
            logger.info("ai-hedge-fund 决策无可解析信号，返回空（真实观望）")
            return {"signals": [], "source": "ai_hedge_fund", "rejected_count": 0, "error": "no_parseable_decision"}

        # 补充实时价格
        prices = await market_data.get_batch_prices([s["symbol"] for s in candidate_signals])
        for sig in candidate_signals:
            if sig["symbol"] in prices:
                sig["price"] = prices[sig["symbol"]]["price"]

        # 风控过滤（P1: total_capital + config 从 agent_configs 读取）
        passed, rejected = await risk_manager.check_risk(db, hire_id, candidate_signals, total_capital=total_capital, config=agent_config)

        # 兜底：真实引擎所有信号被拒且存在"空仓卖出" → 回退 mock 买信号
        # 典型场景：Agent 持仓为空且引擎看空只出卖出信号，sell 被风控的"未持有"拦截
        if not passed and rejected:
            no_pos_sells = [r for r in rejected if "未持有" in r.get("reject_reason", "")]
            if no_pos_sells:
                logger.info(
                    "真实引擎 %d 条信号全部被拒（含 %d 条空仓卖出），返回空（真实空仓观望）",
                    len(rejected), len(no_pos_sells),
                )
                return {"signals": [], "source": "ai_hedge_fund", "rejected_count": len(rejected), "error": "risk_rejected"}

        # 写入信号
        today = date.today()
        saved_orm = []
        # P0-3 信号噪音治理：每轮仅落库高置信度前 SIGNAL_SAVE_LIMIT 条，避免 pending 堆积过期刷屏
        passed = sorted(passed, key=lambda s: float(s.get("confidence", 0) or 0), reverse=True)[:SIGNAL_SAVE_LIMIT]
        for sig in passed:
            db_signal = AgentSignal(
                hire_id=hire_id,
                trader_id=trader_id,
                user_id=user_id,
                symbol=sig["symbol"],
                symbol_name=sig.get("name", sig["symbol"]),
                market="HK" if _is_hk_symbol(sig["symbol"]) else "A",
                action=sig["action"],
                price=sig["price"],
                quantity=_round_lot_quantity(sig["action"], sig["quantity"], sig["symbol"]),
                confidence=sig["confidence"],
                reasoning=sig.get("reasoning", ""),
                exec_status="pending",  # advisory 默认 pending；full_managed 在端点层自动执行
                signal_source="ai_hedge_fund",
                created_at=datetime.now(timezone.utc),
            )
            db.add(db_signal)
            saved_orm.append(db_signal)

        await db.commit()

        saved_signals = [
            {
                "id": s.id or 0,
                "hire_id": hire_id,
                "trader_id": trader_id,
                "symbol": s.symbol,
                "name": s.symbol_name,
                "market": s.market,
                "action": s.action,
                "price": float(s.price or 0),
                "quantity": s.quantity or 0,
                "confidence": s.confidence or 0,
                "reasoning": s.reasoning or "",
                "exec_status": s.exec_status,
                "created_at": s.created_at,
                "updated_at": s.updated_at,
            }
            for s in saved_orm
        ]

        return {
            "signals": saved_signals,
            "source": "ai_hedge_fund",
            "rejected_count": len(rejected),
            "error": None,
        }

    except Exception as e:
        logger.exception("真实引擎信号生成异常")
        return await _generate_mock_signals(db, hire_id, user_id, trader_id, tickers, ticker_map, total_capital, agent_config=agent_config)


async def _generate_mock_signals(
    db: AsyncSession,
    hire_id: int,
    user_id: int,
    trader_id: str,
    tickers: list[str],
    ticker_map: dict[str, str],
    total_capital: float = 100000,
    agent_config=None,
) -> dict[str, Any]:
    """使用模拟信号（Phase 2 兼容，P2-11: 标记为演示模式，禁止 full_managed 自动执行）"""
    count = random.randint(2, 5)
    num_stocks = min(count, len(tickers))
    if num_stocks == 0:
        return {"signals": [], "source": "mock", "rejected_count": 0, "error": None}

    # 检测持仓：空仓时仅生成 buy 信号，避免 sell 被风控"未持有"拦截
    from app.engine.risk_manager import _get_current_positions
    positions = await _get_current_positions(db, hire_id)
    allow_sell = len(positions) > 0

    selected = random.sample(tickers, num_stocks)

    candidate_signals = []
    for symbol in selected:
        action = random.choice(["buy", "sell"]) if allow_sell else "buy"
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

    # 风控过滤（P1: total_capital + config 从 agent_configs 读取）
    passed, rejected = await risk_manager.check_risk(db, hire_id, candidate_signals, total_capital=total_capital, config=agent_config)

    # 写入信号
    saved_orm = []
    # P0-3 信号噪音治理：每轮仅落库高置信度前 SIGNAL_SAVE_LIMIT 条，避免 pending 堆积过期刷屏
    passed = sorted(passed, key=lambda s: float(s.get("confidence", 0) or 0), reverse=True)[:SIGNAL_SAVE_LIMIT]
    for sig in passed:
        # P2-11: mock 演示模式信号强制 pending，禁止 full_managed 自动执行
        db_signal = AgentSignal(
            hire_id=hire_id,
            trader_id=trader_id,
            user_id=user_id,
            symbol=sig["symbol"],
            symbol_name=sig.get("name", sig["symbol"]),
            market="HK" if _is_hk_symbol(sig["symbol"]) else "A",
            action=sig["action"],
            price=sig["price"],
            quantity=sig["quantity"],
            confidence=sig["confidence"],
            reasoning=sig.get("reasoning", ""),
            exec_status="pending",  # mock 演示模式始终 pending；advisory 前端可确认，full_managed 由调度层拦截自动执行
            signal_source="mock",
            created_at=datetime.now(timezone.utc),
        )
        db.add(db_signal)
        saved_orm.append(db_signal)

    await db.commit()

    saved_signals = [
        {
            "id": s.id or 0,
            "hire_id": hire_id,
            "trader_id": trader_id,
            "symbol": s.symbol,
            "name": s.symbol_name,
            "action": s.action,
            "price": float(s.price or 0),
            "quantity": s.quantity or 0,
            "confidence": s.confidence or 0,
            "reasoning": s.reasoning or "",
            "exec_status": s.exec_status,
            "created_at": s.created_at,
            "updated_at": s.updated_at,
        }
        for s in saved_orm
    ]

    return {
        "signals": saved_signals,
        "source": "mock",
        "demo_mode": True,
        "rejected_count": len(rejected),
        "error": None,
    }
