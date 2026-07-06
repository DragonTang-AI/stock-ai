"""app/agents/state.py — LangGraph 管线状态定义"""
from __future__ import annotations

from typing import TypedDict


class CandidatePayload(TypedDict):
    """与 PrescreenCandidate 对齐的 payload（字典形式供 LangGraph 使用）"""
    rank: int
    market: str
    symbol: str
    symbol_name: str | None
    trade_date: str
    close: str
    composite_score: float
    factor_scores: dict[str, float]


class SymbolAgentScores(TypedDict):
    """三维度 Agent 评分"""
    technical: int
    fundamental: int
    sentiment: int


class CommitteeGraphState(TypedDict):
    """LangGraph 全局状态"""
    market: str
    trade_date: str
    candidates: list[CandidatePayload]
    top_n: int
    agent_scores: dict[str, SymbolAgentScores]
    agent_modes: dict[str, str]  # "llm" | "fallback"
    signals: list[dict]
