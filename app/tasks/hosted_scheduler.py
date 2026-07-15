"""P1-F3: AI托管定时调度任务 v3.0 — LLM智能决策 + T+1感知 + 防重入修复"""
import asyncio
import logging
import json
from datetime import datetime, timezone, date
from typing import Optional

from sqlalchemy import text

from app.core.database import get_session_factory
from app.core.exceptions import AppException

logger = logging.getLogger(__name__)

# === 风控阈值（仅作为 LLM 不可用时的回退） ===
STOP_LOSS_PCT = -8.0
TAKE_PROFIT_PCT = 15.0
MAX_POSITIONS = 8
MIN_CASH_RESERVE = 5000.0
LOT_SIZE = 100


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
        WHERE account_id = :aid AND quantity > 0
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
    """检查最近是否已执行过（含 TRIGGERED / BLOCKED / SKIPPED，防止反复尝试）"""
    result = await db.execute(
        text(f"SELECT COUNT(*) FROM hosted_logs "
             f"WHERE user_id = :uid AND symbol = :sym AND action = :act "
             f"AND created_at > NOW() - INTERVAL '{hours} HOURS'"),
        {"uid": user_id, "sym": symbol, "act": action}
    )
    return (result.scalar() or 0) > 0


# ============================================================
# LLM 智能卖出决策
# ============================================================

SELL_DECISION_PROMPT = """你是 A 股量化交易策略分析师。请逐一分析以下持仓，给出操作建议。

【交易规则】
- A股 T+1 制度：持仓中的 available=0 已由系统排除，你看到的所有股票都可以卖出
- 决策类型：[HOLD 持有] [SELL_ALL 全仓卖出] [SELL_HALF 减半] [SELL_QUARTER 减1/4]
- 优化目标：控制回撤 + 捕捉趋势 + 资金效率最大化

【当前持仓】
{positions_text}

【资产概况】总资产 {total_assets:.0f} 元 | 现金 {balance:.0f} 元 | 持仓 {pos_count} 只

请以 JSON 数组输出每只股票的决策。要求：
- 每只股票必须有决策，不要遗漏
- 亏损票需要判断：是短期波动还是趋势反转，不要机械止损
- 盈利票需要判断：是否还有上涨空间，不要过早止盈
- 置信度 50-70 表示不确定倾向持有，80-100 表示坚定

只输出 JSON 数组：
[{{"symbol":"601939.SH","action":"HOLD","confidence":65,"reason":"银行股防御性持有，目前仅浮亏1%"}}]
"""


async def _llm_sell_decision(
    db, user_id: int, sellable_positions: list,
    total_assets: float, balance: float
) -> list[dict]:
    """调用 DeepSeek LLM 对可卖出持仓做出智能决策"""
    # 构建持仓行
    lines = []
    for pos in sellable_positions:
        profit_pct = float(pos[9]) if pos[9] else 0.0
        profit_str = f"+{profit_pct:.1f}%" if profit_pct >= 0 else f"{profit_pct:.1f}%"
        lines.append(
            f"  {pos[1]:12s} {pos[2] or '?':8s} "
            f"持仓{pos[3]}股(可用{pos[4]}) "
            f"成本¥{pos[5]:.2f} 现价¥{pos[7]:.2f} "
            f"市值¥{pos[8]:.0f} "
            f"盈亏{profit_str}"
        )

    prompt = SELL_DECISION_PROMPT.format(
        positions_text="\n".join(lines),
        total_assets=total_assets,
        balance=balance,
        pos_count=len(sellable_positions),
    )

    try:
        from app.services.llm import chat_completion
        response = await chat_completion(
            messages=[
                {"role": "system", "content": "你是 A 股职业交易员。只输出 JSON，不要任何解释。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
        )

        # 提取 JSON 数组
        json_str = response.strip()
        if "```json" in json_str:
            json_str = json_str.split("```json")[1].split("```")[0].strip()
        elif "```" in json_str:
            json_str = json_str.split("```")[1].split("```")[0].strip()
        elif "[" in json_str:
            json_str = json_str[json_str.index("["):json_str.rindex("]") + 1]

        decisions = json.loads(json_str)
        logger.info(f"[托管v3] LLM卖出决策完成: {len(decisions)} 只股票")
        return decisions

    except Exception as e:
        logger.warning(f"[托管v3] LLM卖出决策失败 → 回退规则引擎: {e}")
        return _fallback_sell_decision(sellable_positions)


def _fallback_sell_decision(positions: list) -> list[dict]:
    """硬编码规则回退（LLM 不可用时）"""
    decisions = []
    for pos in positions:
        profit_pct = float(pos[9]) if pos[9] else 0.0
        if profit_pct <= STOP_LOSS_PCT:
            decisions.append({"symbol": pos[1], "action": "SELL_ALL", "confidence": 100,
                              "reason": f"止损: 浮亏{profit_pct:.1f}%"})
        elif profit_pct >= TAKE_PROFIT_PCT:
            decisions.append({"symbol": pos[1], "action": "SELL_ALL", "confidence": 95,
                              "reason": f"止盈: 浮盈{profit_pct:.1f}%"})
        elif profit_pct <= -5.0:
            decisions.append({"symbol": pos[1], "action": "SELL_HALF", "confidence": 80,
                              "reason": f"风险减仓: 浮亏{profit_pct:.1f}%"})
        else:
            decisions.append({"symbol": pos[1], "action": "HOLD", "confidence": 50,
                              "reason": "盈亏在安全范围内"})
    return decisions


# ============================================================
# 主调度流程
# ============================================================

async def run_hosted_signal_processor():
    """AI托管 v3.0：LLM 智能卖出 + T+1 感知"""
    logger.info("[托管v3] ======== 开始智能决策 ========")

    async with get_session_factory()() as db:
        try:
            hosted_users = await get_hosted_users(db)
            if not hosted_users:
                logger.info("[托管v3] 无托管用户，跳过")
                return

            logger.info(f"[托管v3] 托管用户: {len(hosted_users)} 个")

            # ============================================
            # Phase 1: LLM 驱动的卖出决策（含 T+1 感知）
            # ============================================
            sell_executed = 0
            sell_blocked = 0
            sell_skipped = 0
            sell_t1_locked = 0

            for user_id in hosted_users:
                acct = await _get_user_account(db, user_id)
                if not acct:
                    continue
                account_id, balance = acct[0], float(acct[1])

                all_positions = await _get_user_positions(db, account_id)
                if not all_positions:
                    continue

                # 【修复1】拆分 T+1 锁定 vs 可卖出
                sellable = []
                for p in all_positions:
                    avail = int(p[4])
                    if avail <= 0:
                        sell_t1_locked += 1
                        logger.debug(f"[托管v3] 用户{user_id} {p[1]} T+1锁定，跳过卖出")
                    else:
                        sellable.append(p)

                user_locked = len(all_positions) - len(sellable)
                sell_t1_locked += user_locked
                if user_locked > 0:
                    logger.info(f"[托管v3] 用户{user_id} T+1锁定 {user_locked} 只，可卖 {len(sellable)} 只")

                if not sellable:
                    continue

                pos_value = sum(float(p[8]) if p[8] else 0 for p in all_positions)
                total_assets = balance + pos_value

                logger.info(
                    f"[托管v3] 用户{user_id} 总持仓{len(all_positions)}只，"
                    f"可卖{len(sellable)}只，总资产¥{total_assets:.0f}"
                )

                # LLM 智能决策
                decisions = await _llm_sell_decision(
                    db, user_id, sellable, total_assets, balance
                )

                from app.services import hosted as hosted_svc

                class _User:
                    def __init__(self, uid):
                        self.id = uid

                for dec in decisions:
                    symbol = dec.get("symbol", "")
                    action = dec.get("action", "HOLD")
                    confidence = dec.get("confidence", 50)
                    reason = dec.get("reason", "")

                    if action == "HOLD":
                        continue

                    # 【修复2】防重入：24h 内已执行过（含 BLOCKED）
                    if await is_recently_executed(db, user_id, symbol, 'SELL', hours=24):
                        sell_skipped += 1
                        continue

                    # 查找持仓
                    pos = next((p for p in sellable if p[1] == symbol), None)
                    if not pos:
                        continue

                    available = int(pos[4])
                    market_price = float(pos[7]) if pos[7] else 0.0

                    if action == "SELL_ALL":
                        sell_qty = available
                    elif action == "SELL_HALF":
                        sell_qty = max(LOT_SIZE, int(available / 2 / LOT_SIZE) * LOT_SIZE)
                    elif action == "SELL_QUARTER":
                        sell_qty = max(LOT_SIZE, int(available / 4 / LOT_SIZE) * LOT_SIZE)
                    else:
                        continue

                    if sell_qty < LOT_SIZE:
                        continue

                    signal_id = f"sell_{symbol}_{int(datetime.now().timestamp())}"

                    try:
                        await hosted_svc.trigger_signal_order(
                            db=db, user=_User(user_id),
                            symbol=symbol,
                            signal_id=signal_id,
                            action="SELL",
                            confidence=confidence,
                            target_price=market_price,
                            reasoning=f"[LLM] {reason}",
                            quantity=sell_qty,
                        )
                        sell_executed += 1
                        logger.info(f"[托管v3] ✅ 卖出 {symbol} {sell_qty}股 | {reason}")
                    except AppException as e:
                        sell_blocked += 1
                        logger.info(f"[托管v3] 🚫 卖出拦截 {symbol}: {e.message}")
                    except Exception as e:
                        sell_blocked += 1
                        logger.warning(f"[托管v3] ⚠️ 卖出异常 {symbol}: {e}")

            # ============================================
            # Phase 2: 选股 & 买入决策（沿用 v2 逻辑）
            # ============================================
            from app.services.committee_service import run_committee_analysis

            buy_signals = []
            try:
                committee_result = await run_committee_analysis(
                    market="A", trade_date=date.today()
                )
                buy_signals = [
                    s for s in committee_result.signals
                    if str(s.action.value) == "BUY"
                ]
            except Exception as e:
                logger.warning(f"[托管v3] 选股失败: {e}")

            if buy_signals:
                buy_signals.sort(key=lambda s: s.confidence, reverse=True)
                buy_signals = buy_signals[:5]
                logger.info(f"[托管v3] Phase2: {len(buy_signals)} 个买入信号 (top-5)")

            buy_executed = buy_skipped = buy_blocked = 0

            for user_id in hosted_users:
                if not buy_signals:
                    break

                acct = await _get_user_account(db, user_id)
                if not acct:
                    continue
                account_id, balance = acct[0], float(acct[1])

                positions = await _get_user_positions(db, account_id)
                pos_count = len(positions)
                pos_value = sum(float(p[8]) if p[8] else 0 for p in positions) if positions else 0.0
                total_assets = balance + pos_value

                if pos_count >= MAX_POSITIONS:
                    logger.info(f"[托管v3] 用户{user_id} 已达{MAX_POSITIONS}只上限")
                    continue

                available_slots = MAX_POSITIONS - pos_count
                effective_signals = buy_signals[:available_slots]
                available_cash = max(0, balance - MIN_CASH_RESERVE)
                if available_cash < 1000:
                    continue

                total_conf = sum(s.confidence for s in effective_signals)
                if total_conf == 0:
                    continue

                from app.services import hosted as hosted_svc

                for signal in effective_signals:
                    if await is_recently_executed(db, user_id, signal.symbol, 'BUY', hours=24):
                        buy_skipped += 1
                        continue

                    weight = signal.confidence / total_conf
                    allocated = min(available_cash * weight, total_assets * 0.15)
                    target_price = signal.target_price or 0
                    if target_price <= 0:
                        continue
                    qty = int(allocated / target_price / LOT_SIZE) * LOT_SIZE
                    if qty < LOT_SIZE:
                        continue

                    class _User:
                        def __init__(self, uid):
                            self.id = uid

                    try:
                        await hosted_svc.trigger_signal_order(
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
                            f"[托管v3] ✅ 买入 {signal.symbol} "
                            f"置信度{signal.confidence} 分配{allocated:.0f}元"
                        )
                    except AppException as e:
                        buy_blocked += 1
                        logger.info(f"[托管v3] 🚫 买入拦截 {signal.symbol}: {e.message}")
                    except Exception as e:
                        buy_blocked += 1
                        logger.warning(f"[托管v3] ⚠️ 买入异常 {signal.symbol}: {e}")

            logger.info(
                f"[托管v3] ======== 完成 ========\n"
                f"  卖出: 执行{sell_executed} 拦截{sell_blocked} 跳过{sell_skipped} T+1锁定{sell_t1_locked}\n"
                f"  买入: 执行{buy_executed} 跳过{buy_skipped} 拦截{buy_blocked}"
            )

        except Exception as e:
            logger.error(f"[托管v3] 调度异常: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(run_hosted_signal_processor())
