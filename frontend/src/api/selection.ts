/**
 * 选股 API
 * 对应后端 /api/v1/selection
 */
import { request } from '@/utils/request'
import { cachedRequest, clearCache } from '@/utils/cache'

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

// ---- T-M021: 选股详情页类型 ----

/** 单个 Agent 评分详情 */
export interface AgentScoreDetail {
  agent: string          // Technical | Fundamental | Sentiment | Risk
  score: number          // 0-100 评分
  confidence: number     // 0-100 置信度
  reasoning: string      // 分析理由
  reason_codes: string[] // 推荐理由编码
}

/** 单股详情分析（GET /api/v1/selection/stock/{symbol}） */
export interface StockAnalysisDetail {
  symbol: string
  name: string
  market: 'A' | 'HK' | 'US'
  current_price: number
  change: number
  change_pct: number
  currency: 'CNY' | 'HKD' | 'USD'
  // Signal 字段（对齐 signal.schema.json）
  signal_id: string
  action: 'BUY' | 'ADD' | 'HOLD' | 'REDUCE' | 'SELL'
  confidence: number       // 0-100
  reason_codes: string[]
  reasoning: string
  target_price?: number
  stop_loss?: number
  take_profit?: number
  tags?: string[]
  // 4-Agent 详细评分
  agents: AgentScoreDetail[]
  generated_at: string
}

// ---- API 方法 ----

/** 获取委员会选股结果（缓存 5 分钟） */
export function fetchCommitteeResults(): Promise<CommitteeResult[]> {
  return cachedRequest(
    'selection:committee',
    () => request<{ signals: CommitteeResult[] }>(
      '/selection/committee', { method: 'GET' }
    ).then(res => res.signals)
  )
}

/** 获取单股详细分析 */
export function fetchStockDetail(symbol: string): Promise<StockAnalysisDetail> {
  return cachedRequest(
    'selection:stockDetail',
    () => request<{ success: boolean; data: StockAnalysisDetail }>(
      `/selection/stock/${encodeURIComponent(symbol)}`, { method: 'GET' }
    ).then(res => res.data),
    { symbol },
    { ttl: 5 * 60 * 1000 }
  )
}

/** 获取策略列表（缓存 10 分钟） */
export function fetchStrategies(): Promise<StrategyInfo[]> {
  return cachedRequest(
    'selection:strategies',
    () => request<{ success: boolean; data: StrategyInfo[] }>(
      '/selection/strategies', { method: 'GET' }
    ).then(res => res.data),
    undefined,
    { ttl: 10 * 60 * 1000 }
  )
}

/** 添加自选 */
export function addToWatchlist(symbol: string): Promise<void> {
  return request('/watchlist/add', { method: 'POST', data: { symbol } })
}

/** 移除自选 */
export function removeFromWatchlist(symbol: string): Promise<void> {
  return request('/watchlist/remove', { method: 'POST', data: { symbol } })
}

// ---- T-M022: 候选池浏览 ----

/** 候选池股票条目 */
export interface CandidateStock {
  rank: number           // 排名
  symbol: string
  name: string
  market: 'A' | 'HK' | 'US'
  coarse_score: number    // 粗筛分 0-100
  analyst_score: number   // 分析师气概览 0-100
  industry: string        // 行业
  current_price?: number
  change_pct?: number
}

/** 候选池分页响应 */
export interface CandidatesResponse {
  items: CandidateStock[]
  total: number
  page: number
  page_size: number
  has_more: boolean
}

/**
 * 获取候选池列表
 * GET /api/v1/selection/candidates
 */
export function fetchCandidates(params: {
  page?: number
  page_size?: number
  score_min?: number
  score_max?: number
  industry?: string
  sort_by?: 'coarse_score' | 'analyst_score' | 'rank'
}): Promise<CandidatesResponse> {
  return request<{ success: boolean; data: CandidatesResponse }>(
    '/selection/candidates',
    {
      method: 'GET',
      params: {
        page: params.page ?? 1,
        page_size: params.page_size ?? 20,
        score_min: params.score_min,
        score_max: params.score_max,
        industry: params.industry,
        sort_by: params.sort_by,
      },
    }
  ).then(res => res.data)
}

/**
 * 获取行业分布列表（用于筛选，缓存 30 分钟）
 * GET /api/v1/selection/industries
 */
export function fetchIndustries(): Promise<string[]> {
  return cachedRequest(
    'selection:industries',
    () => request<{ success: boolean; data: string[] }>(
      '/selection/industries',
      { method: 'GET' }
    ).then(res => res.data),
    undefined,
    { ttl: 30 * 60 * 1000 }
  )
}

/** 清除选股相关缓存 */
export function clearSelectionCache(): void {
  clearCache('selection:committee')
  clearCache('selection:strategies')
  clearCache('selection:industries')
  clearCache('selection:stockDetail')
}
