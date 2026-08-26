"""
app/api/v1/selection.py — 选股路由（v1：多因子评分）
公开接口，无需登录即可访问（选股是通用推荐）
"""
from fastapi import APIRouter, Depends, Query
from typing import Optional
from app.models.user import User
from app.api.v1.auth import get_current_user_optional
from app.schemas.selection import RecommendResponse, RecommendRequest
import logging
from app.services.selection import recommend_stocks
from app.services.daily_picks_service import get_daily_picks as get_daily_picks_cache, refresh_daily_picks

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/recommend", response_model=RecommendResponse)
async def get_recommend(
    market: str = Query("all", description="市场过滤：all/A/HK"),
    top_n: int = Query(10, ge=1, le=50, description="返回 Top N（1~50）"),
    strategy: str = Query("momentum", description="策略：momentum(追涨)/reversal(抄底)/balanced(均衡)"),
    min_change_pct: float = Query(-2.0, description="最小涨幅 %（默认 -2.0）"),
    max_change_pct: float = Query(9.0, description="最大涨幅 %（默认 9.0，避开涨停）"),
    industry: Optional[str] = Query(None, description="行业过滤（如 金融/消费/医药/科技/新能源/制造/材料/通信/农业/港股）"),
    score_min: Optional[float] = Query(None, ge=0, le=100, description="最低综合评分"),
    score_max: Optional[float] = Query(None, ge=0, le=100, description="最高综合评分"),
    sort_by: str = Query("rank", description="排序：rank(综合分降序)/change_pct(涨幅降序)"),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """
    选股推荐（公开接口，无需登录）。

    v2.0 多因子评分（动量/RSI/趋势/量能/MACD/布林带/换手），
    支持三种策略模式：
    - momentum（默认）：追涨策略，动量+量价确认权重高
    - reversal：抄底策略，RSI超卖+布林下轨权重高
    - balanced：均衡策略，各因子权重平均

    从候选股票池（92只主流A股）中过滤风险股并按综合得分排序。

    Args:
        market: 市场过滤（all/A/HK）
        top_n: 返回 Top N（1~50）
        strategy: 策略模式（momentum/reversal/balanced）
        min_change_pct: 最小涨幅过滤
        max_change_pct: 最大涨幅过滤

    Returns:
        推荐股票列表 + 元数据
    """
    req = RecommendRequest(
        market=market,
        top_n=top_n,
        strategy=strategy,
        min_change_pct=min_change_pct,
        max_change_pct=max_change_pct,
        industry=industry,
        score_min=score_min,
        score_max=score_max,
        sort_by=sort_by,
    )
    return await recommend_stocks(req)


@router.get("/daily-picks")
async def get_daily_picks(
    market: str = Query("A", description="市场过滤：A/HK"),
    engine: str = Query("committee_llm", description="读取引擎：committee_llm(LLM委员会,默认)/factor(因子评分)"),
    current_user: Optional[User] = Depends(get_current_user_optional),
) -> dict:
    """
    每日推荐（C 端直读缓存，不触发实时计算）。

    每日 8:00 由总部调度器预生成并落库（LLM 委员会 + 因子评分双引擎），
    用户进入页面直接读取当日结果；未生成时返回空列表。
    默认读取 committee_llm（LLM 委员会结果），缺失/失败时自动 fallback 到 factor。
    """
    return await get_daily_picks_cache(market=market, engine=engine)


@router.post("/daily-picks/refresh")
async def post_daily_picks_refresh(
    market: str = Query("A", description="市场过滤：A/HK"),
    top_n: int = Query(5, ge=1, le=50, description="返回 Top N"),
    engine: str = Query("committee_llm", description="生成引擎：committee_llm(LLM委员会,默认)/factor(因子评分)"),
    current_user: Optional[User] = Depends(get_current_user_optional),
) -> dict:
    """
    每日推荐手动刷新：强制重新生成当日结果并落库（默认 LLM 委员会引擎）。
    登录用户刷新成功后自动写入一条通知中心消息。
    """
    user_id = current_user.id if current_user else None
    return await refresh_daily_picks(market=market, top_n=top_n, engine=engine, notify_user_id=user_id)

# ── Prescreen 粗筛接口 ────────────────────────────────
from datetime import date
from app.schemas.prescreen import PrescreenResponse
from app.services.prescreen_service import get_prescreen_candidates


@router.get("/prescreen", response_model=PrescreenResponse)
async def get_prescreen(
    market: str = Query("A", description="市场代码: A/HK/US"),
    limit: int = Query(20, ge=1, le=50, description="返回 Top N（1~50）"),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """
    轻量级因子粗筛（公开接口）。

    基于涨幅动量(60%) + 成交量活跃度(40%)评分，
    从候选池中筛选综合得分最高的股票。

    用途：快速获取当日强势股候选名单，
    可对接后续 4-Agent 深度分析流程。
    """
    return await get_prescreen_candidates(market=market, limit=limit)


# ── 4-Agent 选股委员会接口# ── Prescreen 粗筛接口 ────────────────────────────────
from datetime import date
from app.schemas.committee import CommitteeRunResponse
from app.services.committee_service import run_committee_analysis


@router.get("/committee", response_model=CommitteeRunResponse)
async def get_committee(
    market: str = Query("A", description="市场代码: A/HK"),
    limit: int = Query(5, ge=1, le=5, description="输出信号上限"),
    days_back: int = Query(0, ge=0, le=5, description="往前多少个交易日（0=今日）"),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """
    4-Agent 选股委员会（LangGraph）。

    流程：Prescreen 粗筛（50只）→ 3个分析师Agent → 投委会Agent → Signal列表
    Fallback：LLM 不可用时自动降级为确定性因子评分

    返回 Top N Signal（按置信分降序），包含三维度 Agent 评分和推荐理由。
    """
    trade_date = date.today()
    return await run_committee_analysis(
        market=market,
        trade_date=trade_date,
        signal_limit=limit,
    )
