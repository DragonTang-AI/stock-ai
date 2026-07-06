"""app/agents/orchestrator.py — LangGraph 4-Agent 选股委员会管线

流程：粗筛候选股 → Technical Agent → Fundamental Agent → Sentiment Agent → 投委会
- AI 模式：LLM 推理打分（Anthropic/DeepSeek，按 config 路由）
- Fallback 模式：确定性因子派生评分（LLM 不可用时自动降级）
- Signal 协议：输出严格对齐 app/schemas/signals.py
"""
from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import UTC, date, datetime
from typing import Any
from uuid import uuid4

from langgraph.graph import END, START, StateGraph

from app.agents.llm_client import LLMClient
from app.agents.prompts import (
    REASON_CODE_VOCAB,
    committee_prompt,
    fundamental_prompt,
    sentiment_prompt,
    technical_prompt,
)
from app.agents.state import (
    CandidatePayload,
    CommitteeGraphState,
    SymbolAgentScores,
)
from app.agents.transports import build_router_transport
from app.schemas.prescreen import PrescreenCandidate
from app.schemas.signals import (
    ActionType,
    AgentScores,
    CurrencyType,
    MarketType,
    ReasonCode,
    Signal,
    SignalStatus,
)
from app.core.config import settings

logger = logging.getLogger(__name__)

_TOP_CONFIDENCE_THRESHOLD = 70
_HOLD_CONFIDENCE_THRESHOLD = 50
_DEFAULT_TOP_N = 5
_VALID_ACTIONS = {a.value for a in ActionType}
_REASON_CODE_SET = set(REASON_CODE_VOCAB)  # 字符串集合，供 orchestrator 使用

# ReasonCode 字符串 → enum 映射
_REASON_CODE_MAP: dict[str, ReasonCode] = {
    rc.value: rc for rc in ReasonCode
}


def _clamp_int(value: float, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, int(round(value))))


def _candidate_to_payload(c: PrescreenCandidate) -> CandidatePayload:
    return CandidatePayload(
        rank=c.rank,
        market=c.market,
        symbol=c.symbol,
        symbol_name=c.symbol_name,
        trade_date=c.trade_date,
        close=c.close,
        composite_score=c.composite_score,
        factor_scores={
            "momentum": c.factor_scores.momentum,
            "volume_activity": c.factor_scores.volume_activity,
            "trend": c.factor_scores.trend,
        },
    )


def _empty_scores() -> SymbolAgentScores:
    return SymbolAgentScores(technical=0, fundamental=0, sentiment=0)


# ── 确定性 Fallback 评分器 ──────────────────────────────────────────────


def _fallback_technical(candidate: CandidatePayload) -> int:
    momentum = candidate["factor_scores"]["momentum"]
    trend = candidate["factor_scores"]["trend"]
    return _clamp_int((momentum * 0.6) + (trend * 0.4), 0, 100)


def _fallback_fundamental(candidate: CandidatePayload) -> int:
    composite = candidate["composite_score"]
    volume_activity = candidate["factor_scores"]["volume_activity"]
    return _clamp_int((composite * 0.7) + (volume_activity * 0.3), 0, 100)


def _fallback_sentiment(candidate: CandidatePayload) -> int:
    volume_activity = candidate["factor_scores"]["volume_activity"]
    return _clamp_int((volume_activity - 50.0) * 0.8, -50, 50)


def _parse_score_map(payload: dict, *, minimum: int, maximum: int) -> dict[str, int]:
    scores = payload.get("scores")
    if not isinstance(scores, dict):
        raise ValueError("missing_scores_object")
    parsed: dict[str, int] = {}
    for symbol, value in scores.items():
        parsed[str(symbol)] = _clamp_int(float(value), minimum, maximum)
    return parsed


def _merge_field(
    scores: dict[str, SymbolAgentScores],
    symbol: str,
    field: str,
    value: int,
) -> None:
    current = scores.get(symbol, _empty_scores())
    current = dict(current)  # type: ignore[assignment]
    current[field] = value  # type: ignore[literal-required]
    scores[symbol] = current  # type: ignore[assignment]


# ── Analyst Node Factory ───────────────────────────────────────────────


def _make_analyst_node(
    *,
    name: str,
    field: str,
    prompt_builder: Callable[[list[CandidatePayload]], tuple[str, str]],
    fallback: Callable[[CandidatePayload], int],
    minimum: int,
    maximum: int,
    client: LLMClient,
) -> Callable[[CommitteeGraphState], dict[str, Any]]:
    def node(state: CommitteeGraphState) -> dict[str, Any]:
        scores: dict[str, SymbolAgentScores] = {
            symbol: dict(value)  # type: ignore[misc]
            for symbol, value in state.get("agent_scores", {}).items()
        }
        modes = dict(state.get("agent_modes", {}))
        candidates = state["candidates"]

        llm_scores: dict[str, int] = {}
        mode = "fallback"
        if client.available():
            try:
                system_prompt, user_prompt = prompt_builder(candidates)
                payload = client.complete_json(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                )
                llm_scores = _parse_score_map(payload, minimum=minimum, maximum=maximum)
                mode = "llm"
            except Exception as exc:  # noqa: BLE001
                logger.warning("%s agent fell back to deterministic: %s", name, exc)
                mode = "fallback"

        for candidate in candidates:
            symbol = candidate["symbol"]
            if mode == "llm" and symbol in llm_scores:
                value = llm_scores[symbol]
            else:
                value = fallback(candidate)
            _merge_field(scores, symbol, field, value)

        modes[name] = mode
        return {"agent_scores": scores, "agent_modes": modes}

    return node


# ── Committee Synthesis ────────────────────────────────────────────────


def _confidence_from_scores(scores: SymbolAgentScores) -> int:
    sentiment_normalized = (scores["sentiment"] + 50) / 100 * 100
    raw = scores["technical"] * 0.4 + scores["fundamental"] * 0.4 + sentiment_normalized * 0.2
    return _clamp_int(raw, 0, 100)


def _action_from_confidence(confidence: int) -> ActionType:
    if confidence >= _TOP_CONFIDENCE_THRESHOLD:
        return ActionType.BUY
    if confidence >= _HOLD_CONFIDENCE_THRESHOLD:
        return ActionType.HOLD
    return ActionType.REDUCE


def _fallback_reason_codes(candidate: CandidatePayload, scores: SymbolAgentScores) -> list[str]:
    codes: list[str] = []
    if candidate["factor_scores"]["momentum"] >= 60:
        codes.append("momentum")
    if candidate["factor_scores"]["trend"] >= 60:
        codes.append("breakout")
    if scores["fundamental"] >= 70:
        codes.append("high_roe")
    if scores["sentiment"] >= 10:
        codes.append("positive_news")
    if not codes:
        codes.append("sector_rotation")
    return codes


def _sanitize_reason_codes(raw: Any) -> list[str]:
    if not isinstance(raw, list):
        return []
    cleaned: list[str] = []
    for item in raw:
        code = str(item).strip().lower()
        if code in _REASON_CODE_SET and code not in cleaned:
            cleaned.append(code)
        if len(cleaned) >= 4:
            break
    return cleaned


def _string_to_reason_codes(raw: Any) -> list[ReasonCode]:
    """将字符串 reason_codes 转为 ReasonCode 枚举列表"""
    str_codes = _sanitize_reason_codes(raw)
    result: list[ReasonCode] = []
    for code in str_codes:
        rc = _REASON_CODE_MAP.get(code)
        if rc is not None:
            result.append(rc)
    return result


def _build_signal(
    candidate: CandidatePayload,
    scores: SymbolAgentScores,
    *,
    market: str,
    trade_date: str,
    action: ActionType,
    confidence: int,
    reason_codes: list[str],
    reasoning: str,
) -> Signal:
    """构建 Signal（对齐 prod signals.py schema）"""
    close_price = float(candidate["close"]) if candidate["close"] else 0.0
    signal_market = MarketType(market)
    currency = CurrencyType.CNY if signal_market == MarketType.A else CurrencyType.HKD
    is_buy = action in {ActionType.BUY, ActionType.ADD}

    return Signal(
        signal_id=str(uuid4()),
        symbol=candidate["symbol"],
        symbol_name=candidate.get("symbol_name"),
        market=signal_market,
        action=action,
        confidence=confidence,
        currency=currency,
        target_price=round(close_price * 1.08, 4) if is_buy and close_price > 0 else None,
        stop_loss=round(close_price * 0.92, 4) if close_price > 0 else None,
        take_profit=round(close_price * 1.12, 4) if is_buy and close_price > 0 else None,
        reason_codes=_string_to_reason_codes(reason_codes),
        reasoning=reasoning[:500],
        source="committee_agent",
        agent_scores=AgentScores(
            technical=scores["technical"],
            fundamental=scores["fundamental"],
            sentiment=scores["sentiment"],
        ),
        created_at=datetime.now(UTC),
        status=SignalStatus.PENDING,
    )


def _make_committee_node(client: LLMClient) -> Callable[[CommitteeGraphState], dict[str, Any]]:
    def node(state: CommitteeGraphState) -> dict[str, Any]:
        scores_map = state.get("agent_scores", {})
        candidates = state["candidates"]

        scored: list[tuple[int, CandidatePayload, SymbolAgentScores]] = []
        for candidate in candidates:
            scores = scores_map.get(candidate["symbol"])
            if scores is None:
                continue
            scored.append((_confidence_from_scores(scores), candidate, scores))
        scored.sort(key=lambda item: (-item[0], item[1]["symbol"]))
        top_n = max(1, min(state.get("top_n", _DEFAULT_TOP_N), _DEFAULT_TOP_N))
        selected = scored[:top_n]

        llm_decisions: dict[str, dict] = {}
        if client.available() and selected:
            try:
                agent_scores_payload = {
                    candidate["symbol"]: dict(scores) for _, candidate, scores in selected
                }
                system_prompt, user_prompt = committee_prompt(
                    [candidate for _, candidate, _ in selected],
                    agent_scores_payload,  # type: ignore[arg-type]
                )
                payload = client.complete_json(system_prompt=system_prompt, user_prompt=user_prompt)
                decisions = payload.get("decisions")
                if isinstance(decisions, dict):
                    llm_decisions = {str(k): v for k, v in decisions.items() if isinstance(v, dict)}
            except Exception as exc:  # noqa: BLE001
                logger.warning("committee agent fell back to deterministic: %s", exc)

        signals: list[dict] = []
        for fallback_confidence, candidate, scores in selected:
            symbol = candidate["symbol"]
            decision = llm_decisions.get(symbol)

            action = _action_from_confidence(fallback_confidence)
            confidence = fallback_confidence
            reason_codes = _fallback_reason_codes(candidate, scores)
            reasoning = (
                f"技术面 {scores['technical']} / 基本面 {scores['fundamental']} / "
                f"舆情 {scores['sentiment']}；综合置信 {confidence}。"
            )

            if decision is not None:
                action_raw = str(decision.get("action", "")).upper()
                if action_raw in _VALID_ACTIONS:
                    action = ActionType(action_raw)
                confidence_raw = decision.get("confidence")
                if isinstance(confidence_raw, (int, float)):
                    confidence = _clamp_int(float(confidence_raw), 0, 100)
                llm_codes = _sanitize_reason_codes(decision.get("reason_codes"))
                if llm_codes:
                    reason_codes = llm_codes
                reasoning_raw = decision.get("reasoning")
                if isinstance(reasoning_raw, str) and reasoning_raw.strip():
                    reasoning = reasoning_raw.strip()[:2000]

            signal = _build_signal(
                candidate,
                scores,
                market=state["market"],
                trade_date=state["trade_date"],
                action=action,
                confidence=confidence,
                reason_codes=reason_codes,
                reasoning=reasoning,
            )
            signals.append(signal.model_dump(mode="json"))

        return {"signals": signals}

    return node


def build_committee_graph(client: LLMClient):
    """构建 LangGraph 有向无环图"""
    graph = StateGraph(CommitteeGraphState)
    graph.add_node(
        "technical",
        _make_analyst_node(
            name="technical",
            field="technical",
            prompt_builder=technical_prompt,
            fallback=_fallback_technical,
            minimum=0,
            maximum=100,
            client=client,
        ),
    )
    graph.add_node(
        "fundamental",
        _make_analyst_node(
            name="fundamental",
            field="fundamental",
            prompt_builder=fundamental_prompt,
            fallback=_fallback_fundamental,
            minimum=0,
            maximum=100,
            client=client,
        ),
    )
    graph.add_node(
        "sentiment",
        _make_analyst_node(
            name="sentiment",
            field="sentiment",
            prompt_builder=sentiment_prompt,
            fallback=_fallback_sentiment,
            minimum=-50,
            maximum=50,
            client=client,
        ),
    )
    graph.add_node("committee", _make_committee_node(client))

    graph.add_edge(START, "technical")
    graph.add_edge("technical", "fundamental")
    graph.add_edge("fundamental", "sentiment")
    graph.add_edge("sentiment", "committee")
    graph.add_edge("committee", END)
    return graph.compile()


def run_committee_graph(
    candidates: list[PrescreenCandidate],
    *,
    market: str,
    trade_date: str,
    top_n: int = _DEFAULT_TOP_N,
) -> list[Signal]:
    """
    执行 4-Agent 选股委员会管线。

    步骤：粗筛候选股 → Technical → Fundamental → Sentiment → 投委会
    输出：Top N Signal（对齐 Signal 协议）

    Args:
        candidates: 粗筛候选股列表（PrescreenCandidate）
        market: 市场代码（A/HK）
        trade_date: 交易日期（YYYY-MM-DD）
        top_n: 输出信号数量上限（默认5）

    Returns:
        Signal 列表（按置信分降序）
    """
    if not candidates:
        return []

    client = LLMClient(
        primary_model=settings.llm_primary_model,
        backup_model=settings.llm_backup_model,
        timeout_seconds=settings.llm_timeout_seconds,
        max_retries=settings.llm_max_retries,
        transport=build_router_transport(),
        enabled=settings.llm_enabled,
    )

    compiled = build_committee_graph(client)
    result = compiled.invoke(
        {
            "market": market,
            "trade_date": trade_date,
            "candidates": [_candidate_to_payload(c) for c in candidates],
            "top_n": top_n,
            "agent_scores": {},
            "agent_modes": {},
            "signals": [],
        }
    )
    return [Signal.model_validate(item) for item in result["signals"]]
