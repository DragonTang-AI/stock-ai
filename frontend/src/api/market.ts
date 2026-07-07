/**
 * 行情 API
 * 对应后端 /api/v1/market
 */
import { request } from '@/utils/request'

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

/** 获取 K 线数据 */
export function fetchKline(params: {
  code: string
  period?: 'day' | 'week' | 'month'
  count?: number
}): Promise<KlineResponse> {
  return request<{ success: boolean; data: KlineResponse }>(
    '/market/kline', { method: 'GET', params }
  ).then(res => res.data)
}

/** 获取实时行情 */
export function fetchQuote(code: string): Promise<QuoteSnapshot> {
  return request<{ success: boolean; data: QuoteSnapshot }>(
    `/market/quote/${code}`, { method: 'GET' }
  ).then(res => res.data)
}
