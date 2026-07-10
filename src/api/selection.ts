/**
 * 选股 API
 * 后端端点: /api/v1/selection/recommend, /api/v1/selection/daily-picks
 * 个股诊断: /api/v1/analysis/diagnose/{symbol}
 * 自选操作: /api/v1/watchlist
 */
import { request } from '@/utils/request'
import { cachedRequest, clearCache } from '@/utils/cache'

/** Agent 信号 */
export interface AgentSignal {
  agent: string
  action: 'BUY' | 'SELL' | 'HOLD'
  confidence: number
  reasoning: string
  score: number
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

/** 单个 Agent 评分详情 */
export interface AgentScoreDetail {
  agent: string
  score: number
  confidence: number
  reasoning: string
  reason_codes: string[]
}

/** 单股详情分析 */
export interface StockAnalysisDetail {
  symbol: string
  name: string
  market: 'A' | 'HK' | 'US'
  current_price: number
  change: number
  change_pct: number
  currency: 'CNY' | 'HKD' | 'USD'
  signal_id: string
  action: 'BUY' | 'ADD' | 'HOLD' | 'REDUCE' | 'SELL'
  confidence: number
  reason_codes: string[]
  reasoning: string
  target_price?: number
  stop_loss?: number
  take_profit?: number
  tags?: string[]
  agents: AgentScoreDetail[]
  generated_at: string
}

/** 候选池股票条目 */
export interface CandidateStock {
  rank: number
  symbol: string
  name: string
  market: 'A' | 'HK' | 'US'
  coarse_score: number
  analyst_score: number
  industry: string
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

// ── API 方法 ──

/** 获取推荐选股结果 (GET /selection/recommend) */
export function fetchCommitteeResults(): Promise<CommitteeResult[]> {
  return cachedRequest(
    'selection:committee',
    () => request<any>('/selection/recommend', { method: 'GET' })
      .then(res => {
        // 后端返回 { success, picks: [...] } 或 { data: [...] } 或直接数组
        const raw = res?.data || res?.picks || res || []
        const list = Array.isArray(raw) ? raw : raw.items || raw.results || []
        return list.map(normalizeCommitteeResult)
      })
  )
}

/** 获取每日精选 (GET /selection/daily-picks) */
export function fetchDailyPicks(): Promise<CommitteeResult[]> {
  return cachedRequest(
    'selection:dailyPicks',
    () => request<any>('/selection/daily-picks', { method: 'GET' })
      .then(res => {
        const raw = res?.data || res?.picks || res || []
        const list = Array.isArray(raw) ? raw : raw.items || raw.results || []
        return list.map(normalizeCommitteeResult)
      })
  )
}

/** 获取单股详细分析 → 后端 /analysis/diagnose/{symbol} */
export function fetchStockDetail(symbol: string): Promise<StockAnalysisDetail> {
  return cachedRequest(
    'selection:stockDetail',
    () => request<any>(`/analysis/diagnose/${encodeURIComponent(symbol)}`, { method: 'GET' })
      .then(res => normalizeStockDetail(res?.data || res, symbol)),
    { symbol },
    { ttl: 5 * 60 * 1000 }
  )
}

/** 获取策略列表（后端暂无，返回模拟空） */
export function fetchStrategies(): Promise<StrategyInfo[]> {
  return Promise.resolve([])
}

/** 添加自选 POST /watchlist */
export function addToWatchlist(symbol: string): Promise<void> {
  return request('/watchlist', { method: 'POST', data: { symbol } })
}

/** 移除自选 DELETE /watchlist/{symbol} */
export function removeFromWatchlist(symbol: string): Promise<void> {
  return request(`/watchlist/${encodeURIComponent(symbol)}`, { method: 'DELETE' })
}

/** 获取候选池 → 复用 /selection/recommend */
export function fetchCandidates(params: {
  page?: number
  page_size?: number
  score_min?: number
  score_max?: number
  industry?: string
  sort_by?: 'coarse_score' | 'analyst_score' | 'rank'
}): Promise<CandidatesResponse> {
  return request<any>('/selection/recommend', {
    method: 'GET',
    params: {
      page: params.page ?? 1,
      page_size: params.page_size ?? 20,
    },
  }).then(res => {
    const raw = res?.data || res?.picks || res || []
    const list = Array.isArray(raw) ? raw : raw.items || raw.results || []
    const mapped: CandidateStock[] = list.map((item: any, idx: number) => ({
      rank: item.rank || idx + 1,
      symbol: item.symbol || '',
      name: item.name || item.symbol || '',
      market: item.market || 'A',
      coarse_score: item.coarse_score ?? item.score ?? 50,
      analyst_score: item.analyst_score ?? item.confidence ?? 50,
      industry: item.industry || '综合',
      current_price: item.price ?? item.current_price,
      change_pct: item.change_pct,
    }))
    return {
      items: mapped,
      total: mapped.length,
      page: params.page || 1,
      page_size: params.page_size || 20,
      has_more: false,
    }
  })
}

/** 获取行业分布列表（暂无专用端点，从推荐中提取） */
export function fetchIndustries(): Promise<string[]> {
  return request<any>('/selection/recommend', { method: 'GET' })
    .then(res => {
      const raw = res?.data || res?.picks || res || []
      const list = Array.isArray(raw) ? raw : raw.items || raw.results || []
      const industries = new Set<string>()
      list.forEach((item: any) => {
        if (item.industry) industries.add(item.industry)
      })
      return Array.from(industries).sort()
    })
}

/** 清除选股相关缓存 */
export function clearSelectionCache(): void {
  clearCache('selection:committee')
  clearCache('selection:dailyPicks')
  clearCache('selection:stockDetail')
}

// ── 数据标准化函数 ──

function normalizeCommitteeResult(raw: any): CommitteeResult {
  // 后端返回: { symbol, name, score, factors: [{name, value, score, weight}] }
  const score = raw.score ?? raw.final_confidence ?? raw.confidence ?? 0
  const factors = Array.isArray(raw.factors) ? raw.factors : []
  return {
    symbol: raw.symbol || '',
    name: raw.name || raw.symbol || '',
    final_action: raw.action || raw.final_action || raw.recommendation
      || (score >= 60 ? 'BUY' : score >= 40 ? 'HOLD' : 'SELL'),
    final_confidence: score,
    signals: factors.map((f: any) => ({
      agent: f.name || f.agent || f.source || '',
      action: f.action || (f.score >= 60 ? 'BUY' : f.score >= 40 ? 'HOLD' : 'SELL'),
      confidence: f.score ?? f.confidence ?? 0,
      reasoning: f.reasoning || f.reason || `因子分值: ${f.score ?? 0}`,
      score: f.score ?? 0,
    })),
    summary: raw.summary || raw.reasoning || raw.reason || '',
    generated_at: raw.generated_at || raw.timestamp || new Date().toISOString(),
  }
}

function normalizeStockDetail(raw: any, symbol: string): StockAnalysisDetail {
  // 后端返回 { success, data: { stock, reason_codes, reasoning, rating, confidence, action, agents, generated_at } }
  const stock = raw.stock || raw

  // action: 可能是字符串 "REDUCE" 或对象 { action: "reduce", text: "..." }
  let actionStr: string = 'HOLD'
  if (typeof raw.action === 'string') {
    actionStr = raw.action.toUpperCase()
  } else if (raw.action && typeof raw.action.action === 'string') {
    const m: Record<string, string> = { buy: 'BUY', add: 'ADD', hold: 'HOLD', reduce: 'REDUCE', sell: 'SELL', partial_sell: 'REDUCE' }
    actionStr = m[raw.action.action] || 'HOLD'
  }

  // agents: 优先使用后端返回的 agents 数组，降级到 signals
  const agentsRaw = Array.isArray(raw.agents) ? raw.agents : (Array.isArray(raw.signals) ? raw.signals : [])

  return {
    symbol: stock.symbol || symbol,
    name: stock.name || symbol,
    market: stock.market || 'A',
    current_price: stock.price ?? stock.current_price ?? 0,
    change: stock.change ?? 0,
    change_pct: stock.change_pct ?? 0,
    currency: stock.currency || 'CNY',
    signal_id: raw.signal_id || stock.signal_id || '',
    action: actionStr,
    confidence: raw.confidence ?? 0,
    reason_codes: raw.reason_codes || [],
    reasoning: raw.reasoning || raw.rating_text || '',
    target_price: raw.target_price || stock.target_price,
    stop_loss: raw.stop_loss || stock.stop_loss,
    take_profit: raw.take_profit || stock.take_profit,
    tags: raw.tags,
    agents: agentsRaw.map((s: any, i: number) => ({
      agent: s.agent || s.name || `Agent${i + 1}`,
      score: s.score ?? s.value ?? 0,
      confidence: s.confidence ?? s.value ?? 0,
      reasoning: s.reasoning || s.desc || '',
      reason_codes: s.reason_codes || [],
    })),
    generated_at: raw.generated_at || stock.generated_at || new Date().toISOString(),
  }
}
