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
    min_change_pct: float = Query(-2.0, description="最小涨幅 %（默认 -2.0）"),
    max_change_pct: float = Query(9.0, description="最大涨幅 %（默认 9.0，避开涨停）"),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """
    选股推荐（公开接口，无需登录）。

    基于多因子评分（动量 40% + 量比 30% + 趋势 20% + 换手 10%），
    从候选股票池中过滤风险股并按综合得分排序，返回 Top N 推荐。

    Args:
        market: 市场过滤（all/A/HK）
        top_n: 返回 Top N（1~50）
        min_change_pct: 最小涨幅过滤（默认 -2.0%）
        max_change_pct: 最大涨幅过滤（默认 9.0%，避开涨停）

    Returns:
        推荐股票列表 + 元数据（评分版本/候选数/过滤数/生成时间）
    """
    req = RecommendRequest(
        market=market,
        top_n=top_n,
        min_change_pct=min_change_pct,
        max_change_pct=max_change_pct,
    )
    return await recommend_stocks(req)


@router.get("/daily-picks")
async def get_daily_picks(
    current_user: Optional[User] = Depends(get_current_user_optional),
) -> dict:
    """
    每日精选（兼容旧接口，复用 recommend top 5）
    """
    req = RecommendRequest(market="all", top_n=5)
    result = await recommend_stocks(req)
    return {
        "success": True,
        "picks": [p.model_dump() for p in result.picks],
        "meta": result.meta,
    }
