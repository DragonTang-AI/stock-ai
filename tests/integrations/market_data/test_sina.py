"""
tests/integrations/market_data/test_sina.py — SinaAdapter 单元测试

测试策略：
1. 单元测试：使用 respx/httpx_mock 拦截 HTTP 请求
2. 集成测试：直接打真实 API（标记为 integration，需要时手动跑）
"""
import pytest
import respx
import httpx
from datetime import datetime

from app.integrations.market_data.sina import SinaAdapter, _to_sina_symbol, _to_standard_symbol
from app.integrations.market_data.base import QuoteData, Period, DataSourceError


# === Symbol 转换测试 ===
class TestSymbolConversion:
    """测试代码转换函数"""

    def test_sh_to_sina(self):
        assert _to_sina_symbol("600519.SH") == "sh600519"

    def test_sz_to_sina(self):
        assert _to_sina_symbol("000001.SZ") == "sz000001"

    def test_bj_to_sina(self):
        assert _to_sina_symbol("830799.BJ") == "bj830799"

    def test_sina_to_standard(self):
        assert _to_standard_symbol("sh600519") == "600519.SH"
        assert _to_standard_symbol("sz000001") == "000001.SZ"
        assert _to_standard_symbol("bj830799") == "830799.BJ"

    def test_invalid_format_raises(self):
        with pytest.raises(ValueError):
            _to_sina_symbol("600519")  # 缺后缀


# === QuoteData.from_sina 测试 ===
class TestQuoteDataFromSina:
    """测试新浪字段解析"""

    def test_full_34_fields(self):
        """完整 33 字段解析（新浪实际返回 33 个字段）"""
        # 构造 33 字段: name + 5 OHLC + 2 bid/ask + 2 vol/amt + 20 bid/ask volumes + date + time + status
        fields = (
            ["贵州茅台"]  # [0] name
            + ["1193.01", "1193.01", "1203.00", "1215.52", "1190.51"]  # [1-5] OHLC
            + ["1203.00", "1204.00"]  # [6-7] bid1/ask1
            + ["5000000", "6000000000.000"]  # [8-9] volume/amount
            + ["0"] * 20  # [10-29] bid/ask volumes
            + ["2026-07-02", "15:00:00", "00"]  # [30-32] date/time/status
        )
        assert len(fields) == 33

        q = QuoteData.from_sina("600519.SH", "贵州茅台", fields)
        assert q.symbol == "600519.SH"
        assert q.name == "贵州茅台"
        assert q.price == 1203.00
        assert q.open == 1193.01
        assert q.high == 1215.52
        assert q.low == 1190.51
        assert q.prev_close == 1193.01
        assert q.change == pytest.approx(9.99, abs=0.01)
        assert q.change_pct == pytest.approx(0.84, abs=0.01)
        assert q.volume == 5000000
        assert q.amount == 6000000000.000
        assert q.timestamp == datetime(2026, 7, 2, 15, 0, 0)

    def test_insufficient_fields_raises(self):
        """字段数不足应该抛异常"""
        with pytest.raises(ValueError, match="字段数不足"):
            QuoteData.from_sina("600519.SH", "贵州茅台", ["贵州茅台", "1.0"])


# === SinaAdapter HTTP 测试 ===
class TestSinaAdapterHTTP:
    """使用 respx 模拟 HTTP 响应"""

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_quote_success(self):
        """成功获取单只股票"""
        # 准备 mock 响应（GBK 编码）
        response_text = (
            'var hq_str_sh600519="贵州茅台,1193.010,1193.010,1203.000,'
            "1215.520,1190.510,1203.000,1204.000,5000000,6000000000.000,"
            '0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,2026-07-02,15:00:03,00";'
        )
        # 用 GBK 编码
        response_bytes = response_text.encode("gbk")

        respx.get("http://hq.sinajs.cn/list=sh600519").mock(
            return_value=httpx.Response(200, content=response_bytes)
        )

        adapter = SinaAdapter()
        try:
            q = await adapter.get_quote("600519.SH")
            assert q.symbol == "600519.SH"
            assert q.name == "贵州茅台"
            assert q.price == 1203.0
            assert q.volume == 5000000
        finally:
            await adapter.close()

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_quotes_batch(self):
        """批量获取"""
        response_text = (
            'var hq_str_sh600519="贵州茅台,1193.010,1193.010,1203.000,'
            "1215.520,1190.510,1203.000,1204.000,5000000,6000000000.000,"
            '0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,2026-07-02,15:00:03,00";\n'
            'var hq_str_sz000001="平安银行,10.160,10.160,10.280,'
            "10.360,10.170,10.280,10.290,100000000,1000000000.000,"
            '0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,2026-07-02,15:00:00,00";'
        )
        response_bytes = response_text.encode("gbk")

        respx.get("http://hq.sinajs.cn/list=sh600519,sz000001").mock(
            return_value=httpx.Response(200, content=response_bytes)
        )

        adapter = SinaAdapter()
        try:
            quotes = await adapter.get_quotes(["600519.SH", "000001.SZ"])
            assert len(quotes) == 2
            symbols = {q.symbol for q in quotes}
            assert symbols == {"600519.SH", "000001.SZ"}
        finally:
            await adapter.close()

    @pytest.mark.asyncio
    @respx.mock
    async def test_empty_data_line_skipped(self):
        """空数据行（停牌）应该被跳过"""
        response_text = (
            'var hq_str_sh600519="";\n'  # 停牌
            'var hq_str_sz000001="平安银行,10.160,10.160,10.280,'
            "10.360,10.170,10.280,10.290,100000000,1000000000.000,"
            '0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,2026-07-02,15:00:00,00";'
        )
        response_bytes = response_text.encode("gbk")

        respx.get("http://hq.sinajs.cn/list=sh600519,sz000001").mock(
            return_value=httpx.Response(200, content=response_bytes)
        )

        adapter = SinaAdapter()
        try:
            quotes = await adapter.get_quotes(["600519.SH", "000001.SZ"])
            # 600519 停牌被跳过，只返回 000001
            assert len(quotes) == 1
            assert quotes[0].symbol == "000001.SZ"
        finally:
            await adapter.close()

    @pytest.mark.asyncio
    @respx.mock
    async def test_http_error_raises(self):
        """HTTP 错误应该抛 DataSourceError"""
        respx.get("http://hq.sinajs.cn/list=sh600519").mock(
            return_value=httpx.Response(500, text="Server Error")
        )

        adapter = SinaAdapter()
        try:
            with pytest.raises(DataSourceError, match="HTTP 500"):
                await adapter.get_quote("600519.SH")
        finally:
            await adapter.close()


# === 集成测试（需要网络，默认跳过） ===
class TestSinaIntegration:
    """真实 API 测试，需要网络"""

    @pytest.mark.skip(reason="集成测试，需要时手动跑")
    @pytest.mark.asyncio
    async def test_real_api(self):
        """打真实新浪 API"""
        adapter = SinaAdapter()
        try:
            q = await adapter.get_quote("600519.SH")
            assert q.symbol == "600519.SH"
            assert q.price > 0
            print(f"\n实时行情: {q.name} {q.price} {q.change_pct:+.2f}%")
        finally:
            await adapter.close()
