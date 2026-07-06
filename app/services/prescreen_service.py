"""app/services/prescreen_service.py — Prescreen 服务层"""
import logging
from datetime import date, datetime
from app.schemas.prescreen import PrescreenResponse
from app.selection.prescreen import run_prescreen
from app.services.market import fetch_realtime_quotes

logger = logging.getLogger(__name__)

# A股候选池（102只，覆盖主要板块）
A_STOCK_POOL = [
    "600519.SH","000858.SH","600036.SH","601318.SH","600900.SH","600028.SH",
    "601398.SH","601288.SH","601988.SH","601088.SH","601166.SH","600016.SH",
    "601328.SH","601818.SH","600837.SH","601601.SH","600030.SH","600050.SH",
    "600276.SH","000001.SZ","000002.SZ","000333.SZ","000651.SZ","000876.SZ",
    "000568.SZ","000725.SZ","000768.SZ","002594.SZ","002415.SZ","002460.SZ",
    "002475.SZ","002371.SZ","002230.SZ","300059.SZ","300750.SZ","300015.SZ",
    "300122.SZ","300274.SZ","300124.SZ","300142.SZ","300033.SZ","300014.SZ",
    "300347.SZ","300760.SZ","300496.SZ","300666.SZ","300782.SZ","300474.SZ",
    "300601.SZ","300529.SZ","688041.SH","688012.SH","688111.SH","688036.SH",
    "688185.SH","688981.SH","688599.SH","688126.SH","688008.SH","688009.SH",
    "688188.SH","688256.SH","688048.SH","688065.SH","688396.SH","688521.SH",
    "688339.SH","688005.SH","688180.SH","688390.SH","688561.SH","688766.SH",
    "688223.SH","688187.SH","688169.SH","688071.SH","688117.SH","688026.SH",
    "688167.SH","688019.SH","688063.SH","688116.SH","688289.SH","688208.SH",
    "688220.SH","688099.SH","688158.SH","688399.SH","688018.SH","688006.SH",
    "301071.SZ","301099.SZ","301050.SZ","301056.SZ","301072.SZ","301080.SZ",
    "301088.SZ","301103.SZ","301138.SZ","301269.SZ","301368.SZ","301369.SZ",
    "301378.SZ","301558.SZ",
]

# 扩展池（增加覆盖）
EXTENDED_POOL = [
    "600150.SH","600160.SH","600309.SH","600585.SH","600547.SH","600690.SH",
    "600809.SH","603259.SH","603288.SH","603605.SH","603501.SH","603799.SH",
    "603986.SH","603712.SH","603260.SH","603288.SH","002304.SZ","002714.SZ",
    "002607.SZ","002352.SZ","002049.SZ","002466.SZ","002459.SZ","002027.SZ",
    "002241.SZ","002624.SZ","300223.SZ","300274.SZ","300450.SZ","300496.SZ",
]


async def get_prescreen_candidates(
    market: str = "A",
    trade_date: date | None = None,
    limit: int = 20,
) -> PrescreenResponse:
    """
    获取粗筛候选股票列表。
    
    基于实时行情数据，计算动量+量比评分，输出 Top N。
    """
    effective_date = trade_date or date.today()
    trade_date_str = effective_date.strftime("%Y-%m-%d")

    pool = A_STOCK_POOL + EXTENDED_POOL
    effective_limit = max(1, min(limit, 50))

    try:
        raw = await fetch_realtime_quotes(pool)
    except Exception as e:
        logger.warning(f"Prescreen fetch_quotes failed: {e}, falling back to empty")
        raw = []

    # QuoteItem → dict（兼容 Pydantic 模型）
    stocks = []
    for item in raw:
        if hasattr(item, "model_dump"):
            stocks.append(item.model_dump())
        elif hasattr(item, "dict"):
            stocks.append(item.dict())
        else:
            stocks.append(item)

    candidates = run_prescreen(
        stocks,
        market=market,
        trade_date=trade_date_str,
        limit=effective_limit,
    )

    return PrescreenResponse(
        market=market,
        trade_date=trade_date_str,
        pool_size=len(pool),
        candidates=candidates,
    )
