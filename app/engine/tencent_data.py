"""
腾讯股票 API 数据适配器
提供价格数据、基本面数据的获取，替代 Yahoo Finance / financialdatasets.ai
"""
import logging
import re
from datetime import datetime, date
from typing import Optional

import pandas as pd
import requests

from src.data.models import Price, FinancialMetrics

logger = logging.getLogger(__name__)

# ── 股票代码转换 ──

def normalize_ticker(ticker: str) -> str:
    """
    将用户输入的股票代码转为腾讯API格式
    600036 → sh600036, 000001 → sz000001, 300750 → sz300750, 688111 → sh688111
    已含 sh/sz 前缀则直接返回
    """
    ticker = ticker.strip().upper()
    if ticker.startswith("SH") or ticker.startswith("SZ"):
        return ticker.lower()
    # 6位纯数字
    if re.match(r'^\d{6}$', ticker):
        code = ticker
        if code.startswith(('6', '68')):
            return f"sh{code}"
        elif code.startswith(('0', '3')):
            return f"sz{code}"
    # 已经带前缀
    if re.match(r'^(?:sh|sz)\d{6}$', ticker, re.IGNORECASE):
        return ticker.lower()
    return ticker.lower()


def is_a_share_ticker(ticker: str) -> bool:
    """判断是否为 A 股代码"""
    ticker = ticker.strip()
    if re.match(r'^(?:sh|sz)\d{6}$', ticker, re.IGNORECASE):
        return True
    if re.match(r'^\d{6}$', ticker):
        code = ticker
        return code.startswith(('6', '68', '0', '3'))
    return False


def get_raw_ticker(ticker: str) -> str:
    """提取纯数字代码（去掉 sh/sz）"""
    ticker = ticker.strip()
    m = re.search(r'(\d{6})', ticker)
    return m.group(1) if m else ticker


# ── 实时行情 ──

def get_realtime_quote(ticker: str) -> Optional[dict]:
    """
    获取实时行情数据
    返回包含 name, price, pe_ratio, market_cap, volume, change_pct 等字段的 dict
    """
    tencent_ticker = normalize_ticker(ticker)
    try:
        url = f"http://qt.gtimg.cn/q={tencent_ticker}"
        resp = requests.get(url, timeout=10)
        resp.encoding = 'gbk'
        text = resp.text
        if not text or '="' not in text:
            logger.warning("Empty or invalid response for %s", tencent_ticker)
            return None

        # 提取引号内的数据
        data_str = text.split('="')[1].rstrip('";\n\r ')
        if not data_str:
            return None

        fields = data_str.split('~')
        if len(fields) < 50:
            logger.warning("Insufficient fields (%d) for %s", len(fields), tencent_ticker)
            return None

        # 腾讯API字段映射
        # 0=市场, 1=名称, 2=代码, 3=现价, 4=昨收, 5=今开, 6=成交量(手), 
        # 30=涨跌额, 31=涨跌幅%, 32=换手率, 33=最高, 34=最低,
        # 36=成交额(万), 37=总市值, 38=流通市值, 39=市盈率,
        # 42=涨停价, 43=跌停价, 44=量比, 45=委差, 46=均价, 
        # 47=动态市盈率, 48=静态市盈率, 49=振幅%

        def to_float(val: str) -> Optional[float]:
            try:
                return float(val) if val else None
            except (ValueError, TypeError):
                return None

        total_market_cap_raw = to_float(fields[37])  # 单位：亿
        market_cap = total_market_cap_raw * 1e8 if total_market_cap_raw else None

        return {
            "name": fields[1],
            "code": fields[2],
            "price": to_float(fields[3]),
            "prev_close": to_float(fields[4]),
            "open": to_float(fields[5]),
            "volume_hands": to_float(fields[6]),
            "high": to_float(fields[33]),
            "low": to_float(fields[34]),
            "amount_wan": to_float(fields[36]),
            "market_cap": market_cap,  # 已转换为元
            "circulating_market_cap": (to_float(fields[38]) or 0) * 1e8,
            "pe_ratio": to_float(fields[39]),
            "dynamic_pe": to_float(fields[47]),
            "static_pe": to_float(fields[48]),
            "change_pct": to_float(fields[31]),
            "change_amount": to_float(fields[30]),
            "turnover_rate": to_float(fields[32]),
            "high_limit": to_float(fields[42]),
            "low_limit": to_float(fields[43]),
            "volume_ratio": to_float(fields[44]),
            "amplitude": to_float(fields[49]),
        }
    except Exception as e:
        logger.warning("Failed to get realtime quote for %s: %s", ticker, e)
        return None


# ── K线历史数据 ──

def get_kline_data(ticker: str, days: int = 365, kline_type: str = "day") -> Optional[pd.DataFrame]:
    """
    获取K线历史数据，返回 DataFrame
    列: Date(索引), Open, High, Low, Close, Volume
    
    K线数据格式: [日期, 开盘价, 收盘价, 最高价, 最低价, 成交量]
    """
    tencent_ticker = normalize_ticker(ticker)
    try:
        url = f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={tencent_ticker},{kline_type},,,{days},qfq"
        resp = requests.get(url, timeout=15)
        data = resp.json()
        if data.get("code") != 0:
            logger.warning("Kline API error for %s: code=%s", tencent_ticker, data.get("code"))
            return None

        stock_data = data.get("data", {}).get(tencent_ticker, {})
        kline_key = f"qfq{kline_type}"
        kline_list = stock_data.get(kline_key)
        
        if not kline_list:
            # 尝试不复权
            kline_list = stock_data.get(kline_type)
        if not kline_list:
            logger.warning("No kline data for %s", tencent_ticker)
            return None

        # 腾讯K线格式: [日期, 开盘, 收盘, 最高, 最低, 成交量]
        rows = []
        for row in kline_list:
            if len(row) < 6:
                continue
            try:
                rows.append({
                    "Date": row[0],
                    "Open": float(row[1]),
                    "Close": float(row[2]),
                    "High": float(row[3]),
                    "Low": float(row[4]),
                    "Volume": float(row[5]),
                })
            except (ValueError, TypeError):
                continue

        if not rows:
            return None

        df = pd.DataFrame(rows)
        df["Date"] = pd.to_datetime(df["Date"])
        df.set_index("Date", inplace=True)
        df.sort_index(inplace=True)
        return df
    except Exception as e:
        logger.warning("Failed to get kline data for %s: %s", ticker, e)
        return None


# ── 与 ai-hedge-fund 兼容的接口 ──

def get_prices(ticker: str, start_date: str, end_date: str) -> list[Price]:
    """
    替换 api.py 中的 get_prices，返回 list[Price]
    仅在 A 股时使用；非 A 股返回空列表交由原逻辑处理
    """
    if not is_a_share_ticker(ticker):
        return []

    # 计算需要的天数
    try:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        days = (end_dt - start_dt).days + 10  # 多一些缓冲
        if days < 30:
            days = 30
        days = min(days, 2000)
    except Exception:
        days = 365

    df = get_kline_data(ticker, days=days)
    if df is None or df.empty:
        return []

    # 按日期范围过滤
    try:
        df = df.loc[start_date:end_date]
    except Exception:
        pass

    if df.empty:
        return []

    prices = []
    for idx, row in df.iterrows():
        try:
            prices.append(Price(
                open=float(row["Open"]),
                close=float(row["Close"]),
                high=float(row["High"]),
                low=float(row["Low"]),
                volume=int(row["Volume"]),
                time=idx.strftime("%Y-%m-%d") if hasattr(idx, 'strftime') else str(idx)[:10],
            ))
        except Exception:
            continue

    return prices


def get_financial_metrics(ticker: str, end_date: str, period: str = "ttm", limit: int = 10) -> list[FinancialMetrics]:
    """
    替换 api.py 中的 get_financial_metrics
    从腾讯实时行情中提取可用指标填充 FinancialMetrics
    """
    if not is_a_share_ticker(ticker):
        return []

    quote = get_realtime_quote(ticker)
    if not quote:
        return []

    # 构建 FinancialMetrics，腾讯API能提供的字段
    report_period = end_date or date.today().strftime("%Y-%m-%d")
    
    metrics = FinancialMetrics(
        ticker=ticker,
        report_period=report_period,
        period=period,
        currency="CNY",
        market_cap=quote.get("market_cap"),
        enterprise_value=None,
        price_to_earnings_ratio=quote.get("pe_ratio"),
        price_to_book_ratio=None,
        price_to_sales_ratio=None,
        enterprise_value_to_ebitda_ratio=None,
        enterprise_value_to_revenue_ratio=None,
        free_cash_flow_yield=None,
        peg_ratio=None,
        gross_margin=None,
        operating_margin=None,
        net_margin=None,
        return_on_equity=None,
        return_on_assets=None,
        return_on_invested_capital=None,
        asset_turnover=None,
        inventory_turnover=None,
        receivables_turnover=None,
        days_sales_outstanding=None,
        operating_cycle=None,
        working_capital_turnover=None,
        current_ratio=None,
        quick_ratio=None,
        cash_ratio=None,
        operating_cash_flow_ratio=None,
        debt_to_equity=None,
        debt_to_assets=None,
        interest_coverage=None,
        revenue_growth=None,
        earnings_growth=None,
        book_value_growth=None,
        earnings_per_share_growth=None,
        free_cash_flow_growth=None,
        operating_income_growth=None,
        ebitda_growth=None,
        payout_ratio=None,
        earnings_per_share=None,
        book_value_per_share=None,
        free_cash_flow_per_share=None,
    )
    
    return [metrics]


def get_market_cap(ticker: str, end_date: str = None) -> Optional[float]:
    """替换 api.py 中的 get_market_cap"""
    if not is_a_share_ticker(ticker):
        return None
    quote = get_realtime_quote(ticker)
    if quote:
        return quote.get("market_cap")
    return None


def get_company_name(ticker: str) -> str:
    """获取股票中文名称"""
    quote = get_realtime_quote(ticker)
    if quote:
        return quote.get("name", ticker)
    return ticker


# ── 便捷函数 ──

def prices_to_df(prices: list[Price]) -> pd.DataFrame:
    """与 api.py 中同名函数保持一致的接口"""
    df = pd.DataFrame([p.model_dump() for p in prices])
    df["Date"] = pd.to_datetime(df["time"])
    df.set_index("Date", inplace=True)
    numeric_cols = ["open", "close", "high", "low", "volume"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df.sort_index(inplace=True)
    return df


def get_price_data(ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
    """与 api.py 中同名函数保持一致的接口"""
    prices = get_prices(ticker, start_date, end_date)
    if not prices:
        return pd.DataFrame()
    return prices_to_df(prices)
