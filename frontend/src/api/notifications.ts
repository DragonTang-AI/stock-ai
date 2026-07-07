/**
 * 通知中心 API
 * 对应后端 /api/v1/notifications
 */
import { request } from '@/utils/request'

export type NotificationType = 'system' | 'price' | 'selection' | 'advisor' | 'trade'

export interface NotificationItem {
  id: string
  type: NotificationType
  title: string
  content: string
  created_at: string   // ISO datetime
  read: boolean
  data?: Record<string, any>  // 跳转携带数据（code 等）
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
  return request<{ success: boolean; data: NotificationsPage }>(
    '/notifications', { method: 'GET', params }
  ).then(res => res.data)
}

/** 标记单条已读 */
export function markAsRead(id: string): Promise<void> {
  return request(`/notifications/${id}/read`, { method: 'PUT' })
}

/** 全部标记已读 */
export function markAllAsRead(): Promise<void> {
  return request('/notifications/read-all', { method: 'PUT' })
}

/** 删除单条通知 */
export function deleteNotification(id: string): Promise<void> {
  return request(`/notifications/${id}`, { method: 'DELETE' })
}

/** 清空全部通知 */
export function clearAllNotifications(): Promise<void> {
  return request('/notifications', { method: 'DELETE' })
}
