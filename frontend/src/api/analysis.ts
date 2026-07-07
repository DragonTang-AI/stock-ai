/**
 * 分析/看板 API
 * 对应后端 /api/v1/portfolio/* 分析扩展
 * 后端统一返回 {success, data}，这里 unwrap data
 */
import { request } from '@/utils/request'
import { cachedRequest } from '@/utils/cache'

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

/** 获取看板概览（缓存 5 分钟） */
export function fetchDashboardSummary(): Promise<DashboardSummary> {
  return cachedRequest(
    'analysis:dashboardSummary',
    () => request<{ success: boolean; data: DashboardSummary }>(
      '/portfolio/summary', { method: 'GET' }
    ).then(res => res.data)
  )
}

/** 获取统计指标（缓存 5 分钟） */
export function fetchStatistics(): Promise<StatisticsData> {
  return cachedRequest(
    'analysis:statistics',
    () => request<{ success: boolean; data: StatisticsData }>(
      '/portfolio/statistics', { method: 'GET' }
    ).then(res => res.data)
  )
}

/** 获取收益率曲线 */
export function fetchEquityCurve(period: string): Promise<EquityCurveData> {
  return cachedRequest(
    'analysis:equityCurve',
    () => request<{ success: boolean; data: EquityPoint[] }>(
      '/portfolio/equity_curve', { method: 'GET', params: { period } }
    ).then(res => ({
      dates: res.data.map(p => p.date),
      equity: res.data.map(p => p.equity),
      benchmark: res.data[0]?.benchmark !== undefined
        ? res.data.map(p => p.benchmark as number)
        : undefined,
    })),
    { period },
    { ttl: 5 * 60 * 1000 }
  )
}

/** 获取归因分析（缓存 5 分钟） */
export function fetchAttribution(period: string): Promise<{ items: AttributionItem[] }> {
  return cachedRequest(
    'analysis:attribution',
    () => request<{ success: boolean; data: AttributionItem[] }>(
      '/portfolio/attribution', { method: 'GET', params: { period } }
    ).then(res => ({ items: res.data })),
    { period },
    { ttl: 5 * 60 * 1000 }
  )
}

/** 资产概览 */
export interface AssetOverview {
  totalAssets: number
  todayPnl: number
  positionPnl: number
  positionValue: number
  availableCash: number
}

/** 获取资产概览（缓存 1 分钟） */
export function fetchAssetOverview(): Promise<AssetOverview> {
  return cachedRequest(
    'analysis:assetOverview',
    () => request<{ success: boolean; data: AssetOverview }>(
      '/portfolio/overview', { method: 'GET' }
    ).then(res => res.data),
    undefined,
    { ttl: 60 * 1000 }
  )
}

/** 持仓分布饼图数据 */
export interface PositionDistItem {
  name: string
  value: number
  symbol: string
}

/** 获取持仓分布 */
export function fetchPositionDistribution(): Promise<PositionDistItem[]> {
  return request<{ success: boolean; data: PositionDistItem[] }>(
    '/portfolio/distribution', { method: 'GET' }
  ).then(res => res.data)
}
