/**
 * AI托管 API
 * 对应后端 /api/v1/hosted/*
 * 后端字段名严格对齐 schemas/hosted.py
 */
import { request } from '@/utils/request'
import { cachedRequest, clearCache } from '@/utils/cache'

export type HostedMode = 'MANUAL' | 'AI_HOSTED'

export type RiskLevel = 'conservative' | 'balanced' | 'aggressive'
export const RiskLevelLabel: Record<RiskLevel, string> = {
  conservative: '保守',
  balanced: '平衡',
  aggressive: '激进',
}

/** 状态响应（对齐 HostedStatusResponse） */
export interface HostedStatus {
  mode: HostedMode
  enabled_at: string | null
  disabled_at: string | null
  is_active: boolean
  risk_level: RiskLevel
  max_position_ratio: number | null
  max_single_trade_ratio: number | null
  min_confidence: number | null
  single_trade_limit: number | null
  daily_trade_limit: number | null
  industry_concentration: number | null
  auto_stop_loss: boolean
  total_trades: number
  active_signals_today: number
  daily_loss_pct: number | null
  is_audit_mode: boolean
  disclaimer: string | null
}

/** 开关请求（对齐 HostedSwitchRequest） */
export interface HostedSwitchRequest {
  mode: HostedMode
}

/** 风控配置请求（对齐 HostedConfigRequest） */
export interface HostedConfigRequest {
  risk_level?: RiskLevel
  max_position_ratio?: number
  max_single_trade_ratio?: number
  min_confidence?: number
  single_trade_limit?: number
  daily_trade_limit?: number
  industry_concentration?: number
  auto_stop_loss?: boolean
}

/** 日志项（对齐 HostedLogItem） */
export interface HostedLog {
  id: string
  signal_id: string | null
  order_id: number | null
  action: string  // BUY | SELL
  symbol: string
  target_price: number | null
  qty: number | null
  reason: string | null
  status: string  // TRIGGERED | BLOCKED | SKIPPED | ERROR
  error: string | null
  created_at: string
}

/** 信号日志项（对齐信号日志列表） */
export interface HostedSignal {
  id: string
  signal_id: string
  created_at: string
  action: string // BUY | ADD | HOLD | REDUCE | SELL
  symbol: string
  price: number | null
  confidence: number
  status: string // PENDING | EXECUTED | REJECTED | CANCELLED | EXPIRED
  reason: string | null
}

/** 信号→订单请求（对齐 SignalToOrderRequest） */
export interface SignalToOrderRequest {
  symbol: string
  signal_id: string
  action: string  // BUY | SELL
  confidence: number
  target_price: number
  reasoning?: string
}

/** 获取 AI 托管状态（缓存 30 秒） */
export function getHostedStatus(): Promise<HostedStatus> {
  return cachedRequest(
    'hosted:status',
    () => request<HostedStatus>('/hosted/status', { method: 'GET' }),
    undefined,
    { ttl: 30 * 1000 }
  )
}

/** 切换 AI 托管（开启传 AI_HOSTED，关闭传 MANUAL） */
export function switchHosted(mode: HostedMode): Promise<HostedStatus> {
  clearCache('hosted:status')
  return request<HostedStatus>('/hosted/switch', { method: 'POST', data: { mode } })
}

/** 修改风控参数（需先开启托管） */
export function updateHostedConfig(config: HostedConfigRequest): Promise<HostedStatus> {
  clearCache('hosted:status')
  return request<HostedStatus>('/hosted/config', { method: 'PATCH', data: config })
}

/** 获取执行日志（limit/offset 作为查询参数） */
export function getHostedLogs(params?: { limit?: number; offset?: number }): Promise<{
  total: number; logs: HostedLog[];
}> {
  return request<{ total: number; logs: HostedLog[] }>(
    '/hosted/logs', { method: 'GET', params }
  )
}

/** 获取信号日志列表 */
export function getHostedSignals(params?: { limit?: number; offset?: number }): Promise<{
  total: number; signals: HostedSignal[];
}> {
  return request<{ total: number; signals: HostedSignal[] }>(
    '/hosted/signals', { method: 'GET', params }
  )
}

/** 手动触发信号（用于调试） */
export function triggerHosted(req: SignalToOrderRequest): Promise<{
  success: boolean; data: any;
}> {
  return request('/hosted/trigger', { method: 'POST', data: req })
}
