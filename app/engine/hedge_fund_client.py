"""
hedge_fund_client.py — ai-hedge-fund 调用客户端

封装对 /opt/ai-hedge-fund 的异步调用。
输入: ticker + agents 列表 → 输出: 分析结果
支持超时和 fallback 到 mock 信号。
"""
from __future__ import annotations

import asyncio
import os
import sys
from datetime import date, datetime, timedelta
from typing import Any

from app.core.config import settings


# ai-hedge-fund 项目路径
HEDGE_FUND_PATH = os.environ.get("AI_HEDGE_FUND_PATH", "/opt/ai-hedge-fund")

# 是否启用真实引擎
ENABLED = os.environ.get("AI_HEDGE_FUND_ENABLED", "false").lower() == "true"
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

# 单个 ticker 超时（秒）
TICKER_TIMEOUT = int(os.environ.get("AI_HEDGE_FUND_TICKER_TIMEOUT", "60"))


async def is_available() -> bool:
    """检查 ai-hedge-fund 是否可用"""
    if not ENABLED:
        return False
    if not OPENAI_API_KEY:
        return False
    if not os.path.isdir(HEDGE_FUND_PATH):
        return False
    # 检查关键模块是否可导入
    try:
        sys.path.insert(0, HEDGE_FUND_PATH)
        from src.main import run_hedge_fund  # noqa: F401
        sys.path.pop(0)
        return True
    except Exception:
        if HEDGE_FUND_PATH in sys.path:
            sys.path.pop(0)
        return False


async def analyze(
    tickers: list[str],
    agents: list[str],
    model_name: str = "gpt-4o",
    model_provider: str = "OpenAI",
    timeout: int | None = None,
) -> dict[str, Any]:
    """
    调用 ai-hedge-fund 分析一组股票

    Args:
        tickers: 股票代码列表（如 ['600519', '000858']）
        agents: 分析师列表（如 ['warren_buffett', 'ben_graham']）
        model_name: LLM 模型名
        model_provider: LLM 提供商
        timeout: 超时秒数

    Returns:
        {
            "success": bool,
            "decisions": [...],
            "analyst_signals": {...},
            "error": str | None,
        }
    """
    timeout = timeout or TICKER_TIMEOUT

    if not await is_available():
        return {
            "success": False,
            "decisions": [],
            "analyst_signals": {},
            "error": "ai-hedge-fund 不可用（未启用或 API key 未配置）",
        }

    try:
        sys.path.insert(0, HEDGE_FUND_PATH)

        # 动态导入，避免污染全局
        from dotenv import load_dotenv
        load_dotenv(os.path.join(HEDGE_FUND_PATH, ".env"))

        from src.main import run_hedge_fund

        # 构建 portfolio
        portfolio = {
            "cash": 100000.0,
            "margin_requirement": 0.0,
            "margin_used": 0.0,
            "positions": {
                t: {
                    "long": 0, "short": 0,
                    "long_cost_basis": 0.0, "short_cost_basis": 0.0,
                    "short_margin_used": 0.0,
                }
                for t in tickers
            },
            "realized_gains": {
                t: {"long": 0.0, "short": 0.0} for t in tickers
            },
        }

        end_date = date.today().strftime("%Y-%m-%d")
        start_date = (date.today() - timedelta(days=90)).strftime("%Y-%m-%d")

        # 异步执行（run_hedge_fund 是同步函数，在线程池中运行）
        loop = asyncio.get_running_loop()
        result = await asyncio.wait_for(
            loop.run_in_executor(
                None,
                lambda: run_hedge_fund(
                    tickers=tickers,
                    start_date=start_date,
                    end_date=end_date,
                    portfolio=portfolio,
                    show_reasoning=False,
                    selected_analysts=agents,
                    model_name=model_name,
                    model_provider=model_provider,
                ),
            ),
            timeout=timeout,
        )

        if HEDGE_FUND_PATH in sys.path:
            sys.path.pop(0)

        return {
            "success": True,
            "decisions": result.get("decisions", []) or [],
            "analyst_signals": result.get("analyst_signals", {}),
            "error": None,
        }

    except asyncio.TimeoutError:
        if HEDGE_FUND_PATH in sys.path:
            sys.path.remove(HEDGE_FUND_PATH)
        return {
            "success": False,
            "decisions": [],
            "analyst_signals": {},
            "error": "分析超时（大于 {}s）".format(timeout),
        }
    except Exception as e:
        if HEDGE_FUND_PATH in sys.path:
            sys.path.remove(HEDGE_FUND_PATH)
        return {
            "success": False,
            "decisions": [],
            "analyst_signals": {},
            "error": "{}: {}".format(type(e).__name__, str(e)),
        }


# ── 策略到 agent 映射 ──

# 注意: agent key 必须与 ai-hedge-fund 中 ANALYST_CONFIG 的 key 完全一致
# 参考: /opt/ai-hedge-fund/src/utils/analysts.py
STRATEGY_AGENT_MAP: dict[str, list[str]] = {
    # ── 数据库中的交易员 ID（拼音）──
    "zhenyue": [        # 镇岳 — 价值猎手
        "ben_graham",
        "warren_buffett",
        "charlie_munger",
    ],
    "zhuguang": [       # 逐光 — 成长先锋
        "phil_fisher",
        "peter_lynch",
        "cathie_wood",
        "growth_analyst",
    ],
    "qianji": [         # 千机 — 量化大师
        "technical_analyst",
        "fundamentals_analyst",
    ],
    "nichuan": [        # 逆川 — 逆向猎手
        "sentiment_analyst",
        "news_sentiment_analyst",
        "michael_burry",
        "nassim_taleb",
    ],
    "shouyi": [         # 守一 — 全能管家
        "ben_graham",
        "warren_buffett",
        "charlie_munger",
        "phil_fisher",
        "peter_lynch",
        "cathie_wood",
        "technical_analyst",
        "fundamentals_analyst",
        "valuation_analyst",
        "sentiment_analyst",
        "news_sentiment_analyst",
        "michael_burry",
        "nassim_taleb",
        "bill_ackman",
        "stanley_druckenmiller",
    ],
    # ── 设计文档中的英文策略名（向后兼容）──
    "value_hunter": [
        "ben_graham",
        "warren_buffett",
        "charlie_munger",
    ],
    "growth_pioneer": [
        "phil_fisher",
        "peter_lynch",
        "cathie_wood",
        "growth_analyst",
    ],
    "quant_master": [
        "technical_analyst",
        "fundamentals_analyst",
    ],
    "contrarian_hunter": [
        "sentiment_analyst",
        "news_sentiment_analyst",
        "michael_burry",
        "nassim_taleb",
    ],
    "steward": [
        "ben_graham",
        "warren_buffett",
        "charlie_munger",
        "phil_fisher",
        "peter_lynch",
        "cathie_wood",
        "technical_analyst",
        "fundamentals_analyst",
        "valuation_analyst",
        "sentiment_analyst",
        "news_sentiment_analyst",
        "michael_burry",
        "nassim_taleb",
        "bill_ackman",
        "stanley_druckenmiller",
    ],
}


def get_agents_for_strategy(strategy: str) -> list[str]:
    """根据策略代码获取对应的 ai-hedge-fund agents 列表"""
    return STRATEGY_AGENT_MAP.get(strategy, ["ben_graham", "warren_buffett", "technical_analyst"])


# ── 结果解析 ──

def parse_decision_to_signal(decision: dict, ticker_name_map: dict[str, str]) -> dict | None:
    """
    将 ai-hedge-fund 的 decision 转为 StockAI 的信号格式

    ai-hedge-fund decision 格式:
    {
        "action": "buy" | "sell" | "hold" | "short" | "cover",
        "ticker": "AAPL",
        "quantity": 100,
        "confidence": 0.85,
        "reasoning": "..."
    }
    """
    action = decision.get("action", "").lower()
    ticker = decision.get("ticker", "")

    if action not in ("buy", "sell"):
        return None  # hold/short/cover 暂不处理

    confidence = decision.get("confidence", 0.5)
    if isinstance(confidence, (int, float)):
        confidence_pct = int(confidence * 100) if confidence <= 1 else int(confidence)
    else:
        confidence_pct = 50

    quantity = decision.get("quantity", 100)
    if not isinstance(quantity, int) or quantity <= 0:
        quantity = 100

    reasoning = decision.get("reasoning", "")

    return {
        "symbol": ticker,
        "name": ticker_name_map.get(ticker, ticker),
        "action": action,
        "price": 0.0,
        "quantity": quantity,
        "confidence": min(max(confidence_pct, 10), 100),
        "reasoning": reasoning[:500] if reasoning else "AI 分析生成",
    }
