/**
 * 认证 API 模块
 * 登录 / 注册 / 刷新 Token / 退出
 */
import { request } from '@/utils/request'

export interface LoginParams {
  username: string
  password: string
}

export interface RegisterParams {
  username: string
  email: string
  password: string
}

export interface LoginResponse {
  access_token: string
  refresh_token: string
  user?: {
    id: number
    username: string
    nickname?: string
    avatar?: string
  }
}

/** 用户登录 */
export function login(params: LoginParams): Promise<LoginResponse> {
  return request<LoginResponse>('/auth/login', {
    method: 'POST',
    data: params,
  })
}

/** 用户注册 */
export function register(params: RegisterParams): Promise<LoginResponse> {
  return request<LoginResponse>('/auth/register', {
    method: 'POST',
    data: params,
  })
}

/** 刷新 Token */
export function refreshToken(token: string): Promise<{ access_token: string }> {
  return request<{ access_token: string }>('/auth/refresh', {
    method: 'POST',
    data: { refresh_token: token },
  })
}

/** 获取当前用户信息 */
export function getCurrentUser(): Promise<LoginResponse['user']> {
  return request<LoginResponse['user']>('/auth/me', { method: 'GET' })
}

/** 退出登录（通知服务端失效 Token） */
export function logout(): Promise<void> {
  return request<void>('/auth/logout', { method: 'POST' })
}
