/**
 * 行情 API 客户端
 * 对接后端 /api/v1/market/*
 */
import { request } from '@/utils/request'

export interface QuoteItem {
  symbol: string        // 股票代码，如 "600519.SH"
  name: string         // 股票名称，如 "贵州茅台"
  price: number        // 最新价
  change: number       // 涨跌额
  change_pct: number   // 涨跌幅 (%)
  prev_close: number   // 昨收
  open: number         // 开盘价
  high: number         // 最高价
  low: number          // 最低价
  volume: number       // 成交量（手）
  amount: number       // 成交额（元）
  market: 'A' | 'HK'  // 市场：A=A股，HK=港股
  update_time: string  // 更新时间 ISO
}

export interface MarketKLine {
  symbol: string
  period: '1d' | '1w' | '1m'
  data: Array<{
    time: string
    open: number
    high: number
    low: number
    close: number
    volume: number
  }>
}

/** 后端行情 API 通用响应包装 */
interface MarketApiResponse<T> {
  success: boolean
  data: T
  note?: string
}

/**
 * 将后端原始行情字段标准化为 QuoteItem
 * 后端字段: symbol, name, price, open, high, low, close(昨收), change, change_pct, volume, amount
 */
function normalizeQuote(raw: Record<string, any>): QuoteItem {
  return {
    symbol: raw.symbol || '',
    name: raw.name || raw.symbol || '',
    price: raw.price ?? 0,
    change: raw.change ?? 0,
    change_pct: raw.change_pct ?? 0,
    prev_close: raw.close ?? raw.prev_close ?? 0,  // 后端 close 字段即为昨收价
    open: raw.open ?? 0,
    high: raw.high ?? 0,
    low: raw.low ?? 0,
    volume: raw.volume ?? 0,
    amount: raw.amount ?? 0,
    market: raw.market || (String(raw.symbol || '').endsWith('.HK') ? 'HK' : 'A'),
    update_time: raw.update_time || new Date().toISOString(),
  }
}

/** 获取行情列表（全部或指定股票） */
export async function fetchQuotes(symbols?: string[]): Promise<QuoteItem[]> {
  const params: Record<string, string> = {}
  if (symbols && symbols.length > 0) {
    params.symbols = symbols.join(',')
  }
  // 后端返回 { success, data: [...] }，request 直接返回响应体
  const response = await request<MarketApiResponse<any[]>>('/market/quotes', {
    method: 'GET',
    params,
  })
  // 解包 data 数组并标准化每条数据
  const list = Array.isArray(response?.data) ? response.data : []
  return list.map(normalizeQuote)
}

/** 获取 K 线数据
 *  后端路由: GET /api/v1/market/kline/{symbol}?period=daily&count=100
 *  映射: date→time, period=daily→1d
 */
export async function fetchKLine(
  symbol: string,
  period: '1d' | '1w' | '1m' = '1d',
  limit = 100
): Promise<MarketKLine> {
  // period 映射: 前端 1d/1w/1m → 后端 daily/weekly/monthly
  const periodMap: Record<string, string> = { '1d': 'daily', '1w': 'weekly', '1m': 'monthly' }
  const response = await request<{ success: boolean; data: any[]; symbol: string }>(
    `/market/kline/${symbol}`,
    {
      method: 'GET',
      params: { period: periodMap[period] || 'daily', count: limit },
    }
  )
  return {
    symbol: response?.symbol || symbol,
    period,
    data: Array.isArray(response?.data)
      ? response.data.map((r: any) => ({
          time: r.date || r.time || '',
          open: r.open ?? 0,
          high: r.high ?? 0,
          low: r.low ?? 0,
          close: r.close ?? 0,
          volume: r.volume ?? 0,
        }))
      : [],
  }
}

// ──────────────────────────────────────────────
// T-M009 行情详情 API
// ──────────────────────────────────────────────

export interface KLineItem {
  date: string
  open: number
  close: number
  high: number
  low: number
  volume: number
}

export interface StockDetail {
  symbol: string
  name: string
  market: string
  price: number
  change: number
  change_pct: number
  open: number
  high: number
  low: number
  prev_close: number
  volume: number
  amount: number
  turnover_rate: number | null
  pe_ratio: number | null
  pb_ratio: number | null
  market_cap: number | null
  circul_cap: number | null
  ma5: number | null
  ma10: number | null
  ma20: number | null
  ma60: number | null
  ma5_pct: number | null
  ma20_pct: number | null
  rsi_6: number | null
  rsi_14: number | null
  macd_value: number | null
  macd_signal: number | null
  macd_hist: number | null
  boll_upper: number | null
  boll_mid: number | null
  boll_lower: number | null
  klines_daily: KLineItem[]
  klines_weekly: KLineItem[]
}

/** 实时行情快照（对接 detail 页面） */
export interface QuoteSnapshot {
  symbol: string
  name: string
  market: string
  price: number
  change: number
  change_pct: number
  open: number
  high: number
  low: number
  prev_close: number
  volume: number
  amount: number
  turnover_rate: number | null
  pe_ratio: number | null
  pb_ratio: number | null
  market_cap: number | null
  update_time: string
}

/** K线数据点（对接 detail 页面 KlineChart） */
export interface KlinePoint {
  date: string
  open: number
  close: number
  high: number
  low: number
  volume: number
  amount?: number
  change_pct?: number
}

/** 获取单股实时行情 */
export async function fetchQuote(symbol: string): Promise<QuoteSnapshot> {
  const detail = await marketApi.getDetail(symbol)
  const d = detail?.data || detail || {}
  return {
    symbol: d.symbol || symbol,
    name: d.name || symbol,
    market: d.market || 'A',
    price: d.price ?? 0,
    change: d.change ?? 0,
    change_pct: d.change_pct ?? 0,
    open: d.open ?? 0,
    high: d.high ?? 0,
    low: d.low ?? 0,
    prev_close: d.prev_close ?? 0,
    volume: d.volume ?? 0,
    amount: d.amount ?? 0,
    turnover_rate: d.turnover_rate ?? null,
    pe_ratio: d.pe_ratio ?? null,
    pb_ratio: d.pb_ratio ?? null,
    market_cap: d.market_cap ?? null,
    update_time: d.update_time || new Date().toISOString(),
  }
}

/** 获取K线（对接 detail 页面 KlineChart） */
export async function fetchKline(params: {
  symbol: string
  period?: 'day' | 'week' | 'month'
  count?: number
}): Promise<{ symbol: string; name: string; period: string; points: KlinePoint[] }> {
  const { symbol, period = 'day', count = 60 } = params
  const periodMap: Record<string, string> = { day: 'daily', week: 'weekly', month: 'monthly' }
  const res = await request<any>(`/market/kline/${symbol}`, {
    method: 'GET',
    params: { period: periodMap[period] || 'daily', count },
  })
  const data = res?.data || res || {}
  const points: KlinePoint[] = (Array.isArray(data) ? data : data.data || [])
    .map((r: any) => ({
      date: r.date || r.time || '',
      open: r.open ?? 0,
      close: r.close ?? 0,
      high: r.high ?? 0,
      low: r.low ?? 0,
      volume: r.volume ?? 0,
      amount: r.amount,
      change_pct: r.change_pct,
    }))
  return {
    symbol: data.symbol || symbol,
    name: data.name || symbol,
    period,
    points,
  }
}

export const marketApi = {
  getDetail: (symbol: string) => request<any>(`/market/detail/${symbol}`),
}
