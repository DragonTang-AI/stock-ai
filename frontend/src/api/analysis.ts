/**
 * 分析/看板 API
 * 对应后端 /api/v1/portfolio/* 分析扩展
 */
import { request } from '@/utils/request'

/** 收益率曲线数据点 */
export interface EquityPoint {
  date: string
  equity: number
  benchmark?: number
}

/** 归因分析项 */
export interface AttributionItem {
  label: string
  contribution: number
  percentage: number
}

/** 看板概览 */
export interface DashboardSummary {
  totalReturn: number
  annualizedReturn: number
  beatBenchmark: number
  sharpeRatio: number
  maxDrawdown: number
  winRate: number
}

/** 获取收益率曲线 */
export function fetchEquityCurve(period: string): Promise<{ dates: string[]; equity: number[]; benchmark?: number[] }> {
  return request({ url: '/portfolio/equity_curve', method: 'GET', data: { period } })
}

/** 获取归因分析 */
export function fetchAttribution(period: string): Promise<{ items: AttributionItem[] }> {
  return request({ url: '/portfolio/attribution', method: 'GET', data: { period } })
}

/** 获取看板概览 */
export function fetchDashboardSummary(): Promise<DashboardSummary> {
  return request({ url: '/portfolio/summary', method: 'GET' })
}

/** 获取统计指标 */
export function fetchStatistics(): Promise<{
  winRate: number
  profitLossRatio: number
  maxSingleProfit: number
  maxSingleLoss: number
  sharpeRatio: number
  maxDrawdown: number
}> {
  return request({ url: '/portfolio/statistics', method: 'GET' })
}
