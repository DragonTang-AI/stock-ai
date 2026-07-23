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
