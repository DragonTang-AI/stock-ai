"""P1-F3: AI托管定时调度任务"""
import asyncio
import logging
from datetime import datetime, timezone
from sqlalchemy import text
from app.core.database import async_session_maker
from app.core.exceptions import AppException

logger = logging.getLogger(__name__)


async def get_hosted_users(db) -> list[int]:
    result = await db.execute(
        text("SELECT user_id FROM public.hosted_settings "
             "WHERE mode = 'AI_HOSTED' AND disabled_at IS NULL")
    )
    return [row[0] for row in result.fetchall()]


async def is_recently_executed(db, user_id: int, symbol: str, hours: int = 24) -> bool:
    result = await db.execute(
        text(f"SELECT COUNT(*) FROM public.hosted_logs "
             f"WHERE user_id = :uid AND symbol = :sym "
             f"AND status = 'TRIGGERED' "
             f"AND created_at > NOW() - INTERVAL '{hours} hours'"),
        {"uid": user_id, "sym": symbol}
    )
    return (result.scalar() or 0) > 0


async def run_hosted_signal_processor():
    """
    定时处理托管信号
    
    流程：
    1. 运行 4-Agent 选股委员会
    2. 对每个托管用户执行信号合规检查
    3. 自动触发纸面交易
    """
    logger.info("[托管调度] 开始处理托管信号...")
    
    async with async_session_maker() as db:
        try:
            from app.services.committee_service import run_committee_analysis
            from app.services import hosted as hosted_svc
            
            # 运行选股
            signals = await run_committee_analysis(market="A", limit=20)
            buy_signals = [s for s in signals if s.action == "BUY"]
            logger.info(f"[托管调度] BUY 信号: {len(buy_signals)} 个")
            
            if not buy_signals:
                return
            
            # 获取托管用户
            hosted_users = await get_hosted_users(db)
            logger.info(f"[托管调度] 托管用户: {len(hosted_users)} 个")
            
            executed = skipped = blocked = 0
            
            for user_id in hosted_users:
                for signal in buy_signals:
                    if await is_recently_executed(db, user_id, signal.symbol, hours=24):
                        skipped += 1
                        continue
                    
                    # 构造 User-like 对象
                    class _User:
                        def __init__(self, uid):
                            self.id = uid
                    
                    try:
                        await hosted_svc.trigger_signal_order(
                            db=db,
                            user=_User(user_id),
                            symbol=signal.symbol,
                            signal_id=signal.id or "scheduled",
                            action=signal.action,
                            confidence=signal.confidence,
                            target_price=signal.target_price or 0.0,
                            reasoning=f"[定时调度] {signal.reason_codes[:2] if signal.reason_codes else []}",
                        )
                        executed += 1
                        logger.info(f"[托管调度] ✅ 用户{user_id} 执行 {signal.symbol}")
                    except AppException as e:
                        blocked += 1
                        logger.debug(f"[托管调度] 拦截 {signal.symbol}: {e.detail}")
                    except Exception as e:
                        logger.warning(f"[托管调度] 异常 {signal.symbol}: {e}")
            
            logger.info(f"[托管调度] 完成: 执行{executed} 跳过{skipped} 拦截{blocked}")
        
        except Exception as e:
            logger.error(f"[托管调度] 调度异常: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(run_hosted_signal_processor())
