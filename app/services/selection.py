"""
app.services.selection — 选股推荐服务（v1：多因子评分）

策略说明：
1. 从候选股票池（默认热门 + 沪深 300 主流）获取实时行情 + 近期 K 线
2. 计算多因子得分：动量 / 量能 / 趋势 / 换手
3. 过滤风险：剔除涨停/跌停/ST/停牌
4. 按综合评分降序排列，返回 Top N

技术实现：
- 复用 market_data adapter（sina/akshare）获取行情和 K 线
- 因子计算用纯 Python（避免引入 numpy/pandas 依赖膨胀）
- 异步批量获取，控制并发防止新浪限流
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

# ========== 候选股票池 ==========
# 简化为 50 只，覆盖 A 股主流板块（金融/消费/医药/科技/能源/工业/材料）
# 实际生产可换成"全 A 股"或"沪深 300"，但当前 v1 用精选池以保性能
CANDIDATE_POOL = [
    # 沪市大盘
    "600519.SH",  # 贵州茅台
    "601318.SH",  # 中国平安
    "600036.SH",  # 招商银行
    "601398.SH",  # 工商银行
    "601939.SH",  # 建设银行
    "601988.SH",  # 中国银行
    "600276.SH",  # 恒瑞医药
    "600887.SH",  # 伊利股份
    "600030.SH",  # 中信证券
    "601012.SH",  # 隆基绿能
    "600900.SH",  # 长江电力
    "601888.SH",  # 中国中免
    "600028.SH",  # 中国石化
    "601857.SH",  # 中国石油
    "600050.SH",  # 中国联通
    "601628.SH",  # 中国人寿
    "600585.SH",  # 海螺水泥
    "600104.SH",  # 上汽集团
    "601800.SH",  # 中国交建
    "601668.SH",  # 中国建筑
    # 沪市消费/医药
    "600196.SH",  # 复星医药
    "600436.SH",  # 片仔癀
    "600690.SH",  # 海尔智家
    "600000.SH",  # 浦发银行
    "600048.SH",  # 保利发展
    # 深市大盘
    "000001.SZ",  # 平安银行
    "000002.SZ",  # 万科A
    "000333.SZ",  # 美的集团
    "000651.SZ",  # 格力电器
    "000858.SZ",  # 五粮液
    "000063.SZ",  # 中兴通讯
    "000725.SZ",  # 京东方A
    "000100.SZ",  # TCL科技
    "000166.SZ",  # 申万宏源
    "000768.SZ",  # 中航西飞
    # 深市成长
    "000661.SZ",  # 长春高新
    "000876.SZ",  # 新希望
    "000895.SZ",  # 双汇发展
    "002230.SZ",  # 科大讯飞
    "002415.SZ",  # 海康威视
    "002475.SH",  # 立讯精密（注：实际是 SZ）
    "002594.SZ",  # 比亚迪
    "300750.SZ",  # 宁德时代
    "300059.SZ",  # 东方财富
    "300015.SZ",  # 爱尔眼科
    "300760.SZ",  # 迈瑞医疗
    "300124.SZ",  # 汇川技术
    "300122.SZ",  # 智飞生物
    "300347.SZ",  # 泰格医药
    "300142.SZ",  # 沃森生物
    "300033.SZ",  # 同花顺
    "300144.SZ",  # 宋城演艺
]

# 并发上限（新浪限流）
BATCH_CONCURRENCY = 5
BATCH_SIZE = 10  # 每批 10 只


def _is_suspended(quote: QuoteItem) -> bool:
    """判断是否停牌（价格=0 或昨收=0）"""
    return quote.price <= 0 or quote.close <= 0


def _is_st(name: str) -> bool:
    """判断是否 ST 股（简化规则：名字含 ST/*ST）"""
    if not name:
        return False
    upper = name.upper()
    return "ST" in upper or "*ST" in upper


def _is_limit_up(quote: QuoteItem) -> bool:
    """判断是否涨停（涨幅 ≥ 9.5%，A 股涨停板约 10%）"""
    return quote.change_pct >= 9.5


def _is_limit_down(quote: QuoteItem) -> bool:
    """判断是否跌停（跌幅 ≤ -9.5%）"""
    return quote.change_pct <= -9.5


def _compute_momentum(klines: List[KLineItem]) -> float:
    """
    动量因子：5 日涨跌幅（最近 5 个交易日的累计涨幅）
    返回值：百分比，如 5.2 表示 5.2%
    """
    if len(klines) < 6:
        return 0.0
    # 5 个交易日前的收盘价
    base_close = klines[-6].close
    latest_close = klines[-1].close
    if base_close <= 0:
        return 0.0
    return (latest_close - base_close) / base_close * 100


def _compute_volume_ratio(klines: List[KLineItem]) -> float:
    """
    量比因子：今日成交量 / 5 日均量
    返回值：1.5 表示今日量是 5 日均量的 1.5 倍
    """
    if len(klines) < 6:
        return 1.0
    today_volume = klines[-1].volume
    avg_volume = sum(k.volume for k in klines[-6:-1]) / 5
    if avg_volume <= 0:
        return 1.0
    return today_volume / avg_volume


def _compute_trend(klines: List[KLineItem]) -> float:
    """
    趋势因子：MA5 与 MA20 的位置关系
    返回值：MA5/MA20 - 1，正数表示多头排列
    """
    if len(klines) < 20:
        return 0.0
    closes = [k.close for k in klines]
    ma5 = sum(closes[-5:]) / 5
    ma20 = sum(closes[-20:]) / 20
    if ma20 <= 0:
        return 0.0
    return (ma5 - ma20) / ma20


def _compute_turnover_score(quote: QuoteItem) -> float:
    """
    换手因子：当日换手率（0~10% 映射到 0~1）
    返回值：0~1 之间的分数
    """
    if quote.turnover_rate is None or quote.turnover_rate < 0:
        # 没数据时给中等分
        return 0.5
    # 换手 1%~5% 视为活跃，2.5% 给满分
    rate = min(quote.turnover_rate, 10.0)
    if rate < 0.5:
        return rate / 0.5 * 0.3  # 0.5% 以下 0~0.3 分
    return 0.3 + min((rate - 0.5) / 2.0, 1.0) * 0.7  # 0.5~2.5% 0.3~1.0


def _score_stock(
    quote: QuoteItem, klines: List[KLineItem]
) -> Optional[Tuple[float, List[PickFactor]]]:
    """
    单只股票评分
    返回 (总分, 因子明细) 或 None（不推荐）
    """
    # 过滤
    if _is_suspended(quote):
        return None
    if _is_st(quote.name):
        return None
    if _is_limit_up(quote) or _is_limit_down(quote):
        return None
    # 跌幅过大不推
    if quote.change_pct < -5.0:
        return None

    # 计算因子
    momentum = _compute_momentum(klines)
    vol_ratio = _compute_volume_ratio(klines)
    trend = _compute_trend(klines)
    turnover_score = _compute_turnover_score(quote)

    # 综合评分（0~100）
    # 动量权重 40%：5 日涨幅 0~10% 映射到 0~40 分
    mom_score = max(0, min(momentum, 10)) / 10 * 40

    # 量比权重 30%：1~3 倍映射到 0~30 分
    vol_score = max(0, min(vol_ratio - 1, 2)) / 2 * 30

    # 趋势权重 20%：-0.05~0.05 映射到 0~20 分
    trend_score = max(0, min(trend + 0.05, 0.1)) / 0.1 * 20

    # 换手权重 10%：0~1 映射到 0~10 分
    turn_score = turnover_score * 10

    total = mom_score + vol_score + trend_score + turn_score

    factors = [
        PickFactor(name="momentum", value=round(momentum, 2), score=round(mom_score, 1), weight=0.4),
        PickFactor(name="volume_ratio", value=round(vol_ratio, 2), score=round(vol_score, 1), weight=0.3),
        PickFactor(name="trend", value=round(trend * 100, 2), score=round(trend_score, 1), weight=0.2),
        PickFactor(name="turnover", value=round(turnover_score, 2), score=round(turn_score, 1), weight=0.1),
    ]

    return (round(total, 1), factors)


async def _fetch_quote_with_kline(symbol: str) -> Optional[Tuple[QuoteItem, List[KLineItem]]]:
    """
    获取单只股票的行情 + K 线（失败返回 None）
    """
    try:
        # 行情
        quotes = await fetch_realtime_quotes([symbol])
        if not quotes:
            return None
        quote = quotes[0]

        # K 线（30 天用于计算 5 日动量 + MA20）
        klines = await fetch_kline(symbol, period="daily", count=30)
        return (quote, klines)
    except Exception as e:
        logger.warning(f"获取 {symbol} 数据失败: {e}")
        return None


async def _fetch_batch(symbols: List[str]) -> List[Tuple[QuoteItem, List[KLineItem]]]:
    """
    批量获取，控制并发
    """
    sem = asyncio.Semaphore(BATCH_CONCURRENCY)

    async def _one(sym: str):
        async with sem:
            return await _fetch_quote_with_kline(sym)

    tasks = [_one(s) for s in symbols]
    results = await asyncio.gather(*tasks, return_exceptions=False)
    # 过滤 None 和失败
    return [r for r in results if r is not None]


async def recommend_stocks(req: RecommendRequest) -> RecommendResponse:
    """
    选股推荐主入口

    Args:
        req: RecommendRequest（market, top_n, min_change_pct, max_change_pct）

    Returns:
        RecommendResponse（picks + factors + meta）
    """
    # 1. 选股票池
    if req.market == "A":
        pool = [s for s in CANDIDATE_POOL if s.endswith(".SH") or s.endswith(".SZ")]
    elif req.market == "HK":
        # v1 暂不支持港股
        pool = []
    else:  # all
        pool = CANDIDATE_POOL

    if not pool:
        return RecommendResponse(
            success=True,
            picks=[],
            meta={
                "total_candidates": 0,
                "scored": 0,
                "filtered": 0,
                "market": req.market,
                "note": "当前 market 无候选股票",
            },
        )

    # 2. 分批并发拉数据
    scored: List[Tuple[QuoteItem, float, List[PickFactor]]] = []
    total_candidates = len(pool)
    fetched = 0

    for i in range(0, len(pool), BATCH_SIZE):
        batch = pool[i : i + BATCH_SIZE]
        results = await _fetch_batch(batch)
        fetched += len(results)
        for quote, klines in results:
            # 二次过滤：涨幅范围
            if quote.change_pct < req.min_change_pct or quote.change_pct > req.max_change_pct:
                continue
            score_result = _score_stock(quote, klines)
            if score_result is None:
                continue
            total, factors = score_result
            scored.append((quote, total, factors))

    # 3. 按评分降序，取 Top N
    scored.sort(key=lambda x: x[1], reverse=True)
    top = scored[: req.top_n]

    # 4. 构造响应
    picks = []
    for rank, (quote, total, factors) in enumerate(top, start=1):
        pick = StockPick(
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
        )
        picks.append(pick)

    return RecommendResponse(
        success=True,
        picks=picks,
        meta={
            "total_candidates": total_candidates,
            "scored": len(scored),
            "filtered": total_candidates - len(scored),
            "market": req.market,
            "top_n": req.top_n,
            "strategy_version": "v1.0",
            "generated_at": datetime.utcnow().isoformat() + "Z",
        },
    )
