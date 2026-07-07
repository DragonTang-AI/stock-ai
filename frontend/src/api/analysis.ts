/**
 * 分析/看板 API
 * 对应后端 /api/v1/portfolio/* 分析扩展
 */
import { request } from '@/utils/request'

export interface EquityPoint {
  date: string
  equity: number
  benchmark?: number
}

export interface AttributionItem {
  label: string
  contribution: number
  percentage: number
}

export interface DashboardSummary {
  totalReturn: number
  annualizedReturn: number
  beatBenchmark: number
  sharpeRatio: number
  maxDrawdown: number
  winRate: number
}

export function fetchEquityCurve(period: string): Promise<{ dates: string[]; equity: number[]; benchmark?: number[] }> {
  return request('/portfolio/equity_curve', { method: 'GET', params: { period } })
}

export function fetchAttribution(period: string): Promise<{ items: AttributionItem[] }> {
  return request('/portfolio/attribution', { method: 'GET', params: { period } })
}

export function fetchDashboardSummary(): Promise<DashboardSummary> {
  return request('/portfolio/summary', { method: 'GET' })
}

export function fetchStatistics(): Promise<{
  winRate: number
  profitLossRatio: number
  maxSingleProfit: number
  maxSingleLoss: number
  sharpeRatio: number
  maxDrawdown: number
}> {
  return request('/portfolio/statistics', { method: 'GET' })
}
