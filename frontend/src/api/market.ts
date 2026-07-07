/**
 * 行情 API
 * 对应后端 /api/v1/market
 */
import { request } from '@/utils/request'
import { cachedRequest, clearCache } from '@/utils/cache'

/** K线数据点 */
export interface KlinePoint {
  date: string       // YYYY-MM-DD
  open: number
  close: number
  high: number
  low: number
  volume: number     // 手
  amount: number     // 成交额（元）
  change_pct: number // 涨跌幅 %
}

/** 实时行情快照 */
export interface QuoteSnapshot {
  code: string
  name: string
  price: number
  change: number
  change_pct: number
  open: number
  high: number
  low: number
  pre_close: number
  volume: number
  amount: number
  turnover: number     // 换手率 %
  high_low: number     // 振幅 %
  update_time: string
}

export interface KlineResponse {
  code: string
  name: string
  period: string
  points: KlinePoint[]
}

/** 获取 K 线数据（缓存 10 分钟，K线数据变化慢） */
export function fetchKline(params: {
  code: string
  period?: 'day' | 'week' | 'month'
  count?: number
}): Promise<KlineResponse> {
  return cachedRequest(
    'market:kline',
    () => request<{ success: boolean; data: KlineResponse }>(
      '/market/kline', { method: 'GET', params }
    ).then(res => res.data),
    params,
    { ttl: 10 * 60 * 1000 }
  )
}

/** 获取实时行情（缓存 30 秒，行情变化快） */
export function fetchQuote(code: string): Promise<QuoteSnapshot> {
  return cachedRequest(
    'market:quote',
    () => request<{ success: boolean; data: QuoteSnapshot }>(
      `/market/quote/${code}`, { method: 'GET' }
    ).then(res => res.data),
    { code },
    { ttl: 30 * 1000 }
  )
}

/** 清除行情相关缓存 */
export function clearMarketCache(): void {
  clearCache('market:quote')
  clearCache('market:kline')
}
