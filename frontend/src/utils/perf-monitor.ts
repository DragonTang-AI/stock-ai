/**
 * 性能监控埋点工具
 *
 * 功能：
 * - 首屏加载时间（FCP）
 * - API 响应时间
 * - 页面渲染时间
 * - 列表滚动帧率
 * - 内存使用
 *
 * 指标会上报到 uni.request 的 /api/v1/metrics（可配置）
 */

interface PerfEntry {
  name: string        // 指标名称
  value: number       // 数值（毫秒或百分比）
  unit: 'ms' | '%' | 'fps' | 'mb'
  timestamp: number   // Unix 时间戳
  page?: string       // 页面路径
  tags?: Record<string, string>
}

interface PageLoadMetrics {
  fcp: number         // First Contentful Paint
  lcp: number         // Largest Contentful Paint
  tti: number         // Time to Interactive
  renderTime: number  // 页面渲染完成时间
  totalTime: number   // 页面完全加载时间
}

interface ApiMetrics {
  url: string
  duration: number
  success: boolean
  cached: boolean
  statusCode?: number
  timestamp: number
}

const MAX_BATCH_SIZE = 20
const REPORT_INTERVAL = 30_000 // 30 秒批量上报

let metricBuffer: PerfEntry[] = []
let reportTimer: ReturnType<typeof setInterval> | null = null
let reportEndpoint = '/api/v1/metrics'
let isEnabled = true

// ---- 首屏加载 ----

let pageLoadStart = 0
let pageLoadEnd = 0
let firstPaintTime = 0

/**
 * 标记页面开始加载（在 onLoad 中调用）
 */
export function markPageLoadStart(): void {
  pageLoadStart = performance.now()
}

/**
 * 标记首屏渲染完成（在 onReady 或数据渲染完成后调用）
 */
export function markPageReady(pagePath?: string): PageLoadMetrics {
  pageLoadEnd = performance.now()
  const now = Date.now()

  const metrics: PageLoadMetrics = {
    fcp: firstPaintTime > 0 ? firstPaintTime - pageLoadStart : Math.round(pageLoadEnd - pageLoadStart),
    lcp: Math.round(pageLoadEnd - pageLoadStart),
    tti: Math.round(pageLoadEnd - pageLoadStart + 200), // 估算
    renderTime: Math.round(pageLoadEnd - pageLoadStart),
    totalTime: Math.round(pageLoadEnd - pageLoadStart),
  }

  recordMetric('page_fcp', metrics.fcp, 'ms', pagePath)
  recordMetric('page_lcp', metrics.lcp, 'ms', pagePath)
  recordMetric('page_render', metrics.renderTime, 'ms', pagePath)

  return metrics
}

/**
 * 标记 FP（在首屏可见内容渲染后立即调用）
 */
export function markFirstPaint(): void {
  firstPaintTime = performance.now()
}

// ---- API 监控 ----

const apiTimers = new Map<string, number>()

/**
 * 开始 API 计时
 */
export function startApiTimer(key: string): void {
  apiTimers.set(key, performance.now())
}

/**
 * 结束 API 计时并记录
 */
export function endApiTimer(key: string, url: string, success: boolean, cached = false, statusCode?: number): number {
  const start = apiTimers.get(key)
  if (!start) return 0

  const duration = Math.round(performance.now() - start)
  apiTimers.delete(key)

  recordMetric(
    'api_duration',
    duration,
    'ms',
    undefined,
    { url, success: String(success), cached: String(cached), statusCode: statusCode ? String(statusCode) : '' }
  )

  return duration
}

// ---- 滚动帧率 ----

let fpsFrameCount = 0
let fpsLastTime = 0
let fpsValue = 0
let fpsTracking = false

/**
 * 开始 FPS 监控（绑定到 scroll 事件）
 */
export function startFpsMonitor(): () => void {
  if (fpsTracking) return () => {}
  fpsTracking = true
  fpsFrameCount = 0
  fpsLastTime = performance.now()

  const tick = () => {
    if (!fpsTracking) return
    fpsFrameCount++
    const now = performance.now()
    if (now - fpsLastTime >= 1000) {
      fpsValue = Math.round(fpsFrameCount / ((now - fpsLastTime) / 1000))
      fpsFrameCount = 0
      fpsLastTime = now
    }
    requestAnimationFrame(tick)
  }

  requestAnimationFrame(tick)

  return () => {
    fpsTracking = false
    if (fpsValue > 0) {
      recordMetric('scroll_fps', fpsValue, 'fps')
    }
  }
}

// ---- 内存 ----

/**
 * 记录当前内存使用
 */
export function recordMemory(page?: string): void {
  // #ifdef H5
  const mem = (performance as any).memory
  if (mem) {
    const usedMB = Math.round(mem.usedJSHeapSize / 1024 / 1024)
    recordMetric('memory_used', usedMB, 'mb', page)
  }
  // #endif
}

// ---- 记录 & 上报 ----

function recordMetric(
  name: string,
  value: number,
  unit: 'ms' | '%' | 'fps' | 'mb',
  page?: string,
  tags?: Record<string, string>
): void {
  if (!isEnabled) return

  const entry: PerfEntry = {
    name,
    value: Math.round(value * 100) / 100,
    unit,
    timestamp: Date.now(),
    page,
    tags,
  }

  metricBuffer.push(entry)

  // 达到阈值立即上报
  if (metricBuffer.length >= MAX_BATCH_SIZE) {
    flushMetrics()
  } else if (!reportTimer) {
    // 启动定时上报
    reportTimer = setInterval(flushMetrics, REPORT_INTERVAL)
  }
}

function flushMetrics(): void {
  if (metricBuffer.length === 0) return

  const batch = metricBuffer.splice(0)
  if (reportTimer) {
    clearInterval(reportTimer)
    reportTimer = null
  }

  // 异步上报，不阻塞主线程
  // 尝试注入 token 避免 401（未登录时跳过）
  let token: string | undefined
  try {
    token = uni.getStorageSync('accessToken') as string | undefined
  } catch { /* empty */ }
  const header: Record<string, string> = { 'Content-Type': 'application/json' }
  if (token) header['Authorization'] = `Bearer ${token}`

  uni.request({
    url: reportEndpoint,
    method: 'POST',
    data: { metrics: batch },
    header,
    fail: () => { /* 上报失败不影响业务 */ },
  })
}

/**
 * 设置上报地址
 */
export function setReportEndpoint(url: string): void {
  reportEndpoint = url
}

/**
 * 启用/禁用监控
 */
export function setMonitorEnabled(enabled: boolean): void {
  isEnabled = enabled
  if (!enabled) {
    if (reportTimer) {
      clearInterval(reportTimer)
      reportTimer = null
    }
    metricBuffer = []
  }
}

/**
 * 获取当前页面的性能数据（用于调试）
 */
export function getDebugInfo(): {
  fps: number
  metrics: PerfEntry[]
  apiCount: number
} {
  return {
    fps: fpsValue,
    metrics: [...metricBuffer],
    apiCount: apiTimers.size,
  }
}

// 页面卸载时上报
// #ifdef H5
window.addEventListener('beforeunload', () => {
  recordMemory()
  flushMetrics()
})
// #endif
