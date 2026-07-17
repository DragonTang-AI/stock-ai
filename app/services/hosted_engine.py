"""
app.services.hosted_engine — AI托管调度引擎

后台 asyncio 循环，每 60 秒扫描活跃托管用户：
1. 获取持仓诊断
2. 对符合条件的信号自动下单（卖出优先）
3. 在市场偏多且有现金时扫描自选股买入机会
"""
import logging
import asyncio
from typing import Dict, Optional
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_session_factory
from app.models.user import User
from app.models.trading import Position
from app.services.advisor import diagnose_portfolio
from app.services.trading import place_order, get_or_create_account
from app.services.market import fetch_realtime_quotes
from app.schemas.trading import OrderRequest

logger = logging.getLogger(__name__)

# 托管决策阈值（保守策略）
SELL_CONFIDENCE_THRESHOLD = 40
BUY_MARKET_BULLISH_THRESHOLD = 30
BUY_CASH_RATIO_MIN = 20.0
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
            }
            self._sessions[user_id] = session
            if user_id not in self._logs:
                self._logs[user_id] = []
            self._add_log(user_id, "success", "AI托管已开启")
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

                await self._process_sell_signals(db, user, diagnosis)
                await self._process_buy_signals(db, user, diagnosis)
                await db.commit()
            except Exception as e:
                logger.error(f"HostedEngine _scan_user({user_id}) 异常: {e}")
                await db.rollback()

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
                await place_order(db, user, order_req, fallback_price=fallback)
                self._add_log(
                    user_id, "success",
                    f"自动卖出 {symbol} {sell_qty}股 ({action_type})，"
                    f"原因: {action.get('reason', '托管决策')}",
                )
                async with self._lock:
                    if user_id in self._sessions:
                        self._sessions[user_id]["total_trades"] += 1
                        self._sessions[user_id]["last_action"] = {
                            "type": "sell", "symbol": symbol, "quantity": sell_qty,
                            "action": action_type,
                            "time": datetime.now(timezone.utc).isoformat(),
                        }
                await db.commit()
            except Exception as e:
                logger.warning(f"HostedEngine 卖出 {symbol} 失败: {e}")
                await db.rollback()

    # ── 买入决策 ──

    async def _process_buy_signals(self, db: AsyncSession, user: User, diagnosis: dict):
        user_id = user.id
        summary = diagnosis.get("summary", {})
        market_temp = diagnosis.get("market_temperature", {})
        temp_score = market_temp.get("score", 0)

        if temp_score < BUY_MARKET_BULLISH_THRESHOLD:
            return

        cash_ratio = summary.get("cash_ratio", 0)
        if cash_ratio < BUY_CASH_RATIO_MIN:
            return

        config = self._sessions.get(user_id, {}).get("config", {})
        watchlist = config.get("watchlist", config.get("symbols", []))
        if not watchlist:
            return

        stmt = select(Position).where(Position.user_id == user_id)
        result = await db.execute(stmt)
        positions = result.scalars().all()
        held_symbols = {p.symbol for p in positions}

        candidates = [s for s in watchlist if s.upper() not in held_symbols]
        if not candidates:
            return

        candidates = candidates[:5]
        try:
            quotes = await fetch_realtime_quotes(candidates)
        except Exception as e:
            logger.warning(f"HostedEngine 获取候选行情失败: {e}")
            return

        buyable = [q for q in quotes if q.change_pct is not None and q.change_pct > 0]
        if not buyable:
            return

        buyable.sort(key=lambda q: q.change_pct)
        target = buyable[0]

        total_equity = summary.get("total_equity", 0)
        if total_equity <= 0:
            return
        max_amount = total_equity * MAX_SINGLE_BUY_PCT / 100.0
        price = float(target.price)
        quantity = int(max_amount / price // 100 * 100)
        if quantity < 100:
            return

        account = await get_or_create_account(db, user)
        estimate_cost = price * quantity * 1.0005
        if float(account.balance) < estimate_cost:
            return

        try:
            order_req = OrderRequest(
                symbol=target.symbol, side="buy", quantity=quantity, order_type="market",
            )
            await place_order(db, user, order_req)
            self._add_log(
                user_id, "success",
                f"自动买入 {target.symbol} {quantity}股 @{price}，"
                f"涨幅 {target.change_pct}%，市场温度 {temp_score}",
            )
            async with self._lock:
                if user_id in self._sessions:
                    self._sessions[user_id]["total_trades"] += 1
                    self._sessions[user_id]["last_action"] = {
                        "type": "buy", "symbol": target.symbol, "quantity": quantity,
                        "price": price, "time": datetime.now(timezone.utc).isoformat(),
                    }
            await db.commit()
        except Exception as e:
            logger.warning(f"HostedEngine 买入 {target.symbol} 失败: {e}")
            await db.rollback()

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


engine = HostedEngine()
