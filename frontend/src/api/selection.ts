/**
 * 选股 API
 * 对应后端 /api/v1/selection
 */
import { request } from '@/utils/request'

/** Agent 信号 */
export interface AgentSignal {
  agent: string          // 技术面 / 基本面 / 舆情 / 情绪
  action: 'BUY' | 'SELL' | 'HOLD'
  confidence: number     // 0~1
  reasoning: string      // 分析理由
  score: number          // 评分
}

/** 委员会汇总结果 */
export interface CommitteeResult {
  symbol: string
  name: string
  final_action: string
  final_confidence: number
  signals: AgentSignal[]
  summary: string
  generated_at: string
}

/** 策略 */
export interface StrategyInfo {
  id: string
  name: string
  description: string
  result_count: number
  benchmark_return?: number
  is_active: boolean
}

/** 获取委员会选股结果 */
export function fetchCommitteeResults(): Promise<CommitteeResult[]> {
  return request<{ success: boolean; data: CommitteeResult[] }>(
    '/selection/committee', { method: 'GET' }
  ).then(res => res.data)
}

/** 获取策略列表 */
export function fetchStrategies(): Promise<StrategyInfo[]> {
  return request<{ success: boolean; data: StrategyInfo[] }>(
    '/selection/strategies', { method: 'GET' }
  ).then(res => res.data)
}

/** 添加自选 */
export function addToWatchlist(symbol: string): Promise<void> {
  return request('/watchlist/add', { method: 'POST', data: { symbol } })
}

/** 移除自选 */
export function removeFromWatchlist(symbol: string): Promise<void> {
  return request('/watchlist/remove', { method: 'POST', data: { symbol } })
}
