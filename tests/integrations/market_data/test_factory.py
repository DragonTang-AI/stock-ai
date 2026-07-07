"""
tests/integrations/market_data/test_factory.py — Factory 单元测试

测试数据源选择逻辑：显式指定 + 自动降级
"""
import pytest
from unittest.mock import patch

from app.integrations.market_data.factory import (
    get_market_data_adapter,
    reset_adapter_cache,
    MockAdapter,
)
from app.integrations.market_data.sina import SinaAdapter
from app.integrations.market_data.akshare import AkshareAdapter, is_akshare_available


class TestFactory:
    def setup_method(self):
        """每个测试前重置缓存"""
        reset_adapter_cache()

    def teardown_method(self):
        """每个测试后重置缓存和环境变量"""
        reset_adapter_cache()
        import os

        if "MARKET_DATA_SOURCE" in os.environ:
            del os.environ["MARKET_DATA_SOURCE"]

    def test_explicit_sina(self):
        """显式指定 sina"""
        import os

        os.environ["MARKET_DATA_SOURCE"] = "sina"
        adapter = get_market_data_adapter()
        assert isinstance(adapter, SinaAdapter)
        assert adapter.name == "sina"

    def test_explicit_mock(self):
        """显式指定 mock"""
        import os

        os.environ["MARKET_DATA_SOURCE"] = "mock"
        adapter = get_market_data_adapter()
        assert isinstance(adapter, MockAdapter)
        assert adapter.name == "mock"

    def test_explicit_akshare_when_available(self):
        """显式指定 akshare（仅当可用时）"""
        import os

        os.environ["MARKET_DATA_SOURCE"] = "akshare"
        adapter = get_market_data_adapter()
        if is_akshare_available():
            assert isinstance(adapter, AkshareAdapter)
        else:
            # 不可用时降级到 mock
            assert isinstance(adapter, MockAdapter)

    def test_auto_fallback(self):
        """未指定时自动降级"""
        adapter = get_market_data_adapter()
        # akshare 或 sina 至少有一个可用；如果都不可用，应该是 Mock
        assert adapter.name in ("akshare", "sina", "mock")

    def test_invalid_source_falls_back_to_mock(self):
        """无效的 source 应该降级到 mock"""
        import os

        os.environ["MARKET_DATA_SOURCE"] = "invalid_source_xyz"
        adapter = get_market_data_adapter()
        assert isinstance(adapter, MockAdapter)

    def test_cache_returns_same_instance(self):
        """缓存保证单例"""
        import os

        os.environ["MARKET_DATA_SOURCE"] = "sina"
        a = get_market_data_adapter()
        b = get_market_data_adapter()
        assert a is b


class TestMockAdapter:
    """MockAdapter 单元测试"""

    @pytest.mark.asyncio
    async def test_get_quote(self):
        adapter = MockAdapter()
        q = await adapter.get_quote("TEST.SH")
        assert q.symbol == "TEST.SH"
        assert q.name == "Mock-TEST.SH"
        assert q.price == 100.0

    @pytest.mark.asyncio
    async def test_get_quotes_batch(self):
        adapter = MockAdapter()
        quotes = await adapter.get_quotes(["A.SH", "B.SZ"])
        assert len(quotes) == 2
        assert {q.symbol for q in quotes} == {"A.SH", "B.SZ"}

    @pytest.mark.asyncio
    async def test_get_kline(self):
        from app.integrations.market_data.base import Period

        adapter = MockAdapter()
        klines = await adapter.get_kline("TEST.SH", Period.DAILY, count=30)
        assert len(klines) == 30
        # 按日期升序
        assert klines[0].date < klines[-1].date
