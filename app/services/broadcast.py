"""
app/services/broadcast.py — 每日播报 AI 生成服务
使用 LLM + 实时市场数据生成结构化播报内容
"""
import json
import logging
from datetime import date, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.services.llm import chat_completion
from app.services.market import fetch_realtime_quotes
from app.models.broadcast import Broadcast
from app.core.database import get_session_factory

logger = logging.getLogger(__name__)

# 主要指数
MAJOR_INDICES = [
    ("000001.SH", "上证指数"),
    ("399001.SZ", "深证成指"),
    ("399006.SZ", "创业板指"),
]

# 热门行业龙头
SECTOR_LEADERS = [
    ("600519.SH", "贵州茅台"),
    ("000858.SZ", "五粮液"),
    ("300750.SZ", "宁德时代"),
    ("002594.SZ", "比亚迪"),
    ("601318.SH", "中国平安"),
    ("600036.SH", "招商银行"),
    ("000063.SZ", "中兴通讯"),
    ("600276.SH", "恒瑞医药"),
    ("300059.SZ", "东方财富"),
    ("688981.SH", "中芯国际"),
]


async def _fetch_market_snapshot() -> dict:
    """拉取关键行情数据作为 LLM 上下文"""
    symbols = [s[0] for s in MAJOR_INDICES + SECTOR_LEADERS]
    all_items = {}

    for symbol in symbols:
        try:
            items = await fetch_realtime_quotes([symbol])
            if items:
                all_items[symbol] = {
                    "name": items[0].name,
                    "price": items[0].price,
                    "change_pct": items[0].change_pct,
                }
        except Exception:
            logger.warning(f"Failed to fetch quote for {symbol}")

    return all_items


def _build_prompt(market_data: dict) -> str:
    """构建 LLM prompt"""
    indices_text = ""
    for code, name in MAJOR_INDICES:
        d = market_data.get(code)
        if d:
            direction = "上涨" if d["change_pct"] >= 0 else "下跌"
            indices_text += f"- {name}({code})：{d['price']:.2f}，{direction}{abs(d['change_pct']):.2f}%\n"

    leaders_text = ""
    for code, name in SECTOR_LEADERS:
        d = market_data.get(code)
        if d:
            direction = "+" if d["change_pct"] >= 0 else ""
            leaders_text += f"- {name}({code})：{d['price']:.2f}，{direction}{d['change_pct']:.2f}%\n"

    return f"""你是专业的A股市场分析师。请根据以下实时行情数据，生成一份简洁专业的每日播报。

当前指数表现：
{indices_text}
热门行业龙头表现：
{leaders_text}

请以 JSON 格式返回播报内容（严格按以下结构，不要多余内容）：
{{
    "overview": "大盘综述（2-3句话，概括今日市场整体表现、资金流向、市场情绪）",
    "recommendations": [
        {{
            "symbol": "股票代码",
            "name": "股票简称",
            "confidence": 75,
            "reason": "推荐理由（一句话，基于今日表现的逻辑）"
        }}
    ],
    "risk_warnings": "风险提示（1-2句话，基于市场波动、政策等因素的实际风险提醒）"
}}

要求：
1. overview 要基于实际数据，不要泛泛而谈
2. recommendations 列出 2-3 只今日表现突出或有逻辑支撑的标的，confidence 50-95
3. 股票代码使用实际代码，不要编造
4. risk_warnings 要具体到当日风险点
5. 只返回 JSON，不要 markdown 代码块包裹"""


async def generate_daily_broadcast(target_date: date | None = None) -> Broadcast:
    """生成每日播报并持久化"""
    if target_date is None:
        target_date = date.today()

    # 1. 拉取行情
    market_data = await _fetch_market_snapshot()
    if not market_data:
        raise ValueError("无法获取行情数据，播报生成失败")

    # 2. LLM 生成
    prompt = _build_prompt(market_data)
    try:
        raw = await chat_completion(
            messages=[
                {"role": "system", "content": "你是专业的A股市场分析师，只输出 JSON，不输出其他内容。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.5,
        )
        raw = raw.strip()
        if raw.startswith("```"):
            lines = raw.split("\n")
            raw = "\n".join(lines[1:])
            if raw.endswith("```"):
                raw = raw[:-3]
        content = json.loads(raw)
    except Exception as e:
        logger.error(f"LLM generation failed: {e}")
        content = {
            "overview": "今日市场数据加载中，请稍后查看完整播报。",
            "recommendations": [],
            "risk_warnings": "市场有风险，投资需谨慎。",
        }

    # 3. 写入 DB（upsert：存在则更新，不存在则插入）
    factory = get_session_factory()
    async with factory() as session:
        # 先尝试查找已有记录
        result = await session.execute(
            select(Broadcast).where(Broadcast.date == target_date).limit(1)
        )
        broadcast = result.scalar_one_or_none()

        if broadcast:
            broadcast.title = f"{target_date.strftime('%m月%d日')} 每日播报"
            broadcast.content = content
        else:
            broadcast = Broadcast(
                date=target_date,
                title=f"{target_date.strftime('%m月%d日')} 每日播报",
                content=content,
            )
            session.add(broadcast)

        await session.commit()
        await session.refresh(broadcast)
        return broadcast


async def get_today_broadcast(db: AsyncSession) -> dict | None:
    """获取今日播报"""
    today = date.today()
    result = await db.execute(
        select(Broadcast)
        .where(Broadcast.date == today)
        .order_by(Broadcast.created_at.desc())
        .limit(1)
    )
    broadcast = result.scalar_one_or_none()
    return _broadcast_to_dict(broadcast) if broadcast else None


async def get_broadcast_list(db: AsyncSession, limit: int = 10, offset: int = 0) -> dict:
    """分页获取播报列表"""
    count_result = await db.execute(select(func.count(Broadcast.id)))
    total = count_result.scalar() or 0

    result = await db.execute(
        select(Broadcast)
        .order_by(Broadcast.date.desc())
        .offset(offset)
        .limit(limit)
    )
    items = [_broadcast_to_dict(b) for b in result.scalars().all()]

    return {
        "items": items,
        "total": total,
        "has_prev": offset > 0,
        "has_next": offset + limit < total,
    }


async def get_broadcast_by_date(db: AsyncSession, date_str: str) -> dict | None:
    """按日期获取播报"""
    try:
        target_date = date.fromisoformat(date_str)
    except ValueError:
        return None

    result = await db.execute(
        select(Broadcast).where(Broadcast.date == target_date).limit(1)
    )
    broadcast = result.scalar_one_or_none()
    return _broadcast_to_dict(broadcast) if broadcast else None


async def get_broadcast_by_id(db: AsyncSession, broadcast_id: str) -> dict | None:
    result = await db.execute(
        select(Broadcast).where(Broadcast.id == broadcast_id).limit(1)
    )
    broadcast = result.scalar_one_or_none()
    return _broadcast_to_dict(broadcast) if broadcast else None


def _broadcast_to_dict(b: Broadcast) -> dict:
    return {
        "id": b.id,
        "date": b.date.isoformat() if b.date else "",
        "title": b.title,
        "content": b.content or {"overview": "", "recommendations": [], "risk_warnings": ""},
        "audio_url": b.audio_url,
        "duration": b.duration,
        "created_at": b.created_at.isoformat() if b.created_at else "",
    }
