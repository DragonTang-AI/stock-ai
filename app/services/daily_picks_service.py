"""app/services/daily_picks_service.py — 每日推荐列表服务

机制：
- 每日 8:00 由调度器触发生成一次（LLM 委员会管线），结果持久化到 daily_picks 表
- C 端直接读取已生成的列表（不触发 LLM / 实时计算）
- 用户手动刷新时强制重新生成（source=refresh）
"""
import json
import logging
from datetime import date, datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_scheduler_db_context
from app.models.daily_pick import DailyPick
from app.services.committee_service import run_committee_analysis

logger = logging.getLogger(__name__)

DEFAULT_TOP_N = 5
DEFAULT_MARKET = "A"


def _signal_to_pick(signal) -> dict:
    """将 Signal 对象转换为 C 端友好结构（对齐前端 normalizeCommitteeResult）"""
    return {
        "symbol": signal.symbol,
        "name": signal.symbol_name or signal.symbol,
        "action": signal.action.value if hasattr(signal.action, "value") else str(signal.action),
        "confidence": signal.confidence,
        "reasoning": signal.reasoning,
        "reason_codes": [rc.value if hasattr(rc, "value") else str(rc) for rc in (signal.reason_codes or [])],
        "summary": signal.reasoning,
        "generated_at": signal.created_at.isoformat() if signal.created_at else datetime.now(timezone.utc).isoformat(),
    }


async def generate_daily_picks(
    *,
    market: str = DEFAULT_MARKET,
    top_n: int = DEFAULT_TOP_N,
    source: str = "scheduler",
) -> dict:
    """执行 4-Agent 委员会（LLM）生成每日推荐并持久化。

    若当日已有记录则覆盖更新（upsert），返回落库后的记录信息。
    """
    trade_date = date.today()
    trade_date_str = trade_date.isoformat()

    logger.info("[daily-picks] 开始生成 %s 每日推荐 (market=%s, top_n=%d, source=%s)",
                trade_date_str, market, top_n, source)

    try:
        result = await run_committee_analysis(
            market=market,
            trade_date=trade_date,
            candidate_limit=50,
            signal_limit=top_n,
        )
        picks = [_signal_to_pick(s) for s in result.signals]
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
    """读取当日已生成的每日推荐（只读，无 LLM 调用）。"""
    trade_date_str = date.today().isoformat()

    async with get_scheduler_db_context() as db:
        record = await _get_record(db, trade_date_str, market)

    if record is None:
        return {
            "success": False,
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
    from sqlalchemy import select
    stmt = select(DailyPick).where(
        DailyPick.trade_date == trade_date,
        DailyPick.market == market,
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()
