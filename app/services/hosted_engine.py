"""
app.services.hosted_engine — AI托管调度引擎 v1.2

修复：
1. 今日盈亏：从 trades 表计算当日实际盈亏
2. 今日信号：按日统计信号生成数
3. 交易日志：结构化存储，对齐前端 HostedTradeLog 接口
4. 买入逻辑：集成选股推荐服务，替代空 watchlist
"""
import logging
import asyncio
import math
from typing import Dict, Optional, List
from datetime import datetime, timezone, date

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.core.database import get_session_factory
from app.models.user import User
from app.models.trading import Position, Trade
from app.services.advisor import diagnose_portfolio
from app.services.trading import place_order, get_or_create_account
from app.services.market import fetch_realtime_quotes
from app.services.selection import recommend_stocks
from app.schemas.selection import RecommendRequest
from app.schemas.trading import OrderRequest

logger = logging.getLogger(__name__)

# 托管决策阈值
SELL_CONFIDENCE_THRESHOLD = 40
BUY_MARKET_BULLISH_THRESHOLD = -100  # 已放宽：允许在弱市中买入
BUY_CASH_RATIO_MIN = 15.0  # 从 20% 放宽到 15%
MAX_SINGLE_BUY_PCT = 10.0


class HostedEngine:
    """AI 托管调度引擎（单例）"""

    def __init__(self):
        self._task: Optional[asyncio.Task] = None
        self._sessions: Dict[int, dict] = {}
        self._logs: Dict[int, list] = {}
        self._lock = asyncio.Lock()

    @property
    def active_count(self) -> int:
        return len(self._sessions)

    def get_logs(self, user_id: int, limit: int = 50) -> list:
        logs = self._logs.get(user_id, [])
        return logs[-limit:]

    def get_state(self, user_id: int) -> Optional[dict]:
        return self._sessions.get(user_id)

    # ── 会话管理 ──

    async def enable(self, user_id: int, config: dict) -> dict:
        async with self._lock:
            now = datetime.now(timezone.utc)
            session = {
                "user_id": user_id,
                "is_active": True,
                "enabled_at": now,
                "config": config,
                "scan_count": 0,
                "last_scan": None,
                "last_action": None,
                "total_trades": 0,
                "signals_today": 0,        # 今日信号计数
                "signals_date": str(now.date()),  # 信号计数日期
                "daily_pnl": 0.0,          # 今日盈亏
                "daily_pnl_pct": 0.0,      # 今日盈亏百分比
                "total_triggered": 0,
                "total_blocked": 0,
            }
            self._sessions[user_id] = session
            if user_id not in self._logs:
                self._logs[user_id] = []
            self._add_log(user_id, "info", "AI托管已开启")
        self._ensure_running()
        return session

    async def disable(self, user_id: int) -> dict:
        async with self._lock:
            self._sessions.pop(user_id, None)
        self._add_log(user_id, "info", "AI托管已关闭")
        if not self._sessions and self._task and not self._task.done():
            self._task.cancel()
        return {"is_active": False}

    async def update_config(self, user_id: int, config: dict) -> dict:
        async with self._lock:
            if user_id not in self._sessions:
                return {"is_active": False}
            self._sessions[user_id]["config"].update(config)
        self._add_log(user_id, "info", "托管配置已更新")
        return self._sessions[user_id]

    def is_active(self, user_id: int) -> bool:
        return user_id in self._sessions

    # ── 内部调度 ──

    def _ensure_running(self):
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._run_loop())
            logger.info("HostedEngine 调度循环已启动")

    async def _run_loop(self):
        logger.info("HostedEngine 开始调度循环")
        while True:
            try:
                if not self._sessions:
                    logger.info("HostedEngine 无活跃用户，退出调度")
                    return
                user_ids = list(self._sessions.keys())
                for user_id in user_ids:
                    try:
                        await self._scan_user(user_id)
                    except Exception as e:
                        logger.error(f"HostedEngine 扫描 user_id={user_id} 失败: {e}")
                await asyncio.sleep(60)
            except asyncio.CancelledError:
                logger.info("HostedEngine 调度循环已取消")
                return
            except Exception as e:
                logger.error(f"HostedEngine 调度循环异常: {e}")
                await asyncio.sleep(60)

    async def _scan_user(self, user_id: int):
        factory = get_session_factory()
        async with factory() as db:
            try:
                stmt = select(User).where(User.id == user_id)
                result = await db.execute(stmt)
                user = result.scalar_one_or_none()
                if user is None:
                    self._sessions.pop(user_id, None)
                    return

                diagnosis = await diagnose_portfolio(db, user)

                async with self._lock:
                    if user_id in self._sessions:
                        self._sessions[user_id]["scan_count"] += 1
                        self._sessions[user_id]["last_scan"] = datetime.now(timezone.utc).isoformat()
                        # 重置每日计数
                        today_str = str(date.today())
                        if self._sessions[user_id].get("signals_date") != today_str:
                            self._sessions[user_id]["signals_date"] = today_str
                            self._sessions[user_id]["signals_today"] = 0

                signals_count_before = self._sessions.get(user_id, {}).get("signals_today", 0)

                await self._process_sell_signals(db, user, diagnosis)
                await self._process_buy_signals(db, user, diagnosis)

                # 计算今日盈亏
                await self._update_daily_pnl(db, user)

                await db.commit()
            except Exception as e:
                logger.error(f"HostedEngine _scan_user({user_id}) 异常: {e}")
                await db.rollback()

    async def _update_daily_pnl(self, db: AsyncSession, user: User):
        """从 trades 表计算今日实际盈亏"""
        user_id = user.id
    async def _update_daily_pnl(self, db: AsyncSession, user: User):
        user_id = user.id
        from app.services.trading import get_or_create_account
        from app.models.trading import Position
        stmt = select(Position).where(Position.user_id == user_id)
        result = await db.execute(stmt)
        positions = result.scalars().all()
        market_value = sum(float(p.market_value) for p in positions)
        account_result = await get_or_create_account(db, user)
        current_equity = float(account_result["total_equity"]) if isinstance(account_result, dict) else float(account_result.total_equity)
        
        async with self._lock:
            if user_id in self._sessions:
                s = self._sessions[user_id]
                start_equity = s.get("daily_start_equity")
                if start_equity is None or s.get("daily_start_date") != str(date.today()):
                    s["daily_start_equity"] = current_equity
                    s["daily_start_date"] = str(date.today())
                    s["daily_pnl"] = 0.0
                    s["daily_pnl_pct"] = 0.0
                else:
                    daily_pnl = current_equity - start_equity
                    s["daily_pnl"] = daily_pnl
                    s["daily_pnl_pct"] = daily_pnl / start_equity if start_equity > 0 else 0.0

        async with self._lock:
            if user_id in self._sessions:
                self._sessions[user_id]["daily_pnl"] = daily_pnl
                self._sessions[user_id]["daily_pnl_pct"] = daily_pnl_pct

    # ── 卖出决策 ──

    async def _process_sell_signals(self, db: AsyncSession, user: User, diagnosis: dict):
        user_id = user.id
        for pos_diag in diagnosis.get("positions", []):
            action = pos_diag.get("action")
            if not action:
                continue
            action_type = action.get("action", "")
            if action_type not in ("reduce", "clear", "partial_sell"):
                continue
            confidence = pos_diag.get("confidence", 0)
            if abs(confidence) < SELL_CONFIDENCE_THRESHOLD:
                continue
            symbol = pos_diag.get("symbol", "")
            if not symbol:
                continue

            stmt = select(Position).where(
                Position.user_id == user_id,
                Position.symbol == symbol,
            )
            result = await db.execute(stmt)
            position = result.scalar_one_or_none()
            if position is None or position.available <= 0:
                continue

            available = position.available
            if action_type == "clear":
                sell_qty = available
            elif action_type == "partial_sell":
                sell_qty = max(100, available // 3)
                sell_qty = (sell_qty // 100) * 100
            else:
                sell_qty = max(100, available // 4)
                sell_qty = (sell_qty // 100) * 100

            if sell_qty < 100:
                continue

            try:
                order_req = OrderRequest(
                    symbol=symbol, side="sell", quantity=sell_qty, order_type="market",
                )
                fallback = float(position.market_price) if position.market_price > 0 else None
                order_result = await place_order(db, user, order_req, fallback_price=fallback)
                signal_id = f"sig_{user_id}_{symbol}_{int(datetime.now().timestamp())}"

                self._add_trade_log(
                    user_id,
                    signal_id=signal_id,
                    order_id=order_result.id if hasattr(order_result, "id") else None,
                    action="SELL",
                    symbol=symbol,
                    symbol_name=pos_diag.get("name", ""),
                    target_price=fallback,
                    qty=sell_qty,
                    reason=action.get("reason", "托管决策"),
                    status="TRIGGERED",
                )
                self._increment_signal(user_id)
                async with self._lock:
                    if user_id in self._sessions:
                        s = self._sessions[user_id]
                        s["total_trades"] += 1
                        s["total_triggered"] = s.get("total_triggered", 0) + 1
                        s["last_action"] = {
                            "type": "sell", "symbol": symbol, "quantity": sell_qty,
                            "action": action_type,
                            "time": datetime.now(timezone.utc).isoformat(),
                        }
                await db.commit()
            except Exception as e:
                logger.warning(f"HostedEngine 卖出 {symbol} 失败: {e}")
                await db.rollback()
                self._add_trade_log(
                    user_id,
                    signal_id=None,
                    order_id=None,
                    action="SELL",
                    symbol=symbol,
                    symbol_name=pos_diag.get("name", ""),
                    target_price=None,
                    qty=sell_qty,
                    reason=action.get("reason", "托管决策"),
                    status="ERROR",
                    error=str(e),
                )

    # ── 买入决策 ──

    async def _process_buy_signals(self, db: AsyncSession, user: User, diagnosis: dict):
        user_id = user.id
        summary = diagnosis.get("summary", {})
        market_temp = diagnosis.get("market_temperature", {})
        temp_score = market_temp.get("score", 0)

        if temp_score < BUY_MARKET_BULLISH_THRESHOLD:
            logger.info(f"HostedEngine user={user_id} 市场温度 {temp_score} 低于买入阈值，跳过买入")
            return

        cash_ratio = summary.get("cash_ratio", 0)
        if cash_ratio < BUY_CASH_RATIO_MIN:
            logger.info(f"HostedEngine user={user_id} 现金比例 {cash_ratio}% 不足，跳过买入")
            return

        # 获取已持仓股票
        stmt = select(Position).where(Position.user_id == user_id)
        result = await db.execute(stmt)
        positions = result.scalars().all()
        held_symbols = {p.symbol for p in positions}

        # 使用选股推荐服务获取买入候选
        config = self._sessions.get(user_id, {}).get("config", {})
        risk_mapping = {"conservative": "balanced", "balanced": "momentum", "aggressive": "momentum"}
        strategy = risk_mapping.get(config.get("risk_level", "balanced"), "momentum")

        buy_candidates = []
        try:
            req = RecommendRequest(strategy=strategy, top_n=20)
            rec_result = await recommend_stocks(req)
            # 过滤掉已持有的
            for pick in rec_result.picks:
                if pick.symbol not in held_symbols:
                    buy_candidates.append({
                        "symbol": pick.symbol,
                        "name": pick.name,
                        "score": pick.score,
                        "reason": "动量选股推荐",
                    })
        except Exception as e:
            logger.warning(f"HostedEngine 获取选股推荐失败: {e}，降级使用自选股")
            watchlist = config.get("watchlist", config.get("symbols", []))
            buy_candidates = [
                {"symbol": s, "name": s, "score": 0, "reason": "自选"}
                for s in watchlist if s.upper() not in held_symbols
            ]

        if not buy_candidates:
            logger.info(f"HostedEngine user={user_id} 无买入候选")
            return

        # 获取实时行情确认涨幅 > 0
        candidate_symbols = [c["symbol"] for c in buy_candidates[:10]]
        try:
            quotes = await fetch_realtime_quotes(candidate_symbols)
        except Exception as e:
            logger.warning(f"HostedEngine 获取候选行情失败: {e}")
            return

        # 合并推荐分数和行情
        quote_map = {q.symbol: q for q in quotes if q.change_pct is not None}
        ranked = []
        for c in buy_candidates:
            q = quote_map.get(c["symbol"])
            if q and q.change_pct > 0:
                # 综合排名 = 推荐分数 + 涨幅加权
                combined = c["score"] * 0.6 + q.change_pct * 0.4
                ranked.append((c, combined, q))

        if not ranked:
            logger.info(f"HostedEngine user={user_id} 无上涨候选")
            return

        # 按综合分数排序，买入得分最高的
        ranked.sort(key=lambda x: x[1], reverse=True)
        target_info, combined_score, quote = ranked[0]
        target_symbol = target_info["symbol"]

        total_equity = summary.get("total_equity", 0)
        if total_equity <= 0:
            return
        max_amount = total_equity * MAX_SINGLE_BUY_PCT / 100.0
        price = float(quote.price)
        quantity = int(max_amount / price // 100 * 100)
        if quantity < 100:
            return

        account = await get_or_create_account(db, user)
        estimate_cost = price * quantity * 1.0005
        if float(account.balance) < estimate_cost:
            logger.info(f"HostedEngine user={user_id} 余额不足：需 {estimate_cost}，可用 {account.balance}")
            return

        try:
            order_req = OrderRequest(
                symbol=target_symbol, side="buy", quantity=quantity, order_type="market",
            )
            order_result = await place_order(db, user, order_req)
            signal_id = f"sig_{user_id}_{target_symbol}_{int(datetime.now().timestamp())}"

            self._add_trade_log(
                user_id,
                signal_id=signal_id,
                order_id=order_result.id if hasattr(order_result, "id") else None,
                action="BUY",
                symbol=target_symbol,
                symbol_name=target_info.get("name", target_symbol),
                target_price=price,
                qty=quantity,
                reason=f"选股推荐 {target_info.get("reason", "")} (得分 {combined_score:.1f})，涨幅 {quote.change_pct}%，市场温度 {temp_score}",
                status="TRIGGERED",
            )
            self._increment_signal(user_id)
            async with self._lock:
                if user_id in self._sessions:
                    s = self._sessions[user_id]
                    s["total_trades"] += 1
                    s["total_triggered"] = s.get("total_triggered", 0) + 1
                    s["last_action"] = {
                        "type": "buy", "symbol": target_symbol, "quantity": quantity,
                        "price": price, "time": datetime.now(timezone.utc).isoformat(),
                    }
            await db.commit()
            logger.info(f"HostedEngine user={user_id} 自动买入 {target_symbol} {quantity}股")
        except Exception as e:
            logger.warning(f"HostedEngine 买入 {target_symbol} 失败: {e}")
            await db.rollback()
            self._add_trade_log(
                user_id,
                signal_id=None,
                order_id=None,
                action="BUY",
                symbol=target_symbol,
                symbol_name=target_info.get("name", target_symbol),
                target_price=price,
                qty=quantity,
                reason=target_info.get("reason", "选股推荐"),
                status="ERROR",
                error=str(e),
            )

    # ── 信号计数 ──

    def _increment_signal(self, user_id: int):
        async def _do():
            async with self._lock:
                if user_id in self._sessions:
                    self._sessions[user_id]["signals_today"] = self._sessions[user_id].get("signals_today", 0) + 1
        asyncio.create_task(_do())

    # ── 日志 ──

    def _add_log(self, user_id: int, level: str, message: str):
        entry = {
            "time": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "message": message,
        }
        if user_id not in self._logs:
            self._logs[user_id] = []
        self._logs[user_id].append(entry)
        logger.info(f"[HostedEngine user={user_id}] [{level}] {message}")

    def _add_trade_log(
        self,
        user_id: int,
        signal_id: Optional[str],
        order_id: Optional[int],
        action: str,
        symbol: str,
        symbol_name: str,
        target_price: Optional[float],
        qty: Optional[int],
        reason: Optional[str],
        status: str,
        error: Optional[str] = None,
    ):
        """结构化交易日志 + 持久化信号到 DB"""
        entry = {
            "time": datetime.now(timezone.utc).isoformat(),
            "level": "success" if status == "TRIGGERED" else "error",
            "message": f"[{action}] {symbol} {qty}股 — {reason}",
            "signal_id": signal_id,
            "order_id": order_id,
            "action": action,
            "symbol": symbol,
            "symbol_name": symbol_name,
            "target_price": target_price,
            "qty": qty,
            "reason": reason,
            "status": status,
            "error": error,
        }
        if user_id not in self._logs:
            self._logs[user_id] = []
        self._logs[user_id].append(entry)
        log_msg = f"[{action}] {symbol} {qty}股"
        if error:
            log_msg += f" 失败: {error}"
        logger.info(f"[HostedEngine user={user_id}] [{status}] {log_msg}")

        # 持久化信号到 DB
        if signal_id:
            asyncio.create_task(self._persist_signal(
                user_id=user_id,
                signal_id=signal_id,
                action=action,
                symbol=symbol,
                symbol_name=symbol_name,
                target_price=target_price,
                qty=qty,
                reason=reason,
                status=status,
                order_id=order_id,
                error=error,
            ))

    async def _persist_signal(
        self,
        user_id: int,
        signal_id: str,
        action: str,
        symbol: str,
        symbol_name: str = "",
        target_price: Optional[float] = None,
        qty: Optional[int] = None,
        reason: Optional[str] = None,
        status: str = "PENDING",
        order_id: Optional[int] = None,
        error: Optional[str] = None,
    ):
        """将信号持久化到 PostgreSQL"""
        try:
            from app.core.database import get_session_factory
            from app.models.signals import Signal
            from sqlalchemy.dialects.postgresql import insert

            factory = get_session_factory()
            async with factory() as db:
                stmt = insert(Signal).values(
                    user_id=user_id,
                    signal_id=signal_id,
                    action=action,
                    symbol=symbol,
                    symbol_name=symbol_name,
                    target_price=target_price,
                    qty=qty,
                    reason=reason,
                    status=status,
                    order_id=order_id,
                    error=error,
                )
                stmt = stmt.on_conflict_do_update(
                    index_elements=["signal_id"],
                    set_=dict(
                        status=status,
                        order_id=order_id,
                        error=error,
                    ),
                )
                await db.execute(stmt)
                await db.commit()
        except Exception as e:
            logger.warning(f"HostedEngine 信号持久化失败 signal={signal_id}: {e}")


engine = HostedEngine()
