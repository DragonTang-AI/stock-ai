"""app/agents/prompts.py — 4-Agent Prompt Builders

每个 Agent 只能分析给定候选池，禁止引入池外标的。
所有 LLM 输出严格 JSON，无多余文本。
"""
from __future__ import annotations

import json

from app.agents.state import CandidatePayload

REASON_CODE_VOCAB: tuple[str, ...] = (
    "momentum",
    "breakout",
    "oversold",
    "overbought",
    "undervalued",
    "overvalued",
    "earnings_beat",
    "earnings_miss",
    "high_roe",
    "high_debt",
    "positive_news",
    "negative_news",
    "sector_rotation",
    "stop_loss_hit",
    "take_profit_hit",
)


def _candidate_brief(candidates: list[CandidatePayload]) -> str:
    """将候选股列表序列化为 LLM 可见的摘要表"""
    rows = [
        {
            "symbol": item["symbol"],
            "close": item["close"],
            "composite_score": round(item["composite_score"], 2),
            "momentum": round(item["factor_scores"].get("momentum", 0), 1),
            "volume_activity": round(item["factor_scores"].get("volume_activity", 0), 1),
            "trend": round(item["factor_scores"].get("trend", 0), 1),
        }
        for item in candidates
    ]
    return json.dumps(rows, ensure_ascii=False)


def technical_prompt(candidates: list[CandidatePayload]) -> tuple[str, str]:
    system = (
        "你是A股/港股技术面分析Agent。只分析给定候选池，禁止引入池外标的。"
        "基于动量、量价、趋势因子给每只股票 0-100 的技术面打分。"
        '严格输出JSON：{"scores":{"<symbol>":<int 0-100>}}，不要输出任何多余文本。'
    )
    user = f"候选池：{_candidate_brief(candidates)}"
    return system, user


def fundamental_prompt(candidates: list[CandidatePayload]) -> tuple[str, str]:
    system = (
        "你是基本面分析Agent。只分析给定候选池。"
        "结合估值与质量线索给每只股票 0-100 的基本面打分（数据有限时给保守中性分）。"
        '严格输出JSON：{"scores":{"<symbol>":<int 0-100>}}，不要输出任何多余文本。'
    )
    user = f"候选池：{_candidate_brief(candidates)}"
    return system, user


def sentiment_prompt(candidates: list[CandidatePayload]) -> tuple[str, str]:
    system = (
        "你是舆情分析Agent。只分析给定候选池。"
        "给每只股票 -50 到 50 的情绪分：负值偏空，正值偏多，无信息给0附近。"
        '严格输出JSON：{"scores":{"<symbol>":<int -50..50>}}，不要输出任何多余文本。'
    )
    user = f"候选池：{_candidate_brief(candidates)}"
    return system, user


def committee_prompt(
    candidates: list[CandidatePayload],
    agent_scores: dict[str, dict[str, int]],
) -> tuple[str, str]:
    vocab = ", ".join(REASON_CODE_VOCAB)
    system = (
        "你是投资委员会Agent。综合技术面/基本面/舆情三个子Agent的打分，"
        "对每只股票给出决策。confidence 为 0-100 综合置信分。"
        "action 只能是 BUY/ADD/HOLD/REDUCE/SELL 之一。"
        f"reason_codes 从以下词表选择 1-4 个：{vocab}。"
        "reasoning 为面向用户的中文简述（<=200字）。"
        '严格输出JSON：{"decisions":{"<symbol>":'
        '{"action":"BUY","confidence":<int 0-100>,'
        '"reason_codes":["momentum"],"reasoning":"..."}}}，不要输出多余文本。'
    )
    payload = {
        "candidates": [
            {"symbol": item["symbol"], "close": item["close"]} for item in candidates
        ],
        "agent_scores": agent_scores,
    }
    user = json.dumps(payload, ensure_ascii=False)
    return system, user
