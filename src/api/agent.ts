/**
 * 交易员市场 API
 */
import { request } from '@/utils/request'

export interface AgentTrader {
  id: string
  code_name: string
  tag: string
  avatar_url: string | null
  description: string
  strategy_detail: string | null
  masters: string
  hire_price_points: number
  profit_share_pct: number
  annual_return: number | null
  max_drawdown: number | null
  sharpe_ratio: number | null
  win_rate: number | null
  total_trades: number | null
}

export interface AgentPerformance {
  period: string
  period_end: string
  return_pct: number
  benchmark_return_pct: number | null
  alpha: number | null
  max_drawdown: number | null
  sharpe_ratio: number | null
  win_rate: number | null
}

export interface AgentTraderDetail extends AgentTrader {
  is_hired: boolean
  management_mode: string | null
  hired_at: string | null
  current_pnl: number | null
  recent_performances: AgentPerformance[]
}

export interface AgentMarketList {
  items: AgentTrader[]
  total: number
}

export interface HireAgentResponse {
  user_agent_id: number
  agent_id: string
  points_spent: number
  balance_after: number
  management_mode: string
  expires_at: string | null
  message: string
}

export interface UserAgent {
  id: number
  agent_id: string
  agent: AgentTrader
  status: string
  management_mode: string
  allocated_capital: number | null
  current_pnl: number | null
  hired_at: string
  expires_at: string | null
}

/** 获取交易员市场列表 */
export function getAgentMarket(): Promise<AgentMarketList> {
  return request<AgentMarketList>('/agent/market')
}

/** 获取交易员详情 */
export function getAgentDetail(agentId: string): Promise<AgentTraderDetail> {
  return request<AgentTraderDetail>('/agent/market/' + agentId)
}

/** 雇佣交易员 */
export function hireAgent(agentId: string, managementMode: string): Promise<HireAgentResponse> {
  return request<HireAgentResponse>('/agent/market/' + agentId + '/hire', {
    method: 'POST',
    data: { management_mode: managementMode },
  })
}

/** 获取我的交易员列表 */
export function getMyAgents(): Promise<UserAgent[]> {
  return request<UserAgent[]>('/agent/my-agents')
}

/** 切换管理模式 */
export function updateManagementMode(userAgentId: number, managementMode: string): Promise<any> {
  return request('/agent/my-agents/' + userAgentId + '/mode', {
    method: 'PATCH',
    data: { management_mode: managementMode },
  })
}

/** 解雇交易员 */
export function dismissAgent(userAgentId: number): Promise<any> {
  return request('/agent/my-agents/' + userAgentId, { method: 'DELETE' })
}

// ── 控制台 API ──

export interface ConsoleOverview {
  hire_id: number
  trader_name: string
  trader_tag: string
  management_mode: string
  status: string
  total_assets: number
  unrealized_pnl: number
  today_signals: number
  pending_signals: number
  position_count: number
}

export interface ConsoleSignal {
  id: number
  hire_id: number
  trader_id: string
  symbol: string
  symbol_name: string
  action: string
  price: number
  quantity: number
  confidence: number
  reasoning: string | null
  exec_status: string
  created_at: string
  updated_at: string | null
}

export interface ConsolePortfolio {
  id: number
  hire_id: number
  symbol: string
  symbol_name: string
  quantity: number
  avg_cost: number
  current_price: number | null
  market_value: number | null
  unrealized_pnl: number | null
}

export interface ConsoleTrade {
  id: number
  symbol: string
  symbol_name: string
  action: string
  price: number
  quantity: number
  confidence: number
  reasoning: string | null
  exec_status: string
  executed_at: string | null
}

export interface EquityCurvePoint {
  date: string
  equity: number
  daily_pnl: number
}

/** 获取控制台概览 */
export function getConsoleOverview(hireId: number): Promise<ConsoleOverview> {
  return request<ConsoleOverview>('/agent-console/' + hireId + '/overview')
}

/** 获取信号列表 */
export function getSignals(hireId: number, status?: string): Promise<ConsoleSignal[]> {
  let url = '/agent-console/' + hireId + '/signals'
  if (status) url += '?status=' + status
  return request<ConsoleSignal[]>(url)
}

/** 确认信号执行 */
export function confirmSignal(signalId: number, quantity?: number): Promise<any> {
  return request('/agent-console/signals/' + signalId + '/confirm', {
    method: 'POST',
    data: quantity ? { quantity } : {},
  })
}

/** 忽略信号 */
export function ignoreSignal(signalId: number): Promise<any> {
  return request('/agent-console/signals/' + signalId + '/ignore', { method: 'POST' })
}

/** 获取交易员持仓 */
export function getAgentPortfolio(hireId: number): Promise<ConsolePortfolio[]> {
  return request<ConsolePortfolio[]>('/agent-console/' + hireId + '/portfolio')
}

/** 获取交易日志 */
export function getAgentTrades(hireId: number): Promise<ConsoleTrade[]> {
  return request<ConsoleTrade[]>('/agent-console/' + hireId + '/trades')
}

/** 获取权益曲线 */
export function getEquityCurve(hireId: number): Promise<EquityCurvePoint[]> {
  return request<EquityCurvePoint[]>('/agent-console/' + hireId + '/equity-curve')
}

/** 切换管理模式 */
export function switchMode(hireId: number, mode: string): Promise<any> {
  return request('/agent/my-agents/' + hireId + '/mode', {
    method: 'PATCH',
    data: { management_mode: mode },
  })
}

/** 暂停交易员 */
export function pauseAgent(hireId: number): Promise<any> {
  return request('/agent/my-agents/' + hireId + '/pause', { method: 'POST' })
}

/** 恢复交易员 */
export function resumeAgent(hireId: number): Promise<any> {
  return request('/agent/my-agents/' + hireId + '/resume', { method: 'POST' })
}

/** 终止雇佣 */
export function terminateAgent(hireId: number): Promise<any> {
  return request('/agent/my-agents/' + hireId + '/terminate', { method: 'POST' })
}

/** 手动生成信号 */
export function generateSignals(hireId: number): Promise<ConsoleSignal[]> {
  return request<ConsoleSignal[]>('/agent-console/' + hireId + '/generate-signals', { method: 'POST' })
}
