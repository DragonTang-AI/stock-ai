/**
 * 自选股 / 关注列表 API
 * 对接后端 /api/v1/watchlist/*
 */
import { request } from '@/utils/request'

export interface WatchlistItem {
  id: number
  symbol: string
  name: string
  price: number | null
  change_pct: number | null
  note: string | null
  sort_order: number
  created_at: string
}

export interface WatchlistListResponse {
  success: boolean
  total: number
  data: WatchlistItem[]
}

export interface WatchlistCheckResponse {
  success: boolean
  in_watchlist: boolean
  data?: WatchlistItem
}

export const watchlistApi = {
  /** 获取自选列表（含实时行情） */
  list: (): Promise<WatchlistListResponse> =>
    request('/watchlist', { method: 'GET' }),

  /** 添加自选 */
  add: (symbol: string, note?: string): Promise<any> =>
    request('/watchlist', { method: 'POST', data: { symbol, note: note || '' } }),

  /** 删除自选 */
  remove: (symbol: string): Promise<any> =>
    request(`/watchlist/${symbol}`, { method: 'DELETE' }),

  /** 检查是否在自选 */
  check: (symbol: string): Promise<WatchlistCheckResponse> =>
    request(`/watchlist/check?symbol=${encodeURIComponent(symbol)}`, { method: 'GET' }),

  /** 批量添加 */
  batchAdd: (symbols: string[]): Promise<any> =>
    request('/watchlist/batch', { method: 'POST', data: { symbols } }),
}
