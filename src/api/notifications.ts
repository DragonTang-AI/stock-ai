/**
 * 通知中心 API
 * 对应后端 /api/v1/notifications
 */
import { request } from '@/utils/request'

export type NotificationType = 'system' | 'price' | 'selection' | 'advisor' | 'trade' | 'signal'

export interface NotificationItem {
  id: number
  type: NotificationType
  title: string
  content: string
  channel: string
  is_read: boolean
  hire_id?: number
  trader_id?: string
  created_at: string   // ISO datetime
}

export interface NotificationsPage {
  items: NotificationItem[]
  total: number
  unread_count: number
  limit: number
  offset: number
}

/** 获取通知列表 */
export function fetchNotifications(params?: {
  limit?: number; offset?: number
}): Promise<NotificationsPage> {
  return request<{ items: NotificationItem[]; total: number; unread_count: number; limit: number; offset: number }>(
    '/notifications', { method: 'GET', params }
  ).then(res => res)
}

/** 标记单条已读 */
export function markAsRead(id: number): Promise<void> {
  return request(`/notifications/${id}/read`, { method: 'PUT' })
}

/** 全部标记已读 */
export function markAllAsRead(): Promise<void> {
  return request('/notifications/read-all', { method: 'PUT' })
}

/** 删除单条通知 */
export function deleteNotification(id: number): Promise<void> {
  return request(`/notifications/${id}`, { method: 'DELETE' })
}

/** 清空全部通知 */
export function clearAllNotifications(): Promise<void> {
  return request('/notifications', { method: 'DELETE' })
}
