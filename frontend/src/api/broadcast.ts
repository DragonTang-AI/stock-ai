/**
 * 定时播报 API
 * 对应后端 /api/v1/broadcast/*
 */
import { request } from '@/utils/request'
import { cachedRequest, clearCache } from '@/utils/cache'

/** 精选推荐条目 */
export interface BroadcastRecommendation {
  symbol: string
  name: string
  confidence: number
  reason: string
}

/** 播报内容 */
export interface BroadcastContent {
  overview: string
  recommendations: BroadcastRecommendation[]
  risk_warnings: string
}

/** 播报完整对象 */
export interface Broadcast {
  id: string
  date: string
  created_at: string
  title: string
  content: BroadcastContent
  audio_url: string | null
  duration: number | null
}

/** 播报列表响应 */
export interface BroadcastListResponse {
  items: Broadcast[]
  total: number
  has_prev: boolean
  has_next: boolean
}

/** 获取今日播报（缓存 10 分钟，每日更新一次） */
export function fetchTodayBroadcast(): Promise<Broadcast> {
  return cachedRequest(
    'broadcast:today',
    () => request<Broadcast>('/broadcast/today', { method: 'GET' }),
    undefined,
    { ttl: 10 * 60 * 1000 }
  )
}

/** 获取历史播报列表（分页） */
export function fetchBroadcastList(params?: {
  limit?: number
  offset?: number
}): Promise<BroadcastListResponse> {
  return request<BroadcastListResponse>('/broadcast/list', {
    method: 'GET',
    params: params as Record<string, string | number | undefined>,
  })
}

/** 获取指定日期的播报 */
export function fetchBroadcastByDate(date: string): Promise<Broadcast> {
  return request<Broadcast>(`/broadcast/${date}`, { method: 'GET' })
}

/** 获取播报音频 URL */
export function fetchBroadcastAudio(id: string): Promise<{ audio_url: string; duration: number }> {
  return request<{ audio_url: string; duration: number }>(`/broadcast/audio/${id}`, {
    method: 'GET',
  })
}
