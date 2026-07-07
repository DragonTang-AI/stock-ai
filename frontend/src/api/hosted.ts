/**
 * AI托管 API
 * 对应后端 /api/v1/hosted/*
 */
import { request } from '@/utils/request'

export interface HostedStatus {
  enabled: boolean
  mode: string
  confidence_threshold: number
  max_position_ratio: number
  today_trades: number
  today_pnl: number
  updated_at: string
}

export interface HostedConfig {
  confidence_threshold?: number
  max_position_ratio?: number
}

export interface HostedLog {
  id: string
  action: string
  symbol: string
  confidence: number
  result: string
  message: string
  created_at: string
}

export interface HostedTrigger {
  triggered: boolean
  symbol: string
  action: string
  reason: string
}

/** 获取AI托管状态 */
export function getHostedStatus(): Promise<HostedStatus> {
  return request({ url: '/hosted/status', method: 'GET' })
}

/** 切换AI托管开关 */
export function switchHosted(enabled: boolean): Promise<HostedStatus> {
  return request({ url: '/hosted/switch', method: 'POST', data: { enabled } })
}

/** 修改风控参数 */
export function updateHostedConfig(config: HostedConfig): Promise<HostedStatus> {
  return request({ url: '/hosted/config', method: 'PATCH', data: config })
}

/** 获取执行日志 */
export function getHostedLogs(params?: { limit?: number; offset?: number }): Promise<{
  logs: HostedLog[]
  total: number
}> {
  return request({ url: '/hosted/logs', method: 'GET', data: params })
}

/** 手动触发信号（调试用） */
export function triggerHosted(symbol: string): Promise<HostedTrigger> {
  return request({ url: '/hosted/trigger', method: 'POST', data: { symbol } })
}
