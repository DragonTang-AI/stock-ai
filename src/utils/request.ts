/**
 * 统一请求封装
 * 基于 uni.request，支持 JWT 自动注入 / 错误处理 / 统一 base URL
 *
 * 错误码处理策略：
 * - 401: 自动刷新 token → 重试请求 → 失败跳登录
 * - 403: 审核模式提示（仅提示，不跳转登录）
 * - 429: 请求过于频繁，指数退避重试
 * - 500: 服务端错误提示
 * - 网络错误: 离线提示
 */

// API Base URL（开发环境）
const BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1'

/** 最大自动重试次数（仅 429 等可重试状态码） */
const MAX_RETRIES = 2
/** 429 退避基础延迟（毫秒） */
const RETRY_BASE_DELAY = 1000

// 性能监控埋点
let startApiTimer: ((key: string) => void) | null = null
let endApiTimer: ((key: string, url: string, success: boolean, cached: boolean, statusCode?: number) => number) | null = null

// 动态导入监控模块（避免循环依赖和构建失败）
try {
  import('./perf-monitor').then(({ startApiTimer: s, endApiTimer: e }) => {
    startApiTimer = s
    endApiTimer = e
  }).catch(() => {})
} catch { /* ignore */ }

// 动态导入埋点模块（避免循环依赖）
let trackApiErrorFn: ((info: Record<string, any>) => void) | null = null
try {
  import('./tracker').then(({ trackApiError: fn }) => {
    trackApiErrorFn = fn
  }).catch(() => {})
} catch { /* ignore */ }

// 请求拦截 + 响应拦截
interface RequestOptions extends UniApp.RequestOptions {
  params?: Record<string, string | number | undefined>
  /** 是否跳过全局错误提示，由调用方自行处理 */
  silent?: boolean
  /** 是否允许自动重试（429 等可重试场景） */
  retryable?: boolean
  /** 当前重试次数（内部使用） */
  _retryCount?: number
}

interface ApiResponse<T = any> {
  data: T
  code?: number
  message?: string
}

export class HttpError extends Error {
  public readonly errorCode: string | undefined
  public readonly detail: string | undefined

  constructor(
    public statusCode: number,
    public payload: any
  ) {
    const data = typeof payload === 'string' ? null : payload
    const msg = typeof payload === 'string' ? payload : (data?.message || data?.detail || '请求失败')
    super(msg)
    this.name = 'HttpError'
    this.errorCode = data?.code || data?.error_code || undefined
    this.detail = data?.detail || data?.message || undefined
  }
}

/**
 * 通用请求函数
 */
export function request<T = any>(url: string, options: RequestOptions = {}): Promise<T> {
  const {
    params,
    silent = false,
    retryable = true,
    _retryCount = 0,
    ...rest
  } = options

  // 组装完整 URL
  let fullUrl = `${BASE_URL}${url}`
  if (params) {
    const qs = Object.entries(params)
      .filter(([, v]) => v !== undefined)
      .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v as string)}`)
      .join('&')
    if (qs) fullUrl += `?${qs}`
  }

  return new Promise((resolve, reject) => {
    // 获取 Token
    const token = uni.getStorageSync('accessToken')

    // 性能监控：API 开始计时
    const timerKey = `${options.method || 'GET'}:${fullUrl}:${Date.now()}`
    startApiTimer?.(timerKey)

    uni.request({
      url: fullUrl,
      ...rest,
      header: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(rest.header || {}),
      },
      success: (res: UniApp.RequestSuccessCallbackResult) => {
        const statusCode = res.statusCode

        if (statusCode >= 200 && statusCode < 300) {
          endApiTimer?.(timerKey, url, true, false, statusCode)
          resolve(res.data as T)
          return
        }

        // ─── 401 未授权：自动刷新 token 后重试 ───
        if (statusCode === 401) {
          endApiTimer?.(timerKey, url, false, false, statusCode)
          if (_retryCount === 0) {
            // 首次 401，尝试刷新 token
            handleUnauthorized()
              .then(() => request<T>(url, { ...options, _retryCount: 1 }))
              .then(resolve)
              .catch(() => {
                jumpToLogin()
                const err = new HttpError(statusCode, res.data as any)
                if (!silent) triggerErrorHandler(err)
                reject(err)
              })
            return
          }
          // 刷新后仍 401，直接跳登录
          jumpToLogin()
          const err = new HttpError(statusCode, res.data as any)
          if (!silent) triggerErrorHandler(err)
          reportApiError(url, options.method || 'GET', err)
          reject(err)
          return
        }

        // ─── 403 审核模式/权限不足 ───
        if (statusCode === 403) {
          const errorData = res.data as any
          const auditMsg = errorData?.detail || errorData?.message || '当前处于审核模式，操作受限'
          const isAuditMode = errorData?.error_code === 'AUDIT_MODE' || auditMsg.includes('审核')

          endApiTimer?.(timerKey, url, false, false, statusCode)

          if (isAuditMode) {
            // 审核模式：弹窗提示，不跳转登录
            uni.showModal({
              title: '审核模式',
              content: auditMsg,
              showCancel: false,
              confirmText: '知道了',
            })
          } else {
            // 普通 403：权限不足提示
            uni.showToast({
              title: '暂无权限执行此操作',
              icon: 'none',
              duration: 3000,
            })
          }

          const err = new HttpError(statusCode, errorData || auditMsg)
          if (!silent) triggerErrorHandler(err)
          reportApiError(url, options.method || 'GET', err)
          reject(err)
          return
        }

        // ─── 429 请求过于频繁：指数退避重试 ───
        if (statusCode === 429) {
          endApiTimer?.(timerKey, url, false, false, statusCode)
          if (retryable && _retryCount < MAX_RETRIES) {
            const delay = RETRY_BASE_DELAY * Math.pow(2, _retryCount)
            if (!silent && _retryCount === 0) {
              uni.showToast({
                title: '请求频繁，稍后重试...',
                icon: 'none',
                duration: 2000,
              })
            }
            setTimeout(() => {
              request<T>(url, { ...options, _retryCount: _retryCount + 1 })
                .then(resolve)
                .catch(reject)
            }, delay)
            return
          }
          // 超过重试次数
          const rateLimitErr = new HttpError(statusCode, { detail: '请求过于频繁，请稍后重试' })
          uni.showToast({
            title: '操作太频繁了，请稍后重试',
            icon: 'none',
            duration: 3000,
          })
          reportApiError(url, options.method || 'GET', rateLimitErr)
          reject(rateLimitErr)
          return
        }

        // ─── 500 服务端错误 ───
        if (statusCode >= 500) {
          const errorData = res.data as any
          const err = new HttpError(statusCode, errorData || '服务器异常，请稍后重试')
          endApiTimer?.(timerKey, url, false, false, statusCode)

          if (retryable && _retryCount < MAX_RETRIES) {
            const delay = RETRY_BASE_DELAY * Math.pow(2, _retryCount)
            setTimeout(() => {
              request<T>(url, { ...options, _retryCount: _retryCount + 1 })
                .then(resolve)
                .catch(reject)
            }, delay)
            return
          }

          if (!silent) triggerErrorHandler(err)
          reportApiError(url, options.method || 'GET', err)
          reject(err)
          return
        }

        // ─── 其他 4xx 错误 ───
        const errorData = res.data as any
        const errMsg = errorData?.detail || errorData?.message || `请求失败 (${statusCode})`
        const err = new HttpError(statusCode, errorData || errMsg)
        endApiTimer?.(timerKey, url, false, false, statusCode)
        if (!silent) triggerErrorHandler(err)
        reportApiError(url, options.method || 'GET', err)
        reject(err)
      },
      fail: (err: UniApp.RequestFailCallbackResult) => {
        // ─── 网络错误：离线提示 ───
        const httpErr = new HttpError(0, err.errMsg || '网络连接失败，请检查网络设置')
        endApiTimer?.(timerKey, url, false, false, 0)

        if (retryable && _retryCount < MAX_RETRIES) {
          const delay = RETRY_BASE_DELAY * Math.pow(2, _retryCount)
          setTimeout(() => {
            request<T>(url, { ...options, _retryCount: _retryCount + 1 })
              .then(resolve)
              .catch(reject)
          }, delay)
          return
        }

        if (!silent) triggerErrorHandler(httpErr)
        reportApiError(url, options.method || 'GET', httpErr)
        reject(httpErr)
      },
    })
  })
}

function triggerErrorHandler(err: HttpError) {
  // 动态导入避免循环依赖
  import('./error-handler').then(({ handleGlobalError }) => {
    handleGlobalError(err)
  })
}

/** 上报 API 异常到埋点系统 */
function reportApiError(url: string, method: string, err: HttpError, durationMs?: number) {
  trackApiErrorFn?.({
    url,
    method,
    status_code: err.statusCode,
    error_message: err.message,
    error_code: err.errorCode,
    duration_ms: durationMs,
  })
}

// ─── Token 刷新互斥锁（防止并发 401 重复刷新）───
let isRefreshing = false
let refreshPromise: Promise<void> | null = null

/** 401 处理（带互斥锁，避免并发刷新竞态） */
async function handleUnauthorized(): Promise<void> {
  // 如果已在刷新流程中，复用同一个 Promise
  if (isRefreshing && refreshPromise) {
    return refreshPromise
  }

  const refreshToken = uni.getStorageSync('refreshToken')
  if (!refreshToken) throw new Error('No refresh token')

  isRefreshing = true
  refreshPromise = (async () => {
    try {
      const res = await refreshTokenSync(refreshToken)
      uni.setStorageSync('accessToken', res.access_token)
      // 同时存储新的 refresh_token，延长有效期
      uni.setStorageSync('refreshToken', res.refresh_token)
    } catch {
      throw new Error('Refresh failed')
    } finally {
      isRefreshing = false
      refreshPromise = null
    }
  })()

  return refreshPromise
}

function refreshTokenSync(refreshToken: string): Promise<{ access_token: string; refresh_token: string }> {
  return new Promise((resolve, reject) => {
    uni.request({
      url: `${BASE_URL}/auth/refresh`,
      method: 'POST',
      data: { refresh_token: refreshToken },
      header: { 'Content-Type': 'application/json' },
      success: (res) => {
        if (res.statusCode === 200) {
          resolve(res.data as { access_token: string; refresh_token: string })
        } else {
          reject(new Error('Refresh failed'))
        }
      },
      fail: () => reject(new Error('Refresh failed')),
    })
  })
}

function jumpToLogin() {
  uni.removeStorageSync('accessToken')
  uni.removeStorageSync('refreshToken')
  uni.removeStorageSync('userInfo')

  const pages = getCurrentPages()
  const currentPage = pages[pages.length - 1]
  if (currentPage?.route !== 'pages/login/index') {
    uni.reLaunch({ url: '/pages/login/index' })
  }
}
