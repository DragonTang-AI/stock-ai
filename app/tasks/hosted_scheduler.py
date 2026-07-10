"""P1-F3: AI托管定时调度任务 v2.0 — 全自动买卖决策"""
import asyncio
import logging
from datetime import datetime, timezone, date
from decimal import Decimal
from typing import Optional
from sqlalchemy import text

from app.core.database import get_session_factory
from app.core.exceptions import AppException

logger = logging.getLogger(__name__)

# === 风控阈值 ===
STOP_LOSS_PCT = -8.0       # 止损线：浮亏超过 8% 强制卖出
TAKE_PROFIT_PCT = 15.0     # 止盈线：浮盈超过 15% 强制卖出
MAX_POSITIONS = 8           # 最大持仓数（超过则不再买入）
MIN_CASH_RESERVE = 5000.0   # 最低保留现金
DEFAULT_CASH = 100000.0     # 默认总资金


async def _get_user_account(db, user_id: int):
    result = await db.execute(
        text("SELECT id, balance FROM accounts WHERE user_id = :uid"),
        {"uid": user_id}
    )
    return result.fetchone()


async def _get_user_positions(db, account_id: int):
    sql = """
        SELECT id, symbol, name, quantity, available, cost_price, cost_amount,
               market_price, market_value, 
               CASE WHEN cost_price > 0 
                    THEN ((market_price - cost_price) / cost_price * 100) 
                    ELSE 0 END as profit_pct
        FROM positions 
        WHERE account_id = :aid 
        ORDER BY market_value DESC
    """
    result = await db.execute(text(sql), {"aid": account_id})
    return result.fetchall()


async def get_hosted_users(db) -> list[int]:
    result = await db.execute(
        text("SELECT user_id FROM hosted_settings "
             "WHERE mode = 'AI_HOSTED' AND disabled_at IS NULL")
    )
    return [row[0] for row in result.fetchall()]


async def is_recently_executed(db, user_id: int, symbol: str, action: str, hours: int = 24) -> bool:
    result = await db.execute(
        text(f"SELECT COUNT(*) FROM hosted_logs "
             f"WHERE user_id = :uid AND symbol = :sym AND action = :act "
             f"AND status = 'TRIGGERED' "
             f"AND created_at > NOW() - INTERVAL '{hours} HOURS'"),
        {"uid": user_id, "sym": symbol, "act": action}
    )
    return (result.scalar() or 0) > 0


async def run_hosted_signal_processor():
    """
    AI托管完整调度流程：

    Phase 1 — 持仓巡检（卖出决策）
        对每个托管用户的每只持仓：
        a) 止损检查：浮亏超过 8% → 强制全仓卖出
        b) 止盈检查：浮盈超过 15% → 强制全仓卖出
        c) 风险减仓：浮亏 5-8% 且未触发止损 → 减仓 50%

    Phase 2 — 选股买入
        a) 运行 4-Agent 选股委员会
        b) 对 top-5 信号按置信度排序
        c) 科学分配资金（权重=置信度占比）
    """
    logger.info("[托管调度v2] 开始全自动买卖决策...")

    async with get_session_factory()() as db:
        try:
            # ============================================
            # Phase 1: 持仓巡检 & 卖出决策
            # ============================================
            hosted_users = await get_hosted_users(db)
            if not hosted_users:
                logger.info("[托管调度v2] 无托管用户，跳过")
                return

            logger.info(f"[托管调度v2] 托管用户: {len(hosted_users)} 个")

            sell_executed = 0
            sell_skipped = 0

            for user_id in hosted_users:
                acct = await _get_user_account(db, user_id)
                if not acct:
                    continue
                account_id, balance = acct[0], float(acct[1])

                positions = await _get_user_positions(db, account_id)
                if not positions:
                    continue

                logger.info(f"[托管调度v2] 用户{user_id} 持仓: {len(positions)} 只")

                for pos in positions:
                    pos_id = pos[0]
                    symbol = pos[1]
                    name = pos[2]
                    qty = int(pos[3])
                    available = int(pos[4])
                    cost_price = float(pos[5]) if pos[5] else 0.0
                    cost_amt = float(pos[6]) if pos[6] else 0.0
                    mkt_price = float(pos[7]) if pos[7] else cost_price
                    mkt_val = float(pos[8]) if pos[8] else 0.0
                    profit_pct = float(pos[9]) if pos[9] else 0.0

                    # 24h 内已卖出过 → 跳过
                    if await is_recently_executed(db, user_id, symbol, 'SELL', hours=24):
                        sell_skipped += 1
                        continue

                    sell_reason = None
                    sell_pct = 0  # 卖出比例（0~100）

                    # a) 止损检查
                    if profit_pct <= STOP_LOSS_PCT:
                        sell_reason = f"止损: 浮亏 {profit_pct:.1f}% <= {STOP_LOSS_PCT}%"
                        sell_pct = 100

                    # b) 止盈检查
                    elif profit_pct >= TAKE_PROFIT_PCT:
                        sell_reason = f"止盈: 浮盈 {profit_pct:.1f}% >= {TAKE_PROFIT_PCT}%"
                        sell_pct = 100

                    # c) 风险减仓
                    elif profit_pct <= -5.0 and profit_pct > STOP_LOSS_PCT:
                        sell_reason = f"风险减仓: 浮亏 {profit_pct:.1f}%，减仓 50%"
                        sell_pct = 50

                    if sell_reason and sell_pct > 0:
                        from app.services import hosted as hosted_svc
                        sell_qty = max(100, int(available * sell_pct / 100 / 100) * 100)

                        class _User:
                            def __init__(self, uid):
                                self.id = uid

                        try:
                            result = await hosted_svc.trigger_signal_order(
                                db=db, user=_User(user_id),
                                symbol=symbol,
                                signal_id=f"sell_{symbol}_{int(datetime.now().timestamp())}",
                                action="SELL",
                                confidence=90,
                                target_price=mkt_price,
                                reasoning=sell_reason,
                                quantity=sell_qty,
                            )
                            sell_executed += 1
                            logger.info(f"[托管调度v2] 卖出 {symbol}: {sell_reason}, {sell_qty}股")
                        except AppException as e:
                            logger.info(f"[托管调度v2] 卖出拦截 {symbol}: {e.details}")
                        except Exception as e:
                            logger.warning(f"[托管调度v2] 卖出异常 {symbol}: {e}")

            # ============================================
            # Phase 2: 选股 & 买入决策
            # ============================================
            from app.services.committee_service import run_committee_analysis

            try:
                committee_result = await run_committee_analysis(
                    market="A", trade_date=date.today()
                )
                buy_signals = [
                    s for s in committee_result.signals
                    if str(s.action.value) == "BUY"
                ]
            except Exception as e:
                logger.warning(f"[托管调度v2] 选股失败: {e}")
                buy_signals = []

            if not buy_signals:
                logger.info(
                    f"[托管调度v2] Phase1完成: 卖出{sell_executed}跳过{sell_skipped}. "
                    f"无买入信号，跳过Phase2"
                )
                return

            # 按置信度排序，取 top-5
            buy_signals.sort(key=lambda s: s.confidence, reverse=True)
            buy_signals = buy_signals[:5]
            logger.info(f"[托管调度v2] Phase2: {len(buy_signals)} 个买入信号 (top-5)")

            buy_executed = buy_skipped = buy_blocked = 0

            for user_id in hosted_users:
                acct = await _get_user_account(db, user_id)
                if not acct:
                    continue
                account_id, balance = acct[0], float(acct[1])

                # 获取当前持仓数和总资产
                positions = await _get_user_positions(db, account_id)
                pos_count = len(positions)
                pos_value = 0.0
                if positions:
                    for p in positions:
                        mv = float(p[8]) if p[8] else 0.0
                        pos_value += mv
                total_assets = balance + pos_value

                # 仓位上限检查
                if pos_count >= MAX_POSITIONS:
                    logger.info(f"[托管调度v2] 用户{user_id} 已达{MAX_POSITIONS}只上限")
                    continue

                # 可用于买入的信号数
                available_slots = MAX_POSITIONS - pos_count
                effective_signals = buy_signals[:available_slots]

                # 可用现金（保留最低余额）
                available_cash = max(0, balance - MIN_CASH_RESERVE)
                if available_cash < 1000:
                    continue

                # 按置信度权重分配资金
                total_conf = sum(s.confidence for s in effective_signals)
                if total_conf == 0:
                    continue

                from app.services import hosted as hosted_svc

                for signal in effective_signals:
                    if await is_recently_executed(db, user_id, signal.symbol, 'BUY', hours=24):
                        buy_skipped += 1
                        continue

                    # 权重分配：置信度越高，分配资金越多
                    weight = signal.confidence / total_conf
                    allocated = min(available_cash * weight, total_assets * 0.15)
                    target_price = signal.target_price or 0
                    if target_price <= 0:
                        continue
                    qty = int(allocated / target_price / 100) * 100
                    if qty < 100:
                        continue

                    class _User:
                        def __init__(self, uid):
                            self.id = uid

                    try:
                        result = await hosted_svc.trigger_signal_order(
                            db=db, user=_User(user_id),
                            symbol=signal.symbol,
                            signal_id=signal.signal_id,
                            action="BUY",
                            confidence=signal.confidence,
                            target_price=signal.target_price or 0.0,
                            reasoning=signal.reasoning or f"委员会选股置信度{signal.confidence}",
                        )
                        buy_executed += 1
                        logger.info(
                            f"[托管调度v2] 买入 {signal.symbol} "
                            f"置信度{signal.confidence} 分配{allocated:.0f}元"
                        )
                    except AppException as e:
                        buy_blocked += 1
                        logger.info(f"[托管调度v2] 买入拦截 {signal.symbol}: {e.details}")
                    except Exception as e:
                        logger.warning(f"[托管调度v2] 买入异常 {signal.symbol}: {e}")

            logger.info(
                f"[托管调度v2] 完成: "
                f"卖出{sell_executed}跳过{sell_skipped} | "
                f"买入{buy_executed}跳过{buy_skipped}拦截{buy_blocked}"
            )

        except Exception as e:
            logger.error(f"[托管调度v2] 调度异常: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(run_hosted_signal_processor())
