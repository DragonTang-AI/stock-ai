"""
app/api/v1/selection.py — 选股路由（v1：多因子评分）
公开接口，无需登录即可访问（选股是通用推荐）
"""
from fastapi import APIRouter, Depends, Query
from typing import Optional
from app.models.user import User
from app.api.v1.auth import get_current_user_optional
from app.schemas.selection import RecommendResponse, RecommendRequest
from app.services.selection import recommend_stocks

router = APIRouter()


@router.get("/recommend", response_model=RecommendResponse)
async def get_recommend(
    market: str = Query("all", description="市场过滤：all/A/HK"),
    top_n: int = Query(10, ge=1, le=50, description="返回 Top N（1~50）"),
    strategy: str = Query("momentum", description="策略：momentum(追涨)/reversal(抄底)/balanced(均衡)"),
    min_change_pct: float = Query(-2.0, description="最小涨幅 %（默认 -2.0）"),
    max_change_pct: float = Query(9.0, description="最大涨幅 %（默认 9.0，避开涨停）"),
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
    )
    return await recommend_stocks(req)



@router.get("/daily")
async def get_daily():
    """前端兼容端点：/selection/daily → /selection/daily-picks"""
    return await get_daily_picks()

@router.get("/daily-picks")
async def get_daily_picks(
    current_user: Optional[User] = Depends(get_current_user_optional),
) -> dict:
    """
    每日精选（兼容旧接口，复用 recommend top 5）
    """
    req = RecommendRequest(market="all", top_n=5, strategy="momentum")
    result = await recommend_stocks(req)
    return {
        "success": True,
        "picks": [p.model_dump() for p in result.picks],
        "meta": result.meta,
    }


# ── Prescreen 粗筛接口 ────────────────────────────────────────────────
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


# ── 4-Agent 选股委员会接口 ────────────────────────────────────────────────
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
