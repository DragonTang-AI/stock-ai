"""app/services/daily_picks_service.py — 每日推荐列表服务

机制：
- 每日 8:00 由调度器触发生成一次（双引擎：factor 因子评分 + committee_llm LLM 委员会），
  结果持久化到 daily_picks 表
- C 端直接读取已生成的列表（不触发 LLM / 实时计算）
- 用户手动刷新时强制重新生成（source=refresh）

引擎：
- factor: 复用 /selection/recommend 多因子评分引擎（确定性，快）
- committee_llm: LangGraph 4-Agent 委员会（LLM 推理，候选池 top15）
  C 端默认展示 committee_llm 结果；未生成/失败时自动 fallback 到 factor。
"""
import json
import logging
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_scheduler_db_context
from app.models.agent import Notification
from app.models.daily_pick import DailyPick
from app.models.pick_tracking import PickTracking
from app.schemas.selection import RecommendRequest
from app.schemas.signals import Signal
from app.services.committee_service import run_committee_analysis
from app.services.selection import recommend_stocks

logger = logging.getLogger(__name__)

DEFAULT_TOP_N = 10
DEFAULT_MARKET = "A"

# 引擎标识
ENGINE_FACTOR = "factor"
ENGINE_COMMITTEE_LLM = "committee_llm"
SUPPORTED_ENGINES = {ENGINE_FACTOR, ENGINE_COMMITTEE_LLM}

# LLM 委员会候选池规模（top15 跑通后再扩展）
LLM_CANDIDATE_LIMIT = 15


def _signal_to_pick(signal: Signal) -> dict:
    """将委员会 Signal 转为前端兼容的 picks 条目格式（保留 agent_scores）。"""
    factors = []
    if signal.agent_scores is not None:
        factors = [
            {
                "name": "technical",
                "agent": "technical",
                "score": signal.agent_scores.technical,
                "confidence": signal.agent_scores.technical,
                "reasoning": f"技术面评分 {signal.agent_scores.technical}",
            },
            {
                "name": "fundamental",
                "agent": "fundamental",
                "score": signal.agent_scores.fundamental,
                "confidence": signal.agent_scores.fundamental,
                "reasoning": f"基本面评分 {signal.agent_scores.fundamental}",
            },
            {
                "name": "sentiment",
                "agent": "sentiment",
                "score": signal.agent_scores.sentiment,
                "confidence": signal.agent_scores.sentiment,
                "reasoning": f"舆情评分 {signal.agent_scores.sentiment}",
            },
        ]
    return {
        "symbol": signal.symbol,
        "name": signal.symbol_name or signal.symbol,
        "action": signal.action.value,
        "confidence": signal.confidence,
        "score": signal.confidence,
        "reasoning": signal.reasoning,
        "summary": signal.reasoning,
        "reason_codes": [rc.value for rc in signal.reason_codes],
        "factors": factors,
        "agent_scores": signal.agent_scores.model_dump() if signal.agent_scores else None,
        "target_price": signal.target_price,
        "stop_loss": signal.stop_loss,
        "take_profit": signal.take_profit,
        "tags": signal.tags,
    }


async def generate_daily_picks(
    *,
    market: str = DEFAULT_MARKET,
    top_n: int = DEFAULT_TOP_N,
    source: str = "scheduler",
    engine: str = ENGINE_FACTOR,
    notify_user_ids: list[int] | None = None,
) -> dict:
    """按指定引擎生成每日推荐并持久化（upsert）。

    若当日该引擎已有记录则覆盖更新，返回落库后的记录信息。
    """
    if engine not in SUPPORTED_ENGINES:
        return {"success": False, "trade_date": date.today().isoformat(), "market": market, "error": f"unsupported engine: {engine}"}

    trade_date = date.today()
    trade_date_str = trade_date.isoformat()

    logger.info("[daily-picks] 开始生成 %s 每日推荐 (market=%s, top_n=%d, engine=%s, source=%s)",
                trade_date_str, market, top_n, engine, source)

    try:
        if engine == ENGINE_FACTOR:
            req = RecommendRequest(market=market, top_n=top_n, strategy="momentum")
            result = await recommend_stocks(req)
            picks = [p.model_dump() for p in result.picks]
        else:
            committee = await run_committee_analysis(
                market=market,
                trade_date=trade_date,
                candidate_limit=LLM_CANDIDATE_LIMIT,
                signal_limit=top_n,
                llm_enabled=True,
            )
            picks = [_signal_to_pick(s) for s in committee.signals]

        picks_json = json.dumps(picks, ensure_ascii=False)

        async with get_scheduler_db_context() as db:
            existing = await _get_record(db, trade_date_str, market, engine)
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
                    engine=engine,
                    picks_json=picks_json,
                    source=source,
                    status="ok",
                )
                db.add(record)
                await db.flush()
                record_id = record.id
            # 回测数据源：逐票写入 pick_tracking（upsert）
            await _track_picks(db, trade_date_str, market, engine, picks)

            # 通知中心联动：生成成功后向指定用户写入通知
            if notify_user_ids:
                try:
                    source_label = "每日推荐已更新" if source == "scheduler" else "每日推荐已刷新"
                    pick_str = "、".join(
                        f"{p.get('name') or p.get('symbol_name')}({p.get('symbol')})"
                        for p in picks[:5] if p.get("symbol")
                    )
                    content = f"今日推荐：{pick_str}" if pick_str else "今日推荐已生成，点击查看详情"
                    for uid in notify_user_ids:
                        db.add(Notification(
                            user_id=uid,
                            type="selection",
                            title=source_label,
                            content=content,
                            channel="inbox",
                        ))
                    logger.info("[daily-picks] 通知中心联动: 写入 %d 条通知 (source=%s)", len(notify_user_ids), source)
                except Exception:  # noqa: BLE001
                    logger.exception("[daily-picks] 写入通知失败")
            await db.commit()

        logger.info("[daily-picks] 生成完成: engine=%s, %d 只 (record_id=%s)", engine, len(picks), record_id)
        return {
            "success": True,
            "record_id": record_id,
            "trade_date": trade_date_str,
            "market": market,
            "engine": engine,
            "source": source,
            "picks": picks,
        }
    except Exception as exc:  # noqa: BLE001
        logger.error("[daily-picks] 生成失败 (engine=%s): %s", engine, exc)
        async with get_scheduler_db_context() as db:
            existing = await _get_record(db, trade_date_str, market, engine)
            if existing:
                existing.status = "error"
                existing.error_msg = str(exc)[:500]
                existing.updated_at = datetime.now(timezone.utc)
                await db.commit()
        return {
            "success": False,
            "trade_date": trade_date_str,
            "market": market,
            "engine": engine,
            "error": str(exc),
        }


async def get_daily_picks(
    market: str = DEFAULT_MARKET,
    engine: str = ENGINE_COMMITTEE_LLM,
    fallback: bool = True,
) -> dict:
    """读取当日已生成的每日推荐（只读，无计算）。

    默认读取 committee_llm（LLM 委员会）；若当日 LLM 结果未生成或失败，
    自动 fallback 到 factor（因子评分），并标注 actual_engine 供前端提示。
    fallback=False 时严格按指定 engine 读取（调度器存在性检查用）。
    """
    trade_date_str = date.today().isoformat()

    async with get_scheduler_db_context() as db:
        record = await _get_record(db, trade_date_str, market, engine)
        actual_engine = engine
        if fallback and (record is None or record.status != "ok"):
            record = await _get_record(db, trade_date_str, market, ENGINE_FACTOR)
            actual_engine = ENGINE_FACTOR

    if record is None:
        return {
            "success": True,
            "found": False,
            "trade_date": trade_date_str,
            "market": market,
            "engine": engine,
            "message": "当日推荐尚未生成",
            "picks": [],
        }

    picks = json.loads(record.picks_json or "[]")
    return {
        "success": True,
        "found": True,
        "trade_date": trade_date_str,
        "market": market,
        "engine": engine,
        "actual_engine": actual_engine,
        "source": record.source,
        "status": record.status,
        "error_msg": record.error_msg,
        "generated_at": record.updated_at.isoformat() if record.updated_at else None,
        "picks": picks,
    }


async def refresh_daily_picks(market: str = DEFAULT_MARKET, top_n: int = DEFAULT_TOP_N, engine: str = ENGINE_COMMITTEE_LLM, notify_user_id: int | None = None) -> dict:
    """用户手动刷新：强制重新生成当日推荐（默认 LLM 委员会引擎）。"""
    return await generate_daily_picks(
        market=market,
        top_n=top_n,
        source="refresh",
        engine=engine,
        notify_user_ids=[notify_user_id] if notify_user_id else None,
    )


async def _get_record(db: AsyncSession, trade_date: str, market: str, engine: str) -> DailyPick | None:
    stmt = select(DailyPick).where(
        DailyPick.trade_date == trade_date,
        DailyPick.market == market,
        DailyPick.engine == engine,
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def _track_picks(
    db: AsyncSession,
    trade_date: str,
    market: str,
    engine: str,
    picks: list[dict],
) -> None:
    """将本次推荐逐票写入 pick_tracking（回测闭环数据源，按唯一键 upsert）。"""
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    for pick in picks:
        symbol = pick.get("symbol")
        if not symbol:
            continue
        values = {
            "trade_date": trade_date,
            "market": market,
            "engine": engine,
            "symbol": symbol,
            "symbol_name": pick.get("name") or pick.get("symbol_name"),
            "action": pick.get("action"),
            "confidence": pick.get("confidence") or pick.get("score"),
        }
        stmt = pg_insert(PickTracking).values(**values)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_pick_tracking_date_market_engine_symbol",
            set_={
                "symbol_name": stmt.excluded.symbol_name,
                "action": stmt.excluded.action,
                "confidence": stmt.excluded.confidence,
            },
        )
        await db.execute(stmt)
