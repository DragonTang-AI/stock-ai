/**
 * 积分系统 API
 */
import { request } from '@/utils/request'

export interface PointsBalance {
  balance: number
  total_earned: number
  total_spent: number
  updated_at: string | null
}

export interface PointsTransaction {
  id: number
  amount: number
  balance_after: number
  tx_type: string
  reference_id: string | null
  description: string | null
  created_at: string
}

export interface PointsHistory {
  items: PointsTransaction[]
  total: number
}

export interface DailyCheckin {
  success: boolean
  points_earned: number
  balance: number
  consecutive_days: number
}

/** 获取积分余额 */
export function getPointsBalance(): Promise<PointsBalance> {
  return request<PointsBalance>('/points/balance')
}

/** 获取积分流水 */
export function getPointsHistory(page = 1, pageSize = 20): Promise<PointsHistory> {
  return request<PointsHistory>('/points/history', { params: { page, page_size: pageSize } })
}

/** 每日签到 */
export function dailyCheckin(): Promise<DailyCheckin> {
  return request<DailyCheckin>('/points/daily-checkin', { method: 'POST' })
}
