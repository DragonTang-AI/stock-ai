/**
 * 分析/看板 API
 * 对应后端 /api/v1/portfolio/* 分析扩展
 * 后端统一返回 {success, data}，这里 unwrap data
 */
import { request } from '@/utils/request'

export interface EquityPoint { date: string; equity: number; benchmark?: number }
export interface AttributionItem { label: string; contribution: number; percentage: number }
export interface DashboardSummary {
  totalReturn: number; annualizedReturn: number; beatBenchmark: number;
  sharpeRatio: number; maxDrawdown: number; winRate: number;
}
export interface StatisticsData {
  winRate: number; profitLossRatio: number;
  maxSingleProfit: number; maxSingleLoss: number;
  sharpeRatio: number; maxDrawdown: number;
}
export interface EquityCurveData {
  dates: string[]; equity: number[]; benchmark?: number[];
}

/** 获取看板概览 */
export function fetchDashboardSummary(): Promise<DashboardSummary> {
  return request<{ success: boolean; data: DashboardSummary }>(
    '/portfolio/summary', { method: 'GET' }
  ).then(res => res.data)
}

/** 获取统计指标 */
export function fetchStatistics(): Promise<StatisticsData> {
  return request<{ success: boolean; data: StatisticsData }>(
    '/portfolio/statistics', { method: 'GET' }
  ).then(res => res.data)
}

/** 获取收益率曲线（unwrap + 转 dates/equity 数组） */
export function fetchEquityCurve(period: string): Promise<EquityCurveData> {
  return request<{ success: boolean; data: EquityPoint[] }>(
    '/portfolio/equity_curve', { method: 'GET', params: { period } }
  ).then(res => ({
    dates: res.data.map(p => p.date),
    equity: res.data.map(p => p.equity),
    benchmark: res.data[0]?.benchmark !== undefined
      ? res.data.map(p => p.benchmark as number)
      : undefined,
  }))
}

/** 获取归因分析 */
export function fetchAttribution(period: string): Promise<{ items: AttributionItem[] }> {
  return request<{ success: boolean; data: AttributionItem[] }>(
    '/portfolio/attribution', { method: 'GET', params: { period } }
  ).then(res => ({ items: res.data }))
}
