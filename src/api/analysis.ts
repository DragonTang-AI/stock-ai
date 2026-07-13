/**
 * 分析/看板 API
 * 后端端点: /api/v1/portfolio/account, /positions, /analytics, /trades
 *             /api/v1/analysis/diagnose, /analysis/market/temperature
 */
import { request } from '@/utils/request'
import { cachedRequest } from '@/utils/cache'

export interface EquityPoint { date: string; equity: number; benchmark?: number }
export interface AttributionItem { label: string; contribution: number; percentage: number }
export interface DashboardSummary {
  totalReturn: number; annualizedReturn: number; beatBenchmark: number
  sharpeRatio: number; maxDrawdown: number; winRate: number
}
export interface StatisticsData {
  winRate: number; profitLossRatio: number
  maxSingleProfit: number; maxSingleLoss: number
  sharpeRatio: number; maxDrawdown: number
}
export interface EquityCurveData {
  dates: string[]; equity: number[]; benchmark?: number[]
}

/** 获取看板概览 → /portfolio/analytics */
export function fetchDashboardSummary(): Promise<DashboardSummary> {
  return cachedRequest(
    'analysis:dashboardSummary',
    () => request<any>('/portfolio/analytics', { method: 'GET' })
      .then(res => {
        const d = res?.data || res || {}
        return {
          totalReturn: d.total_return ?? d.totalReturn ?? 0,
          annualizedReturn: d.annualized_return ?? d.annualizedReturn ?? 0,
          beatBenchmark: d.beat_benchmark ?? d.beatBenchmark ?? 0,
          sharpeRatio: d.sharpe_ratio ?? d.sharpeRatio ?? 0,
          maxDrawdown: d.max_drawdown ?? d.maxDrawdown ?? 0,
          winRate: d.win_rate ?? d.winRate ?? 0,
        }
      })
  )
}

/** 获取统计指标 → /portfolio/analytics */
export function fetchStatistics(): Promise<StatisticsData> {
  return cachedRequest(
    'analysis:statistics',
    () => request<any>('/portfolio/analytics', { method: 'GET' })
      .then(res => {
        const d = res?.data || res || {}
        return {
          winRate: d.win_rate ?? d.winRate ?? 0,
          profitLossRatio: d.profit_loss_ratio ?? d.profitLossRatio ?? 0,
          maxSingleProfit: d.max_single_profit ?? d.maxSingleProfit ?? 0,
          maxSingleLoss: d.max_single_loss ?? d.maxSingleLoss ?? 0,
          sharpeRatio: d.sharpe_ratio ?? d.sharpeRatio ?? 0,
          maxDrawdown: d.max_drawdown ?? d.maxDrawdown ?? 0,
        }
      })
  )
}

/** 获取收益率曲线 → /portfolio/analytics */
export function fetchEquityCurve(period: string): Promise<EquityCurveData> {
  return cachedRequest(
    'analysis:equityCurve',
    () => request<any>('/portfolio/analytics', {
      method: 'GET',
      params: { period },
    }).then(res => {
      const d = res?.data || res || {}
      const dates = d.dates || d.equity_curve?.map((p: any) => p.date) || []
      const equity = d.equity || d.equity_curve?.map((p: any) => p.value) || []
      const benchmark = d.benchmark || d.equity_curve?.map((p: any) => p.benchmark)
      return {
        dates,
        equity,
        benchmark: benchmark?.some((v: any) => v != null) ? benchmark : undefined,
      }
    }),
    { period },
    { ttl: 5 * 60 * 1000 }
  )
}

/** 获取归因分析 → /portfolio/analytics */
export function fetchAttribution(period: string): Promise<{ items: AttributionItem[] }> {
  return cachedRequest(
    'analysis:attribution',
    () => request<any>('/portfolio/analytics', {
      method: 'GET',
      params: { period },
    }).then(res => {
      const d = res?.data || res || {}
      const raw = d.attribution || d.items || []
      return {
        items: raw.map((item: any) => ({
          label: item.label || item.name || '',
          contribution: item.contribution ?? 0,
          percentage: item.percentage ?? 0,
        })),
      }
    }),
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

/** 获取资产概览 → /portfolio/account */
export function fetchAssetOverview(): Promise<AssetOverview> {
  return cachedRequest(
    'analysis:assetOverview',
    () => request<any>('/portfolio/account', { method: 'GET' })
      .then(res => {
        const d = res?.data || res || {}
        return {
          totalAssets: d.total_equity ?? d.total_assets ?? d.totalAssets ?? 0,
          todayPnl: d.today_pnl ?? d.todayPnl ?? 0,
          positionPnl: d.profit ?? d.unrealized_pnl ?? d.positionPnl ?? 0,
          positionValue: d.market_value ?? d.positionValue ?? 0,
          availableCash: d.balance ?? d.available_cash ?? d.availableCash ?? 0,
        }
      }),
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

/** 获取持仓分布 → /portfolio/positions */
export function fetchPositionDistribution(): Promise<PositionDistItem[]> {
  return request<any>('/portfolio/positions', { method: 'GET' })
    .then(res => {
      const d = res?.data || res || {}
      const positions = d.positions || d || []
      const list = Array.isArray(positions) ? positions : []
      return list.map((item: any) => ({
        name: item.name || item.symbol || '',
        value: item.market_value ?? item.value ?? 0,
        symbol: item.symbol || '',
      }))
    })
}
