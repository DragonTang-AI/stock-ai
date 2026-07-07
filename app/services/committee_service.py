"""app/services/committee_service.py — 4-Agent 委员会服务层"""
import logging
from datetime import date

from app.agents.orchestrator import run_committee_graph
from app.schemas.committee import CommitteeRunResponse
from app.schemas.signals import Signal
from app.services.prescreen_service import get_prescreen_candidates

logger = logging.getLogger(__name__)

_DEFAULT_CANDIDATE_LIMIT = 50
_DEFAULT_SIGNAL_LIMIT = 5


async def run_committee_analysis(
    *,
    market: str,
    trade_date: date,
    candidate_limit: int = _DEFAULT_CANDIDATE_LIMIT,
    signal_limit: int = _DEFAULT_SIGNAL_LIMIT,
) -> CommitteeRunResponse:
    """
    执行完整 4-Agent 选股委员会流程。

    流程：Prescreen 粗筛（50只）→ 3个分析师Agent → 投委会Agent → Signal列表
    Fallback：任何 LLM 不可用时自动降级为确定性因子评分

    Args:
        market: 市场代码（A/HK）
        trade_date: 交易日期
        candidate_limit: 粗筛参与上限（默认50）
        signal_limit: 输出信号上限（默认5）

    Returns:
        CommitteeRunResponse（包含 Signal 列表）
    """
    trade_date_str = trade_date.isoformat()

    # Step 1: Prescreen 粗筛
    prescreen = await get_prescreen_candidates(
        market=market,
        trade_date=trade_date,
        limit=candidate_limit,
    )

    effective_signal_limit = max(1, min(signal_limit, 5))

    # Step 2: 4-Agent 管线（PrescreenCandidate → Signal）
    signals: list[Signal] = run_committee_graph(
        prescreen.candidates,
        market=market,
        trade_date=trade_date_str,
        top_n=effective_signal_limit,
    )

    return CommitteeRunResponse(
        market=market,
        trade_date=trade_date_str,
        candidate_pool_size=prescreen.pool_size,
        candidates_evaluated=len(prescreen.candidates),
        signal_limit=effective_signal_limit,
        pipeline="langgraph_committee_v1",
        signals=signals,
    )
