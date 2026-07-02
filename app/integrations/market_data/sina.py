"""
app.integrations.market_data.sina — 新浪财经 HTTP API 实现

API 文档参考（无需鉴权、无频率限制声明）：
  实时行情: http://hq.sinajs.cn/list=sh600519,sz000001
  K 线:     https://quotes.sina.cn/cn/api/jsonp_v2.php/var=.../CN_MarketDataService.getKLineData?symbol=sh600519&scale=240&ma=no&datalen=100

注意：
1. 新浪要求 Referer 头，否则可能 403
2. 新浪 K 线接口的数据是"按时间倒序"，需要反转
3. 实时行情的字段顺序是固定的，参考 base.py 中的 from_sina() 注释
4. 新浪的 volume 单位是"手"（1手=100股），amount 单位是"元"
"""
import logging
from typing import List
import httpx

from app.integrations.market_data.base import (
    MarketDataAdapter,
    QuoteData,
    KLineData,
    Period,
    DataSourceError,
    SymbolNotFoundError,
)

logger = logging.getLogger(__name__)

# 新浪实时行情接口
SINA_REALTIME_URL = "http://hq.sinajs.cn/list={symbols}"

# 新浪 K 线接口
# scale: 240=日线, 1680=周线, 7200=月线
SINA_KLINE_URL = "https://quotes.sina.cn/cn/api/jsonp_v2.php/var={callback}/CN_MarketDataService.getKLineData"
SINA_KLINE_PERIOD_MAP = {
    Period.DAILY: "240",
    Period.WEEKLY: "1680",
    Period.MONTHLY: "7200",
}

# 新浪要求 Referer 头（来自浏览器请求）
SINA_REFERER = "https://finance.sina.com.cn/"


def _to_sina_symbol(symbol: str) -> str:
    """
    标准代码转新浪代码

    Args:
        symbol: 标准代码，如 "600519.SH" / "000001.SZ"

    Returns:
        新浪代码，如 "sh600519" / "sz000001"
    """
    if "." not in symbol:
        raise ValueError(f"标准代码必须带市场后缀: {symbol}")

    code, market = symbol.rsplit(".", 1)
    market_lower = market.lower()

    # 6 开头是上海（sh），其他是深圳（sz）
    if code.startswith("6") or market_lower == "sh":
        return f"sh{code}"
    elif code.startswith(("0", "3")) or market_lower == "sz":
        return f"sz{code}"
    elif code.startswith(("4", "8")) or market_lower == "bj":  # 北交所
        return f"bj{code}"
    else:
        raise ValueError(f"无法识别股票代码市场: {symbol}")


def _to_standard_symbol(sina_code: str) -> str:
    """
    新浪代码转标准代码

    Args:
        sina_code: 新浪代码，如 "sh600519"

    Returns:
        标准代码，如 "600519.SH"
    """
    if sina_code.startswith("sh"):
        return f"{sina_code[2:]}.SH"
    elif sina_code.startswith("sz"):
        return f"{sina_code[2:]}.SZ"
    elif sina_code.startswith("bj"):
        return f"{sina_code[2:]}.BJ"
    else:
        return sina_code


class SinaAdapter(MarketDataAdapter):
    """
    新浪财经数据源适配器

    优点：
    - 零依赖（只用 httpx）
    - 无需 API Key
    - 速度快（CDN 加速）
    - 支持批量查询（list=sh600519,sz000001）

    缺点：
    - 不稳定（新浪经常调整接口字段）
    - 单次最多 50 个代码（实测）
    - 没有市净率/PB 数据
    - 限流严格（高频访问会被封 IP）
    """

    name = "sina"

    def __init__(
        self,
        timeout: float = 5.0,
        max_batch_size: int = 50,
    ):
        self.timeout = timeout
        self.max_batch_size = max_batch_size
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """延迟创建客户端，复用连接池"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                headers={
                    "Referer": SINA_REFERER,
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36",
                },
            )
        return self._client

    async def close(self):
        """关闭客户端"""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def get_quote(self, symbol: str) -> QuoteData:
        """获取单只股票实时行情"""
        results = await self.get_quotes([symbol])
        if not results:
            raise SymbolNotFoundError(self.name, symbol)
        return results[0]

    async def get_quotes(self, symbols: List[str]) -> List[QuoteData]:
        """
        批量获取实时行情

        新浪接口格式：
        hq.sinajs.cn/list=sh600519,sz000001

        响应格式（每行一个股票）：
        var hq_str_sh600519="贵州茅台,1680.00,1680.00,1680.00,...";
        """
        if not symbols:
            return []

        results: List[QuoteData] = []
        client = await self._get_client()

        # 批量请求（分批避免超过上限）
        for i in range(0, len(symbols), self.max_batch_size):
            batch = symbols[i : i + self.max_batch_size]
            sina_codes = [_to_sina_symbol(s) for s in batch]
            url = SINA_REALTIME_URL.format(symbols=",".join(sina_codes))

            try:
                resp = await client.get(url)
                resp.raise_for_status()
            except httpx.HTTPStatusError as e:
                raise DataSourceError(
                    self.name,
                    f"HTTP {e.response.status_code}",
                    original=e,
                )
            except httpx.RequestError as e:
                raise DataSourceError(
                    self.name,
                    f"网络错误: {type(e).__name__}",
                    original=e,
                )

            # 解析响应
            # 响应是 GBK 编码，需要先检测
            try:
                text = resp.content.decode("gbk")
            except UnicodeDecodeError:
                # 降级到 utf-8
                text = resp.text

            for line in text.strip().split("\n"):
                if "=" not in line or '""' in line:
                    # 空数据行：var hq_str_sh600519="";
                    # 表示该股票代码无效或停牌
                    continue

                # 解析 var hq_str_sh600519="...";
                try:
                    # 拆分 var xxx = "...";
                    left, right = line.split("=", 1)
                    sina_code = left.split("_str_")[1].strip()
                    # 去掉前后引号和分号
                    fields_str = right.strip().strip(';').strip()
                    if not fields_str or fields_str.startswith('"'):
                        fields_str = fields_str.strip('"')

                    fields = fields_str.split(",")
                    if len(fields) < 33:
                        logger.warning(
                            f"[{self.name}] 字段数不足: {sina_code}, "
                            f"got {len(fields)}, skip"
                        )
                        continue

                    name = fields[0]
                    standard_symbol = _to_standard_symbol(sina_code)
                    quote = QuoteData.from_sina(standard_symbol, name, fields)
                    results.append(quote)
                except (ValueError, IndexError) as e:
                    logger.warning(f"[{self.name}] 解析失败: {line[:80]}... ({e})")
                    continue

        return results

    async def get_kline(
        self,
        symbol: str,
        period: Period = Period.DAILY,
        count: int = 100,
    ) -> List[KLineData]:
        """
        获取 K 线历史数据

        新浪 K 线接口（JSONP 格式）：
        https://quotes.sina.cn/cn/api/jsonp_v2.php/var=.../CN_MarketDataService.getKLineData?symbol=sh600519&scale=240&ma=no&datalen=100

        响应格式（JSONP 包装的 JSON 数组）：
        var _CN_MarketDataService.getKLineData_xxx = [
          {day:"2024-01-02", open:"1680.00", high:"1700.00", low:"1670.00", close:"1690.00", volume:"1000000", amount:"1680000000"},
          ...
        ];
        """
        client = await self._get_client()
        sina_code = _to_sina_symbol(symbol)
        scale = SINA_KLINE_PERIOD_MAP.get(period, "240")

        # 用 jsonp 回调名
        callback = "_CN_MarketDataService.getKLineData_call"

        params = {
            "symbol": sina_code,
            "scale": scale,
            "ma": "no",
            "datalen": count,
        }

        try:
            resp = await client.get(
                SINA_KLINE_URL.format(callback=callback),
                params=params,
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise DataSourceError(
                self.name,
                f"HTTP {e.response.status_code}",
                original=e,
            )
        except httpx.RequestError as e:
            raise DataSourceError(
                self.name,
                f"网络错误: {type(e).__name__}",
                original=e,
            )

        # 解析 JSONP
        text = resp.text
        # 去掉 var ... =  和 ; 包装
        try:
            # 找到第一个 [ 和最后一个 ]
            start = text.index("[")
            end = text.rindex("]") + 1
            json_str = text[start:end]
            import json

            raw_data = json.loads(json_str)
        except (ValueError, json.JSONDecodeError) as e:
            logger.warning(f"[{self.name}] K线 JSONP 解析失败: {text[:100]}")
            raise DataSourceError(
                self.name,
                f"K线响应解析失败: {type(e).__name__}",
                original=e,
            )

        if not raw_data:
            return []

        # 新浪 K 线数据按时间倒序，需要反转
        raw_data = list(reversed(raw_data))

        results: List[KLineData] = []
        for row in raw_data:
            try:
                # 字段：day, open, high, low, close, volume, amount（可选 ma5/ma10/ma20）
                kline = KLineData(
                    symbol=symbol,
                    date=row.get("day", ""),
                    period=period,
                    open=float(row.get("open", 0)),
                    close=float(row.get("close", 0)),
                    high=float(row.get("high", 0)),
                    low=float(row.get("low", 0)),
                    volume=int(row.get("volume", 0)),
                    amount=float(row["amount"]) if "amount" in row else None,
                )
                results.append(kline)
            except (ValueError, KeyError) as e:
                logger.warning(f"[{self.name}] K线数据行解析失败: {row} ({e})")
                continue

        return results
