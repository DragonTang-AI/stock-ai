/**
 * 全局错误处理工具
 * 统一处理 HTTP 错误、网络异常、业务错误
 */

import { HttpError } from './request'

export type ErrorType = 'network' | 'auth' | 'server' | 'client' | 'unknown'

export interface ErrorInfo {
  type: ErrorType
  code?: number | string
  message: string
  detail?: string
  timestamp: number
  data?: any
}

export class AppError extends Error {
  public readonly type: ErrorType
  public readonly code?: number | string
  public readonly detail?: string
  public readonly data?: any

  constructor(
    message: string,
    type: ErrorType = 'unknown',
    code?: number | string,
    detail?: string,
    data?: any
  ) {
    super(message)
    this.name = 'AppError'
    this.type = type
    this.code = code
    this.detail = detail
    this.data = data
  }
}

/**
 * 将 HttpError 转换为统一的 AppError
 */
export function normalizeHttpError(err: HttpError): AppError {
  const status = err.statusCode
  let type: ErrorType = 'unknown'
  let code: string | number | undefined = err.errorCode
  let message = err.message

  if (status === 0) {
    type = 'network'
    message = '网络连接失败，请检查网络设置'
  } else if (status === 401) {
    type = 'auth'
    message = '登录已过期，请重新登录'
  } else if (status === 403) {
    type = 'auth'
    message = '权限不足，无法访问该资源'
  } else if (status === 404) {
    type = 'client'
    message = '请求的资源不存在'
  } else if (status >= 400 && status < 500) {
    type = 'client'
    message = err.detail || '请求参数有误'
  } else if (status >= 500) {
    type = 'server'
    message = '服务器开小差了，请稍后重试'
  }

  return new AppError(message, type, code, err.detail, err.payload)
}

/**
 * 全局错误处理函数
 * 可扩展：上报、记录、展示等
 */
export function handleGlobalError(err: unknown): ErrorInfo {
  const timestamp = Date.now()
  let errorInfo: ErrorInfo

  if (err instanceof AppError) {
    errorInfo = {
      type: err.type,
      code: err.code,
      message: err.message,
      detail: err.detail,
      timestamp,
      data: err.data,
    }
  } else if (err instanceof HttpError) {
    const appErr = normalizeHttpError(err)
    errorInfo = {
      type: appErr.type,
      code: appErr.code,
      message: appErr.message,
      detail: appErr.detail,
      timestamp,
      data: appErr.data,
    }
  } else if (err instanceof Error) {
    errorInfo = {
      type: 'unknown',
      message: err.message,
      timestamp,
    }
  } else {
    errorInfo = {
      type: 'unknown',
      message: String(err),
      timestamp,
    }
  }

  // 错误上报（可接入 Sentry/监控）
  reportError(errorInfo)

  // 用户提示（根据错误类型决定展示方式）
  showUserTip(errorInfo)

  return errorInfo
}

/**
 * 静默错误上报（开发环境可打印）
 */
function reportError(info: ErrorInfo) {
  if (import.meta.env.DEV) {
    console.error('[Error Handler]', info)
  }
  // 生产环境可接入 Sentry / 监控平台
  // if (import.meta.env.PROD) {
  //   // 上报逻辑
  // }
}

/**
 * 用户提示策略
 */
function showUserTip(info: ErrorInfo) {
  const { type, message } = info

  // 网络错误：自动重试提示
  if (type === 'network') {
    uni.showToast({
      title: message,
      icon: 'none',
      duration: 3000,
    })
    return
  }

  // 认证错误：跳转登录页
  if (type === 'auth') {
    uni.showModal({
      title: '登录失效',
      content: message,
      showCancel: false,
      success: () => {
        uni.reLaunch({ url: '/pages/login/index' })
      },
    })
    return
  }

  // 服务器错误：友好提示
  if (type === 'server') {
    uni.showToast({
      title: message,
      icon: 'none',
      duration: 3000,
    })
    return
  }

  // 客户端错误：展示具体信息
  if (type === 'client') {
    uni.showToast({
      title: message,
      icon: 'none',
      duration: 2500,
    })
    return
  }

  // 其他错误：通用提示
  uni.showToast({
    title: message || '操作失败，请重试',
    icon: 'none',
    duration: 2500,
  })
}

/**
 * 安全执行异步函数，自动捕获错误
 */
export async function safeExecute<T>(
  fn: () => Promise<T>,
  fallback?: T,
  onError?: (err: ErrorInfo) => void
): Promise<T | undefined> {
  try {
    return await fn()
  } catch (err) {
    const errorInfo = handleGlobalError(err)
    if (onError) onError(errorInfo)
    return fallback
  }
}

/**
 * 创建带错误边界的组件包装器（HOC 模式）
 */
export function withErrorBoundary<P extends object>(
  Component: any,
  fallback?: (error: ErrorInfo) => any
) {
  return {
    name: `WithErrorBoundary(${Component.name || 'Anonymous'})`,
    props: Component.props,
    data() {
      return { error: null as ErrorInfo | null }
    },
    errorCaptured(err: unknown) {
      this.error = handleGlobalError(err)
      return false // 阻止错误继续向上冒泡
    },
    render() {
      if (this.error) {
        return fallback
          ? fallback(this.error)
          : h('view', { class: 'error-boundary' }, [
              h('text', { class: 'error-text' }, this.error.message),
            ])
      }
      return h(Component, this.$props)
    },
  }
}
