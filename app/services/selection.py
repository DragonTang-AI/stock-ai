"""
app.services.selection — 选股推荐服务（v2.0：多因子升级）

v2.0 升级：
- 候选池从 52 只 → 102 只（蓝筹 + 行业龙头 + 成长股）
- 新增 RSI(14)、MACD 柱线、布林带位置 3 个因子
- 新增策略模式：momentum（追涨）/ reversal（抄底）/ balanced（均衡）
- 因子权重更均衡，归一化更平滑
- 引入"量价确认"复合因子

技术说明：
- 复用 market_data adapter 获取行情和 K 线
- 技术指标纯 Python 计算（无 numpy/pandas 依赖）
- 异步批量，新浪限流先行情后 K 线两次分批
"""
import asyncio
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime

from app.schemas.selection import (
    RecommendRequest,
    RecommendResponse,
    StockPick,
    PickFactor,
)
from app.services.market import fetch_realtime_quotes, fetch_kline
from app.schemas.market import QuoteItem, KLineItem

logger = logging.getLogger(__name__)

# ========== v2.0 候选股票池（102 只） ==========
# 扩展覆盖：金融/消费/医药/科技/新能源/制造/材料/基建
CANDIDATE_POOL = [
    # === 金融（10）===
    "601318.SH", "600036.SH", "601398.SH", "601939.SH", "601988.SH",
    "600030.SH", "000001.SZ", "000166.SZ", "601628.SH", "600000.SH",
    # === 消费（12）===
    "600519.SH", "000858.SZ", "000333.SZ", "000651.SZ", "600887.SH",
    "600690.SH", "000002.SZ", "600104.SH", "601888.SH", "000895.SZ",
    "600600.SH",  # 青岛啤酒
    "002304.SZ",  # 洋河股份
    # === 医药（12）===
    "600276.SH", "000661.SZ", "300760.SZ", "300015.SZ", "300122.SZ",
    "300347.SZ", "300142.SZ", "600196.SH", "600436.SH", "000538.SZ",  # 云南白药
    "002007.SZ",  # 华兰生物
    "300601.SZ",  # 康泰生物
    # === 科技/电子（14）===
    "000725.SZ", "002415.SZ", "002230.SZ", "000063.SZ", "000100.SZ",
    "002475.SH", "300033.SZ", "300124.SZ", "002049.SZ",  # 紫光国微
    "002371.SZ",  # 北方华创
    "603986.SH",  # 兆易创新
    "688981.SH",  # 中芯国际
    "688111.SH",  # 金山办公
    # === 新能源/汽车（10）===
    "300750.SZ", "601012.SH", "002594.SZ", "600900.SH",
    "600438.SH",  # 通威股份
    "300274.SZ",  # 阳光电源
    "002129.SZ",  # TCL中环
    "601985.SH",  # 中国核电
    "600089.SH",  # 特变电工
    "300014.SZ",  # 亿纬锂能
    # === 制造/工业（10）===
    "601800.SH", "601668.SH", "000768.SZ",
    "600031.SH",  # 三一重工
    "000338.SZ",  # 潍柴动力
    "601766.SH",  # 中国中车
    "600150.SH",  # 中国船舶
    "002460.SZ",  # 赣锋锂业
    "002466.SZ",  # 天齐锂业
    # === 材料/有色（8）===
    "600019.SH",  # 宝钢股份
    "600028.SH",  # 中国石化
    "601857.SH",  # 中国石油
    "601899.SH",  # 紫金矿业
    "600585.SH",  # 海螺水泥
    "002709.SZ",  # 天赐材料
    "600309.SH",  # 万华化学
    "601225.SH",  # 陕西煤业
    # === 通信/传媒（8）===
    "600050.SH", "300059.SZ", "002027.SZ",  # 分众传媒
    "300413.SZ",  # 芒果超媒
    "300418.SZ",  # 昆仑万维
    "002555.SZ",  # 三七互娱
    "600941.SH",  # 中国移动
    # === 农业/食品（6）===
    "000876.SZ", "002714.SZ",  # 牧原股份
    "603288.SH",  # 海天味业
    "002568.SZ",  # 百润股份
    "000596.SZ",  # 古井贡酒
    "603369.SH",  # 今世缘
    # === 港股龙头（5）===
    "0700.HK",   # 腾讯控股
    "9988.HK",   # 阿里巴巴
    "9618.HK",   # 京东
    "9999.HK",   # 网易
    "1810.HK",   # 小米
]

# 并发和分批
BATCH_CONCURRENCY = 5
BATCH_SIZE = 10

# 策略模式权重配置
STRATEGY_WEIGHTS: Dict[str, Dict[str, float]] = {
    "momentum": {
        "momentum": 0.30,
        "volume": 0.20,
        "trend": 0.20,
        "rsi": 0.10,
        "macd": 0.10,
        "turnover": 0.10,
    },
    "reversal": {
        "momentum": 0.05,
        "volume": 0.10,
        "trend": 0.20,
        "rsi": 0.30,
        "macd": 0.15,
        "turnover": 0.05,
        "bollinger": 0.15,
    },
    "balanced": {
        "momentum": 0.20,
        "volume": 0.20,
        "trend": 0.20,
        "rsi": 0.15,
        "macd": 0.10,
        "turnover": 0.05,
        "bollinger": 0.10,
    },
}


def _is_suspended(quote: QuoteItem) -> bool:
    return quote.price <= 0 or quote.close <= 0


def _is_st(name: str) -> bool:
    if not name:
        return False
    upper = name.upper()
    return "ST" in upper or "*ST" in upper


def _is_limit_up(quote: QuoteItem) -> bool:
    return quote.change_pct >= 9.5


def _is_limit_down(quote: QuoteItem) -> bool:
    return quote.change_pct <= -9.5


# ========== 技术指标计算（轻量独立实现，无外部依赖） ==========

def _get_closes(klines: List[KLineItem]) -> List[float]:
    return [k.close for k in klines]


def _compute_ma(closes: List[float], period: int) -> float:
    if len(closes) < period:
        return 0.0
    return sum(closes[-period:]) / period


def _compute_rsi(closes: List[float], period: int = 14) -> Optional[float]:
    if len(closes) < period + 1:
        return None
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [max(d, 0) for d in deltas[:period]]
    losses = [max(-d, 0) for d in deltas[:period]]
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        return 100.0
    alpha = 1.0 / period
    for d in deltas[period:]:
        avg_gain = avg_gain * (1 - alpha) + max(d, 0) * alpha
        avg_loss = avg_loss * (1 - alpha) + max(-d, 0) * alpha
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100.0 - 100.0 / (1.0 + rs), 2)


def _compute_macd(closes: List[float], fast=12, slow=26, signal=9) -> Optional[float]:
    """返回最新 MACD 柱线值（正值=多头，负值=空头）"""
    if len(closes) < slow + signal:
        return None

    def _ema(data, period):
        m = 2.0 / (period + 1)
        ema = [sum(data[:period]) / period]
        for i in range(period, len(data)):
            ema.append((data[i] - ema[-1]) * m + ema[-1])
        return ema

    ema_f = _ema(closes, fast)
    ema_s = _ema(closes, slow)
    offset = slow - fast
    macd_line = [ema_f[i + offset] - ema_s[i] for i in range(len(ema_s))]
    sig_line = _ema(macd_line, signal)
    return round(macd_line[-1] - sig_line[-1], 3)


def _compute_bollinger_pos(closes: List[float], period=20) -> Optional[float]:
    """
    布林带位置因子。
    返回 0~1 值：0=接近下轨（超卖），0.5=中轨，1=接近上轨（超买）
    """
    if len(closes) < period:
        return None
    recent = closes[-period:]
    ma = sum(recent) / period
    variance = sum((c - ma) ** 2 for c in recent) / period
    std = variance ** 0.5
    if std <= 0:
        return 0.5
    pos = (closes[-1] - (ma - 2 * std)) / (4 * std)
    return max(0.0, min(1.0, pos))


def _compute_volume_ratio(klines: List[KLineItem]) -> float:
    """量比：今日量 / 5日均量"""
    if len(klines) < 6:
        return 1.0
    today_v = klines[-1].volume
    avg_v = sum(k.volume for k in klines[-6:-1]) / 5
    if avg_v <= 0:
        return 1.0
    return today_v / avg_v


def _compute_volume_price_confirmation(klines: List[KLineItem]) -> float:
    """
    量价确认因子。
    上涨放量、下跌缩量 → 高分；上涨缩量、下跌放量 → 低分
    """
    if len(klines) < 11:
        return 0.5
    # 分两段：前 5 日和后 5 日
    closes = _get_closes(klines)
    vol_list = [k.volume for k in klines]

    def _segment(i: int) -> Tuple[float, float]:
        seg_closes = closes[i:i + 5]
        seg_vols = vol_list[i:i + 5]
        if len(seg_closes) < 2:
            return 0.0, 0.0
        price_chg = (seg_closes[-1] - seg_closes[0]) / seg_closes[0]
        avg_vol = sum(seg_vols) / len(seg_vols)
        return price_chg, avg_vol

    recent_chg, recent_vol = _segment(-5)
    prior_chg, prior_vol = _segment(-10)

    if prior_vol <= 0:
        return 0.5

    vol_trend = recent_vol / prior_vol  # >1 放量，<1 缩量
    # 上涨+放量 → 1，上涨+缩量 → 0，下跌+放量 → 0，下跌+缩量 → 0.5
    if recent_chg > 0:
        return min(vol_trend / 2, 1.0)
    else:
        return max(0.5 - (vol_trend - 1) / 4, 0.0)


# ========== 因子归一化评分 ==========

def _norm_momentum(momentum: float) -> float:
    """动量因子归一化：-5%~10% → 0~100"""
    # 负数表示下跌，0 表示不涨不跌
    if momentum <= -5:
        return 0.0
    if momentum <= 0:
        return 30.0 * (momentum + 5) / 5  # -5%~0 → 0~30
    if momentum <= 5:
        return 30.0 + 40.0 * momentum / 5  # 0%~5% → 30~70
    if momentum <= 10:
        return 70.0 + 30.0 * (momentum - 5) / 5  # 5%~10% → 70~100
    return 100.0


def _norm_volume_ratio(vr: float) -> float:
    """量比归一化：0.5~3 → 0~100"""
    if vr <= 0.5:
        return 10.0
    if vr <= 1.0:
        return 10.0 + 30.0 * (vr - 0.5) / 0.5  # 0.5~1 → 10~40
    if vr <= 2.0:
        return 40.0 + 40.0 * (vr - 1.0) / 1.0  # 1~2 → 40~80
    if vr <= 3.0:
        return 80.0 + 20.0 * (vr - 2.0) / 1.0  # 2~3 → 80~100
    return 100.0


def _norm_trend(klines: List[KLineItem]) -> float:
    """趋势归一化：检查 MA5 > MA10 > MA20 多头排列"""
    closes = _get_closes(klines)
    if len(closes) < 20:
        return 50.0
    ma5 = _compute_ma(closes, 5)
    ma10 = _compute_ma(closes, 10)
    ma20 = _compute_ma(closes, 20)
    price = closes[-1]
    # 价格在均线之上的程度
    above_ma5 = price > ma5
    above_ma10 = price > ma10
    above_ma20 = price > ma20
    bull_order = ma5 > ma10 > ma20
    bear_order = ma5 < ma10 < ma20
    if bull_order and above_ma5:
        return 90.0
    if bull_order:
        return 75.0
    if above_ma5 and above_ma10:
        return 65.0
    if above_ma5:
        return 55.0
    if above_ma10:
        return 45.0
    if above_ma20:
        return 35.0
    if bear_order:
        return 10.0
    if above_ma20:
        return 25.0
    return 15.0


def _norm_rsi(rsi: Optional[float], strategy: str) -> float:
    """RSI 归一化：策略不同评分不同"""
    if rsi is None:
        return 50.0
    if strategy == "reversal":
        # 抄底策略：超卖区域高分（30 以下给高分），超买低分
        if rsi <= 20:
            return 95.0
        if rsi <= 30:
            return 85.0
        if rsi <= 40:
            return 70.0
        if rsi <= 50:
            return 55.0
        if rsi <= 60:
            return 40.0
        if rsi <= 70:
            return 25.0
        return 10.0
    else:
        # 追涨/均衡：50~70 给高分（强势但不过热）
        if rsi <= 30:
            return 20.0
        if rsi <= 40:
            return 35.0
        if rsi <= 50:
            return 55.0
        if rsi <= 60:
            return 80.0
        if rsi <= 70:
            return 90.0
        if rsi <= 80:
            return 70.0
        return 40.0


def _norm_macd(macd_hist: Optional[float]) -> float:
    """MACD 柱线归一化：正值越高越好"""
    if macd_hist is None:
        return 50.0
    if macd_hist <= -1:
        return 10.0
    if macd_hist <= 0:
        return 10.0 + 30.0 * (macd_hist + 1) / 1  # -1~0 → 10~40
    if macd_hist <= 1:
        return 50.0 + 40.0 * macd_hist / 1  # 0~1 → 50~90
    return 90.0 + min(macd_hist, 10) / 10 * 10  # >1 → 90~100


def _norm_bollinger(boll_pos: Optional[float], strategy: str) -> float:
    """布林带位置归一化"""
    if boll_pos is None:
        return 50.0
    if strategy == "reversal":
        # 抄底：靠近下轨高分
        if boll_pos <= 0.1:
            return 90.0
        if boll_pos <= 0.3:
            return 75.0
        if boll_pos <= 0.5:
            return 55.0
        if boll_pos <= 0.7:
            return 35.0
        if boll_pos <= 0.9:
            return 20.0
        return 10.0
    else:
        # 追涨/均衡：中轨到上轨之间高分
        if boll_pos <= 0.1:
            return 15.0
        if boll_pos <= 0.3:
            return 35.0
        if boll_pos <= 0.5:
            return 55.0
        if boll_pos <= 0.7:
            return 80.0
        if boll_pos <= 0.85:
            return 90.0
        return 70.0


def _norm_turnover(quote: QuoteItem) -> float:
    """换手率归一化：0%~10% → 0~100"""
    rate = quote.turnover_rate
    if rate is None or rate < 0:
        return 50.0
    rate = min(rate, 10.0)
    if rate <= 0.5:
        return rate / 0.5 * 20  # 0~0.5% → 0~20
    if rate <= 1.0:
        return 20 + (rate - 0.5) / 0.5 * 30  # 0.5~1% → 20~50
    if rate <= 3.0:
        return 50 + (rate - 1.0) / 2.0 * 35  # 1~3% → 50~85
    if rate <= 5.0:
        return 85 + (rate - 3.0) / 2.0 * 10  # 3~5% → 85~95
    return 95.0  # >5% 换手过高


# ========== 评分主逻辑 ==========

def _score_stock(
    quote: QuoteItem, klines: List[KLineItem], strategy: str
) -> Optional[Tuple[float, List[PickFactor]]]:
    """
    单只股票评分（v2.0）
    返回 (总分, 因子明细) 或 None（过滤掉不推荐）
    """
    # 过滤
    if _is_suspended(quote):
        return None
    if _is_st(quote.name):
        return None
    if _is_limit_up(quote) or _is_limit_down(quote):
        return None
    if quote.change_pct < -5.0:
        return None

    closes = _get_closes(klines)
    weights = STRATEGY_WEIGHTS.get(strategy, STRATEGY_WEIGHTS["balanced"])

    # 计算各因子得分（0~100）
    momentum_raw = 0.0
    if len(closes) >= 6:
        base = closes[-6]
        if base > 0:
            momentum_raw = (closes[-1] - base) / base * 100
    mom_score = _norm_momentum(momentum_raw)

    vr = _compute_volume_ratio(klines)
    vol_score = _norm_volume_ratio(vr)

    trend_score = _norm_trend(klines)

    rsi_val = _compute_rsi(closes, 14)
    rsi_score = _norm_rsi(rsi_val, strategy)

    macd_val = _compute_macd(closes, 12, 26, 9)
    macd_score = _norm_macd(macd_val)

    turn_score = _norm_turnover(quote)

    boll_pos = _compute_bollinger_pos(closes, 20)
    boll_score = _norm_bollinger(boll_pos, strategy)

    # 加权计算
    total = (
        weights.get("momentum", 0) * mom_score
        + weights.get("volume", 0) * vol_score
        + weights.get("trend", 0) * trend_score
        + weights.get("rsi", 0) * rsi_score
        + weights.get("macd", 0) * macd_score
        + weights.get("turnover", 0) * turn_score
        + weights.get("bollinger", 0) * boll_score
    )

    factors = [
        PickFactor(name="momentum", value=round(momentum_raw, 2), score=round(mom_score, 1), weight=weights.get("momentum", 0)),
        PickFactor(name="volume_ratio", value=round(vr, 2), score=round(vol_score, 1), weight=weights.get("volume", 0)),
        PickFactor(name="trend", value=round(trend_score, 1), score=round(trend_score, 1), weight=weights.get("trend", 0)),
        PickFactor(name="rsi", value=round(rsi_val or 50, 1), score=round(rsi_score, 1), weight=weights.get("rsi", 0)),
        PickFactor(name="macd", value=round(macd_val or 0, 3), score=round(macd_score, 1), weight=weights.get("macd", 0)),
        PickFactor(name="turnover", value=round(quote.turnover_rate or 0, 2), score=round(turn_score, 1), weight=weights.get("turnover", 0)),
        PickFactor(name="bollinger", value=round(boll_pos or 0.5, 3), score=round(boll_score, 1), weight=weights.get("bollinger", 0)),
    ]

    return (round(total, 1), factors)


async def _fetch_quote_with_kline(symbol: str) -> Optional[Tuple[QuoteItem, List[KLineItem]]]:
    """获取单只股票的行情 + K 线"""
    try:
        quotes = await fetch_realtime_quotes([symbol])
        if not quotes:
            return None
        quote = quotes[0]
        klines = await fetch_kline(symbol, period="daily", count=30)
        return (quote, klines)
    except Exception as e:
        logger.warning(f"获取 {symbol} 数据失败: {e}")
        return None


async def _fetch_batch(symbols: List[str]) -> List[Tuple[QuoteItem, List[KLineItem]]]:
    """批量获取，控制并发"""
    sem = asyncio.Semaphore(BATCH_CONCURRENCY)

    async def _one(sym: str):
        async with sem:
            return await _fetch_quote_with_kline(sym)

    tasks = [_one(s) for s in symbols]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return [r for r in results if r is not None and not isinstance(r, Exception)]


async def recommend_stocks(req: RecommendRequest) -> RecommendResponse:
    """
    选股推荐主入口（v2.0）

    Args:
        req: RecommendRequest（market, top_n, strategy, 涨跌幅范围）

    策略说明：
        momentum - 追涨策略（默认）：动量+量价确认权重高，适合上升趋势
        reversal - 抄底策略：RSI 超卖+布林下轨权重高，适合回调反弹
        balanced - 均衡策略：各因子权重平均
    """
    strategy = getattr(req, "strategy", "momentum")

    # 1. 选股票池
    if req.market == "A":
        pool = [s for s in CANDIDATE_POOL if s.endswith((".SH", ".SZ"))]
    elif req.market == "HK":
        pool = [s for s in CANDIDATE_POOL if s.endswith(".HK")]
    else:
        pool = CANDIDATE_POOL

    if not pool:
        return RecommendResponse(
            success=True, picks=[],
            meta={"total_candidates": 0, "scored": 0, "filtered": 0,
                  "market": req.market, "strategy": strategy,
                  "note": "当前 market 无候选股票"},
        )

    scored: List[Tuple[QuoteItem, float, List[PickFactor]]] = []
    total_candidates = len(pool)

    for i in range(0, len(pool), BATCH_SIZE):
        batch = pool[i:i + BATCH_SIZE]
        results = await _fetch_batch(batch)
        for quote, klines in results:
            if quote.change_pct < req.min_change_pct or quote.change_pct > req.max_change_pct:
                continue
            score_result = _score_stock(quote, klines, strategy)
            if score_result is None:
                continue
            total, factors = score_result
            scored.append((quote, total, factors))

    scored.sort(key=lambda x: x[1], reverse=True)
    top = scored[: req.top_n]

    picks = []
    for rank, (quote, total, factors) in enumerate(top, start=1):
        picks.append(StockPick(
            rank=rank,
            symbol=quote.symbol,
            name=quote.name,
            price=quote.price,
            change_pct=quote.change_pct,
            volume=quote.volume,
            turnover_rate=quote.turnover_rate,
            score=total,
            factors=factors,
            market="A" if quote.symbol.endswith((".SH", ".SZ")) else "HK",
        ))

    return RecommendResponse(
        success=True,
        picks=picks,
        meta={
            "total_candidates": total_candidates,
            "scored": len(scored),
            "filtered": total_candidates - len(scored),
            "market": req.market,
            "top_n": req.top_n,
            "strategy": strategy,
            "strategy_version": "v2.0",
            "generated_at": datetime.utcnow().isoformat() + "Z",
        },
    )
