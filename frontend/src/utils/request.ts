/**
 * 统一请求封装
 * 基于 uni.request，支持 JWT 自动注入 / 错误处理 / 统一 base URL
 */

// API Base URL（开发环境）
const BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1'

// 请求拦截 + 响应拦截
interface RequestOptions extends UniApp.RequestOptions {
  params?: Record<string, string | number | undefined>
  /** 是否跳过全局错误提示，由调用方自行处理 */
  silent?: boolean
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
    const msg = typeof payload === 'string' ? payload : (payload?.detail || '请求失败')
    super(msg)
    this.name = 'HttpError'
    this.errorCode = typeof payload === 'object' ? payload?.error_code : undefined
    this.detail = typeof payload === 'object' ? payload?.detail : undefined
  }
}

/**
 * 通用请求函数
 */
export function request<T = any>(url: string, options: RequestOptions = {}): Promise<T> {
  const { params, silent = false, ...rest } = options

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
          resolve(res.data as T)
          return
        }

        // 401 未授权
        if (statusCode === 401) {
          handleUnauthorized()
            .then(() => request<T>(url, options))
            .then(resolve)
            .catch(() => {
              jumpToLogin()
              const err = new HttpError(statusCode, res.data as any)
              if (!silent) triggerErrorHandler(err)
              reject(err)
            })
          return
        }

        // 其他 HTTP 错误 → 传递完整响应体
        const errorData = res.data as any
        const errMsg = errorData?.detail || errorData?.message || `请求失败 (${statusCode})`
        const err = new HttpError(statusCode, errorData || errMsg)
        if (!silent) triggerErrorHandler(err)
        reject(err)
      },
      fail: (err: UniApp.RequestFailCallbackResult) => {
        const httpErr = new HttpError(0, err.errMsg || '网络异常')
        if (!silent) triggerErrorHandler(httpErr)
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

/** 401 处理 */
async function handleUnauthorized(): Promise<void> {
  const refreshToken = uni.getStorageSync('refreshToken')
  if (!refreshToken) throw new Error('No refresh token')

  try {
    const res = await refreshTokenSync(refreshToken)
    uni.setStorageSync('accessToken', res.access_token)
  } catch {
    throw new Error('Refresh failed')
  }
}

function refreshTokenSync(refreshToken: string): Promise<{ access_token: string }> {
  return new Promise((resolve, reject) => {
    uni.request({
      url: `${BASE_URL}/auth/refresh`,
      method: 'POST',
      data: { refresh_token: refreshToken },
      header: { 'Content-Type': 'application/json' },
      success: (res) => {
        if (res.statusCode === 200) {
          resolve(res.data as { access_token: string })
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
