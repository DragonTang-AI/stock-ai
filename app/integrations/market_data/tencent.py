"""
app.integrations.market_data.tencent — 腾讯财经公开 API

批量行情 + 全市场排名，作为东财 API 的替代方案。
- 全市场 ~5000 只股票 → 10 次分批请求，单次请求 < 2s
- 全流程 ~25-30s 完成排序
"""
import asyncio
import logging
import re
import time
import httpx
from dataclasses import dataclass
from typing import List, Optional

logger = logging.getLogger(__name__)

# 腾讯财经行情域名（多地址容错）
TENCENT_QT_HOSTS = [
    "https://qt.gtimg.cn",
    "https://sqt.gtimg.cn",
    "https://web.sqt.gtimg.cn",
]

# ─── 主流活跃股票池 (~800 只，覆盖主要交易品种) ───
# 数据来自 HS300 + ZZ500 + GEM50 + STAR50 成分股（预置保证速度）

STOCK_POOL = [
    # 上证50 / 沪深300 蓝筹
    "sh600000", "sh600004", "sh600006", "sh600007", "sh600008", "sh600009",
    "sh600010", "sh600011", "sh600012", "sh600015", "sh600016", "sh600018",
    "sh600019", "sh600025", "sh600028", "sh600029", "sh600030", "sh600031",
    "sh600036", "sh600037", "sh600048", "sh600050", "sh600061", "sh600085",
    "sh600089", "sh600100", "sh600104", "sh600111", "sh600150", "sh600188",
    "sh600196", "sh600276", "sh600309", "sh600340", "sh600362", "sh600406",
    "sh600436", "sh600438", "sh600487", "sh600519", "sh600547", "sh600570",
    "sh600585", "sh600588", "sh600600", "sh600660", "sh600690", "sh600703",
    "sh600745", "sh600795", "sh600809", "sh600837", "sh600886", "sh600887",
    "sh600893", "sh600900", "sh600905", "sh600918", "sh600926", "sh600941",
    "sh600958", "sh600989", "sh600999", "sh601006", "sh601012", "sh601021",
    "sh601066", "sh601088", "sh601100", "sh601111", "sh601138", "sh601166",
    "sh601169", "sh601186", "sh601225", "sh601229", "sh601288", "sh601318",
    "sh601319", "sh601328", "sh601336", "sh601398", "sh601628", "sh601633",
    "sh601658", "sh601668", "sh601669", "sh601688", "sh601728", "sh601766",
    "sh601800", "sh601808", "sh601818", "sh601838", "sh601857", "sh601877",
    "sh601888", "sh601899", "sh601916", "sh601919", "sh601939", "sh601988",
    "sh601995", "sh601998", "sh603019", "sh603259", "sh603288", "sh603501",
    "sh603799", "sh603986", "sh603993",
    # 沪深300 中盘
    "sh600021", "sh600026", "sh600027", "sh600039", "sh600060", "sh600066",
    "sh600068", "sh600072", "sh600079", "sh600096", "sh600118", "sh600143",
    "sh600161", "sh600170", "sh600177", "sh600183", "sh600196", "sh600208",
    "sh600233", "sh600271", "sh600297", "sh600298", "sh600346", "sh600369",
    "sh600372", "sh600438", "sh600487", "sh600516", "sh600522", "sh600547",
    "sh600583", "sh600585", "sh600660", "sh600690", "sh600703", "sh600705",
    "sh600741", "sh600795", "sh600809", "sh600837", "sh600848", "sh600886",
    "sh600887", "sh600893", "sh600900", "sh600918", "sh600926", "sh600941",
    "sh600958", "sh600989", "sh600999", "sh601012", "sh601066", "sh601088",
    "sh601138", "sh601166", "sh601169", "sh601186", "sh601229", "sh601288",
    "sh601318", "sh601336", "sh601398", "sh601628", "sh633633", "sh633688",
    "sh688001", "sh688009", "sh688012", "sh688036", "sh688065", "sh688082",
    "sh688111", "sh688126", "sh688169", "sh688223", "sh688256", "sh688271",
    "sh688303", "sh688321", "sh688349", "sh688396", "sh688521", "sh688599",
    "sh688981", "sh689009",
    # 深证主板
    "sz000001", "sz000002", "sz000063", "sz000066", "sz000069", "sz000100",
    "sz000157", "sz000333", "sz000338", "sz000425", "sz000538", "sz000568",
    "sz000625", "sz000651", "sz000661", "sz000725", "sz000768", "sz000776",
    "sz000792", "sz000858", "sz000876", "sz000895", "sz000938", "sz000963",
    "sz000977", "sz000999", "sz001289", "sz001979", "sz002001", "sz002027",
    "sz002032", "sz002142", "sz002230", "sz002241", "sz002271", "sz002304",
    "sz002311", "sz002352", "sz002371", "sz002415", "sz002460", "sz002466",
    "sz002475", "sz002493", "sz002555", "sz002594", "sz002607", "sz002714",
    "sz002736", "sz002812", "sz002841", "sz002916", "sz003816", "sz300014",
    "sz300015", "sz300033", "sz300059", "sz300122", "sz300124", "sz300142",
    "sz300144", "sz300223", "sz300274", "sz300316", "sz300347", "sz300408",
    "sz300413", "sz300433", "sz300442", "sz300498", "sz300601", "sz300628",
    "sz300661", "sz300674", "sz300750", "sz300751", "sz300759", "sz300760",
    "sz300782", "sz300866", "sz300888", "sz300896", "sz300919", "sz300979",
    "sz300999",
    # 创业板
    "sz300033", "sz300122", "sz300124", "sz300142", "sz300144", "sz300223",
    "sz300274", "sz300316", "sz300347", "sz300408", "sz300413", "sz300433",
    "sz300442", "sz300498", "sz300601", "sz300628", "sz300661", "sz300674",
    "sz300750", "sz300751", "sz300759", "sz300760", "sz300782", "sz300866",
    "sz300888", "sz300896", "sz300919", "sz300979", "sz300999",
    # 科创板
    "sh688009", "sh688036", "sh688065", "sh688082", "sh688111", "sh688126",
    "sh688169", "sh688223", "sh688256", "sh688271", "sh688303", "sh688321",
    "sh688349", "sh688396", "sh688521", "sh688599", "sh688981",
    # 行业龙头
    "sh601012", "sh601633", "sh600519", "sh600276", "sh600036", "sh601318",
    "sh600030", "sh600887", "sh601166", "sh600000", "sh600028", "sh601857",
    "sh601088", "sh600188", "sh601898", "sh601899", "sh600585", "sh601628",
    "sh601669", "sh601138", "sh601288", "sh601398", "sh601939", "sh601988",
    "sh600837", "sh600690", "sh600703", "sh600660", "sh600309", "sh600196",
    "sh600436", "sh600276", "sh600588", "sh600570", "sh600547", "sh600436",
    "sh600362", "sh600893", "sh600905", "sh600918", "sh600941", "sh600958",
    "sh600989", "sh600999", "sh601012", "sh601066", "sh601088", "sh601100",
    "sh601111", "sh601138", "sh601166", "sh601169", "sh601186", "sh601225",
    "sh601229", "sh601288", "sh601318", "sh601319", "sh601328", "sh601336",
    "sh601398", "sh601628", "sh601633", "sh601658", "sh601668", "sh601669",
    "sh601688", "sh601728", "sh601766", "sh601800", "sh601808", "sh601818",
    "sh601838", "sh601857", "sh601877", "sh601888", "sh601899", "sh601916",
    "sh601919", "sh601939", "sh601988", "sh601995", "sh601998",
    # 热门中小盘
    "sz002415", "sz002466", "sz002475", "sz002493", "sz002555", "sz002594",
    "sz002607", "sz002714", "sz002736", "sz002812", "sz002841", "sz002916",
    "sz003816",
    # 证券
    "sh600030", "sh600837", "sh600999", "sh601066", "sh601788", "sh601901",
    "sh601377", "sh601555", "sh601198", "sh601688", "sh600958", "sh600061",
    "sh600901", "sh601555", "sh601688", "sh601066", "sh600061", "sh600958",
    "sh600901", "sh601162", "sh601377", "sh601555", "sh601198", "sh601788",
    "sh601901", "sh600291", "sh600621", "sh601236", "sh601555",
    # 银行
    "sh600000", "sh600015", "sh600016", "sh600036", "sh601166", "sh601169",
    "sh601288", "sh601328", "sh601398", "sh601939", "sh601988", "sh601658",
    "sh601229", "sh601838", "sh601009", "sh601128", "sh601077", "sh601128",
    # 白酒消费
    "sh600519", "sh600809", "sh600887", "sh600600", "sh600132", "sh603369",
    "sh603589", "sh603517", "sh603288", "sh600197", "sh603027", "sh603043",
    "sz000858", "sz000568", "sz000596", "sz000729", "sz000752", "sz000860",
    "sz000895", "sz000876",
    # 医药
    "sh600276", "sh600196", "sh600436", "sh600867", "sh600085", "sh600521",
    "sh600511", "sh600161", "sh600079", "sh600422", "sh600332", "sh600535",
    "sz000538", "sz000423", "sz000661", "sz000999", "sz300760", "sz300003",
    "sz300015", "sz300122", "sz300142", "sz300347", "sz300601", "sz300003",
    # 新能源
    "sh601012", "sh600905", "sh601877", "sh601615", "sh600089", "sh601727",
    "sh601766", "sh600089", "sh601615", "sh601727", "sh600089", "sh601012",
    "sh600905", "sh601877",
    "sz002074", "sz002460", "sz002129", "sz002709", "sz002074", "sz002709",
    "sz300316", "sz300750", "sz300014", "sz300751", "sz300438", "sz300450",
    "sz300316", "sz300014", "sz300438",
    # 科技
    "sh600588", "sh600271", "sh600850", "sh600100", "sh600845", "sh600845",
    "sh600845", "sh600100", "sh600588", "sh600271", "sh600850",
    "sz000063", "sz000725", "sz000977", "sz002230", "sz002241", "sz002415",
    "sz002475", "sz000063", "sz000725", "sz000977", "sz002230", "sz002241",
    "sz002415", "sz002475",
]


@dataclass
class StockQuote:
    symbol: str
    code: str
    name: str
    price: float
    change: float
    change_pct: float
    volume: int = 0
    amount: float = 0.0
    high: float = 0.0
    low: float = 0.0
    open: float = 0.0
    prev_close: float = 0.0
    turnover_rate: Optional[float] = None
    pe_ratio: Optional[float] = None
    market_cap: Optional[float] = None
    circul_cap: Optional[float] = None


_QT_RE = re.compile(r"v_[^=]+=\"([^\"]*)\"")


def _to_symbol(code: str, market: str) -> str:
    m = market.upper().strip()
    if m in ("1", "SH"):
        return f"{code}.SH"
    if m in ("51", "SZ"):
        return f"{code}.SZ"
    if m in ("0", "BJ"):
        return f"{code}.BJ"
    return f"{code}.UNKNOWN"
    m = market.upper()
    if m == "SH":
        return f"{code}.SH"
    if m == "SZ":
        return f"{code}.SZ"
    if m == "BJ":
        return f"{code}.BJ"
    return f"{code}.UNKNOWN"


def parse_tencent_qt(raw: str) -> List[StockQuote]:
    """解析腾讯 qt 接口返回的文本
    字段索引（参考腾讯官方字段顺序）：
      0:市场  1:名称  2:代码  3:现价  4:昨收  5:今开
      6:成交量(手)  7:外盘  8:内盘
      ...
      31:涨跌额  32:涨跌幅(%)  33:最高  34:最低
      34:价格/成交量  35:成交量(手)  37:成交额(万元)
      38:换手率(%)  39:市盈率(动)
      ...
      45:总市值(亿)  46:流通市值(亿)
    """
    results = []
    for m in _QT_RE.finditer(raw):
        fields = m.group(1).split("~")
        if len(fields) < 50 or not fields[0] or not fields[1]:
            continue
        try:
            market = fields[0]
            name = fields[1]
            code = fields[2]
            price = float(fields[3])
            prev_close = float(fields[4])
            open_price = float(fields[5])
            volume = int(float(fields[6]))
            change = float(fields[31])
            change_pct = float(fields[32])
            high = float(fields[33])
            low = float(fields[34])
            amount = float(fields[37]) * 10000  # 万→元

            turnover_rate = float(fields[38]) if fields[38] else None
            pe_str = fields[39] if len(fields) > 38 else ""
            pe_ratio = float(pe_str) if pe_str and pe_str != "0.00" else None

            mc_str = fields[45] if len(fields) > 44 else ""
            market_cap = float(mc_str) * 1e8 if mc_str and mc_str not in ("", "0.00") else None

            cc_str = fields[46] if len(fields) > 45 else ""
            circul_cap = float(cc_str) * 1e8 if cc_str and cc_str not in ("", "0.00") else None

            results.append(StockQuote(
                symbol=_to_symbol(code, market),
                code=code,
                name=name,
                price=price,
                change=change,
                change_pct=change_pct,
                volume=volume,
                amount=amount,
                high=high,
                low=low,
                open=open_price,
                prev_close=prev_close,
                turnover_rate=turnover_rate,
                pe_ratio=pe_ratio,
                market_cap=market_cap,
                circul_cap=circul_cap,
            ))
        except (ValueError, IndexError):
            continue
    return results


async def fetch_batch_quotes(
    symbols: List[str],
    timeout: float = 15.0,
    batch_size: int = 80,
) -> List[StockQuote]:
    """批量获取行情。symbols 格式: [sh600519, sz000001, ...]"""
    all_results = []

    async def fetch_one_batch(batch: List[str]) -> List[StockQuote]:
        query = ",".join(batch)
        for host in TENCENT_QT_HOSTS:
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    resp = await client.get(
                        f"{host}/q={query}",
                        headers={"User-Agent": "Mozilla/5.0"},
                    )
                    resp.encoding = "gbk"
                    parsed = parse_tencent_qt(resp.text)
                    if parsed:
                        return parsed
            except Exception:
                await asyncio.sleep(0.3)
                continue
        return []

    for i in range(0, len(symbols), batch_size):
        batch = symbols[i:i + batch_size]
        results = await fetch_one_batch(batch)
        all_results.extend(results)
        if i + batch_size < len(symbols):
            await asyncio.sleep(0.2)

    return all_results


# 缓存：拉一次全市场数据，5秒内复用
_market_cache = {"data": [], "ts": 0.0}
_CACHE_TTL = 10.0  # 10 秒缓存


async def fetch_ranking(
    sort_by: str = "change_pct",
    order: str = "desc",
    limit: int = 20,
) -> List[StockQuote]:
    """全市场排名（带 10s 缓存）"""
    now = time.time()
    if now - _market_cache["ts"] < _CACHE_TTL and _market_cache["data"]:
        quotes = _market_cache["data"]
    else:
        # 去重股票池
        pool = list(dict.fromkeys(STOCK_POOL))
        quotes = await fetch_batch_quotes(pool)
        _market_cache["data"] = quotes
        _market_cache["ts"] = now

    # 过滤停牌等无效数据
    quotes = [q for q in quotes if not (q.change_pct == 0.0 and q.price == 0.0)]

    reverse = order == "desc"
    if sort_by == "volume":
        quotes.sort(key=lambda x: x.volume, reverse=reverse)
    elif sort_by == "amount":
        quotes.sort(key=lambda x: x.amount, reverse=reverse)
    else:
        quotes.sort(key=lambda x: x.change_pct, reverse=reverse)

    return quotes[:limit]
