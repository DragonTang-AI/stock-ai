"""定时播报路由"""
from fastapi import APIRouter, Depends, Query
from app.core.database import get_db
from app.models.user import User
from app.api.v1.auth import get_current_user
from app.schemas.broadcast import BroadcastItem, BroadcastListResponse, BroadcastContent, BroadcastRecommendation
from datetime import datetime, timedelta
import random

router = APIRouter()

# 模拟数据
_MARKET_NAMES = {"000001": "平安银行", "600519": "贵州茅台", "000858": "五粮液", "300750": "宁德时代", "002594": "比亚迪"}
_SAMPLE_STOCKS = ["000001", "600519", "000858", "300750", "002594"]

def _gen_broadcast(date_str: str) -> BroadcastItem:
    random.seed(date_str)
    symbols = random.sample(_SAMPLE_STOCKS, 3)
    recs = [BroadcastRecommendation(
        symbol=s, name=_MARKET_NAMES.get(s, s), confidence=round(random.uniform(60, 95), 1),
        reason=f"技术面形态良好，基本面持续改善"
    ) for s in symbols]
    return BroadcastItem(
        id=f"bc_{date_str}",
        date=date_str,
        created_at=f"{date_str}T09:00:00",
        title=f"{date_str} 每日播报",
        content=BroadcastContent(
            overview=f"今日市场整体震荡，{len(symbols)}只精选标的值得关注。",
            recommendations=recs,
            risk_warnings="以上内容仅供参考，不构成投资建议。股市有风险，投资需谨慎。"
        ),
        audio_url=None,
        duration=None,
    )

@router.get("/broadcast/today", response_model=BroadcastItem)
async def get_today_broadcast(current_user: User = Depends(get_current_user)):
    today = datetime.now().strftime("%Y-%m-%d")
    return _gen_broadcast(today)

@router.get("/broadcast/list", response_model=BroadcastListResponse)
async def get_broadcast_list(
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
):
    today = datetime.now()
    items = []
    for i in range(offset, offset + limit):
        date_str = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        items.append(_gen_broadcast(date_str))
    total = 60  # 模拟总数
    return BroadcastListResponse(
        items=items,
        total=total,
        has_prev=offset > 0,
        has_next=offset + limit < total,
    )

@router.get("/broadcast/{date}", response_model=BroadcastItem)
async def get_broadcast_by_date(date: str, current_user: User = Depends(get_current_user)):
    return _gen_broadcast(date)

@router.get("/broadcast/audio/{broadcast_id}")
async def get_broadcast_audio(broadcast_id: str, current_user: User = Depends(get_current_user)):
    return {"audio_url": None, "duration": 0, "message": "音频生成功能即将上线"}
