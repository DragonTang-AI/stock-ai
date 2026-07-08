/**
 * 统一埋点模块
 * 支持页面访问 PV、功能事件埋点、API 异常上报、JS 错误捕获
 *
 * 上报端点：POST /api/v1/events
 * 策略：本地队列 → 批量上报（100ms 节流）→ 失败重试（最多 3 次）
 */

// ─── 类型定义 ───

type EventType = 'page_view' | 'action' | 'api_error' | 'js_error' | 'performance'

interface TrackEvent {
  event_type: EventType
  event_name: string
  props?: Record<string, any>
  timestamp: number
  page_path?: string
}

interface BatchPayload {
  events: TrackEvent[]
  device_id: string
  timestamp: number
}

// ─── 配置 ───

const REPORT_URL = '/api/v1/events'
const BATCH_INTERVAL = 100 // ms，节流上报间隔
const MAX_BATCH_SIZE = 20 // 单批最多事件数
const MAX_RETRIES = 3

// ─── 设备 ID ───

function getDeviceId(): string {
  try {
    let id = uni.getStorageSync('__tracker_device_id__')
    if (!id) {
      id = `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
      uni.setStorageSync('__tracker_device_id__', id)
    }
    return id
  } catch {
    return `unknown-${Date.now()}`
  }
}

// ─── 事件队列 ───

let eventQueue: TrackEvent[] = []
let flushTimer: ReturnType<typeof setTimeout> | null = null
let isFlushing = false
let retryCount = 0

// 获取当前页面路径
function getCurrentPagePath(): string {
  try {
    const pages = getCurrentPages()
    if (pages.length === 0) return '/'
    const page = pages[pages.length - 1] as any
    return page?.route || page?.$page?.fullPath || '/'
  } catch {
    return '/'
  }
}

// ─── 添加到队列 ───

function enqueue(event: TrackEvent) {
  eventQueue.push(event)

  // 达到批量上限立即上报
  if (eventQueue.length >= MAX_BATCH_SIZE) {
    scheduleFlush()
    return
  }

  // 否则节流批量上报
  if (!flushTimer) {
    flushTimer = setTimeout(() => {
      flushTimer = null
      scheduleFlush()
    }, BATCH_INTERVAL)
  }
}

// ─── 上报 ───

function scheduleFlush() {
  if (isFlushing || eventQueue.length === 0) return
  isFlushing = true
  flush().finally(() => {
    isFlushing = false
    // 如果在刷新期间有新事件入队，继续上报
    if (eventQueue.length > 0) {
      scheduleFlush()
    }
  })
}

async function flush() {
  if (eventQueue.length === 0) return

  const batch: BatchPayload = {
    events: eventQueue.splice(0, MAX_BATCH_SIZE),
    device_id: getDeviceId(),
    timestamp: Date.now(),
  }

  try {
    await uni.request({
      url: REPORT_URL,
      method: 'POST',
      header: { 'Content-Type': 'application/json' },
      data: batch,
      timeout: 5000,
    })
    retryCount = 0
  } catch {
    // 失败时放回队列头部
    eventQueue = [...batch.events, ...eventQueue]
    if (retryCount < MAX_RETRIES) {
      retryCount++
      // 指数退避重试
      await new Promise((r) => setTimeout(r, 1000 * retryCount))
      isFlushing = false
      scheduleFlush()
    } else {
      // 超出重试，丢弃并重置
      retryCount = 0
      if (import.meta.env.DEV) {
        console.warn('[Tracker] 上报失败，已丢弃', batch.events.length, '个事件')
      }
    }
  }
}

// ─── 公共 API ───

/**
 * 页面访问 PV 埋点
 * 在页面 onShow 中调用
 */
export function trackPageView(pageName: string, extra?: Record<string, any>) {
  enqueue({
    event_type: 'page_view',
    event_name: pageName,
    props: extra,
    timestamp: Date.now(),
    page_path: getCurrentPagePath(),
  })
}

/**
 * 功能/交互事件埋点
 * 在关键交互处调用，如：下单确认、加入自选、AI托管开关、播报播放
 */
export function trackAction(actionName: string, props?: Record<string, any>) {
  enqueue({
    event_type: 'action',
    event_name: actionName,
    props,
    timestamp: Date.now(),
    page_path: getCurrentPagePath(),
  })
}

/**
 * API 异常上报
 * 在 request.ts 的错误处理中调用
 */
export function trackApiError(errorInfo: {
  url: string
  method?: string
  status_code?: number
  error_message?: string
  error_code?: string
  duration_ms?: number
}) {
  enqueue({
    event_type: 'api_error',
    event_name: 'api_error',
    props: errorInfo,
    timestamp: Date.now(),
    page_path: getCurrentPagePath(),
  })
}

/**
 * JS 错误捕获上报
 * 在 App.vue onError 中调用
 */
export function trackJsError(error: string | Error, stack?: string) {
  const errMsg = typeof error === 'string' ? error : error.message
  enqueue({
    event_type: 'js_error',
    event_name: 'js_error',
    props: {
      message: errMsg,
      stack: stack || (error instanceof Error ? error.stack : undefined),
    },
    timestamp: Date.now(),
    page_path: getCurrentPagePath(),
  })
}

/**
 * 性能埋点（首屏时间、API 耗时等）
 */
export function trackPerformance(metric: string, value: number, extra?: Record<string, any>) {
  enqueue({
    event_type: 'performance',
    event_name: metric,
    props: { value, ...extra },
    timestamp: Date.now(),
    page_path: getCurrentPagePath(),
  })
}

/**
 * 立即刷新队列（页面隐藏/销毁时调用，尽可能保证事件不丢失）
 */
export function flushEvents() {
  if (flushTimer) {
    clearTimeout(flushTimer)
    flushTimer = null
  }
  scheduleFlush()
}

/**
 * 初始化埋点模块
 * 在 App.vue onLaunch 中调用
 */
export function initTracker() {
  if (import.meta.env.DEV) {
    console.log('[Tracker] 埋点模块已初始化')
  }
}
