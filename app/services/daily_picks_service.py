"""app/services/daily_picks_service.py — 每日推荐列表服务

机制：
- 每日 8:00 由调度器触发生成一次（复用 /selection/recommend 因子评分引擎），
  结果持久化到 daily_picks 表
- C 端直接读取已生成的列表（不触发 LLM / 实时计算）
- 用户手动刷新时强制重新生成（source=refresh）

注意：生成引擎与选股页「AI 委员会选股」完全一致（recommend_stocks 多因子评分），
只是执行时机从「每个用户进页面实时计算」改为「总部每天 8 点预生成一次」。
"""
import json
import logging
from datetime import date, datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_scheduler_db_context
from app.models.daily_pick import DailyPick
from app.schemas.selection import RecommendRequest
from app.services.selection import recommend_stocks

logger = logging.getLogger(__name__)

DEFAULT_TOP_N = 5
DEFAULT_MARKET = "A"


async def generate_daily_picks(
    *,
    market: str = DEFAULT_MARKET,
    top_n: int = DEFAULT_TOP_N,
    source: str = "scheduler",
) -> dict:
    """使用原因子评分引擎生成每日推荐并持久化。

    若当日已有记录则覆盖更新（upsert），返回落库后的记录信息。
    """
    trade_date = date.today()
    trade_date_str = trade_date.isoformat()

    logger.info("[daily-picks] 开始生成 %s 每日推荐 (market=%s, top_n=%d, source=%s)",
                trade_date_str, market, top_n, source)

    try:
        req = RecommendRequest(market=market, top_n=top_n, strategy="momentum")
        result = await recommend_stocks(req)
        picks = [p.model_dump() for p in result.picks]
        picks_json = json.dumps(picks, ensure_ascii=False)

        async with get_scheduler_db_context() as db:
            existing = await _get_record(db, trade_date_str, market)
            if existing:
                existing.picks_json = picks_json
                existing.source = source
                existing.status = "ok"
                existing.error_msg = None
                existing.updated_at = datetime.now(timezone.utc)
                record_id = existing.id
            else:
                record = DailyPick(
                    trade_date=trade_date_str,
                    market=market,
                    picks_json=picks_json,
                    source=source,
                    status="ok",
                )
                db.add(record)
                await db.flush()
                record_id = record.id
            await db.commit()

        logger.info("[daily-picks] 生成完成: %d 只 (record_id=%s)", len(picks), record_id)
        return {
            "success": True,
            "record_id": record_id,
            "trade_date": trade_date_str,
            "market": market,
            "source": source,
            "picks": picks,
        }
    except Exception as exc:  # noqa: BLE001
        logger.error("[daily-picks] 生成失败: %s", exc)
        async with get_scheduler_db_context() as db:
            existing = await _get_record(db, trade_date_str, market)
            if existing:
                existing.status = "error"
                existing.error_msg = str(exc)[:500]
                existing.updated_at = datetime.now(timezone.utc)
                await db.commit()
        return {
            "success": False,
            "trade_date": trade_date_str,
            "market": market,
            "error": str(exc),
        }


async def get_daily_picks(market: str = DEFAULT_MARKET) -> dict:
    """读取当日已生成的每日推荐（只读，无计算）。"""
    trade_date_str = date.today().isoformat()

    async with get_scheduler_db_context() as db:
        record = await _get_record(db, trade_date_str, market)

    if record is None:
        return {
            "success": True,
            "found": False,
            "trade_date": trade_date_str,
            "market": market,
            "message": "当日推荐尚未生成",
            "picks": [],
        }

    picks = json.loads(record.picks_json or "[]")
    return {
        "success": True,
        "found": True,
        "trade_date": trade_date_str,
        "market": market,
        "source": record.source,
        "status": record.status,
        "error_msg": record.error_msg,
        "generated_at": record.updated_at.isoformat() if record.updated_at else None,
        "picks": picks,
    }


async def refresh_daily_picks(market: str = DEFAULT_MARKET, top_n: int = DEFAULT_TOP_N) -> dict:
    """用户手动刷新：强制重新生成当日推荐。"""
    return await generate_daily_picks(market=market, top_n=top_n, source="refresh")


async def _get_record(db: AsyncSession, trade_date: str, market: str) -> DailyPick | None:
    stmt = select(DailyPick).where(
        DailyPick.trade_date == trade_date,
        DailyPick.market == market,
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()
