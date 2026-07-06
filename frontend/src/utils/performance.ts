/**
 * 性能优化工具
 * - 防抖/节流
 * - 虚拟列表预估
 * - 图片懒加载指令
 * - 页面可见性检测
 */

/**
 * 防抖
 */
export function debounce<T extends (...args: any[]) => any>(
  fn: T,
  delay: number
): (...args: Parameters<T>) => void {
  let timer: ReturnType<typeof setTimeout> | null = null
  return (...args: Parameters<T>) => {
    if (timer) clearTimeout(timer)
    timer = setTimeout(() => {
      fn(...args)
      timer = null
    }, delay)
  }
}

/**
 * 节流
 */
export function throttle<T extends (...args: any[]) => any>(
  fn: T,
  interval: number
): (...args: Parameters<T>) => void {
  let lastTime = 0
  let timer: ReturnType<typeof setTimeout> | null = null
  return (...args: Parameters<T>) => {
    const now = Date.now()
    if (now - lastTime >= interval) {
      lastTime = now
      fn(...args)
    } else {
      if (timer) clearTimeout(timer)
      timer = setTimeout(() => {
        lastTime = Date.now()
        fn(...args)
        timer = null
      }, interval - (now - lastTime))
    }
  }
}

/**
 * 创建 RAF 节流（适用于动画/滚动）
 */
export function rafThrottle<T extends (...args: any[]) => any>(
  fn: T
): (...args: Parameters<T>) => void {
  let ticking = false
  return (...args: Parameters<T>) => {
    if (!ticking) {
      requestAnimationFrame(() => {
        fn(...args)
        ticking = false
      })
      ticking = true
    }
  }
}

/**
 * 虚拟列表工具
 * 根据可视区高度和项高度计算可见项
 */
export function getVisibleRange(
  scrollTop: number,
  viewportHeight: number,
  itemHeight: number,
  totalCount: number,
  buffer = 5
) {
  const start = Math.max(0, Math.floor(scrollTop / itemHeight) - buffer)
  const visibleCount = Math.ceil(viewportHeight / itemHeight)
  const end = Math.min(totalCount, start + visibleCount + buffer * 2)
  return { start, end }
}

/**
 * 获取虚拟列表样式偏移
 */
export function getVirtualListStyle(
  start: number,
  itemHeight: number,
  totalCount: number
) {
  return {
    paddingTop: `${start * itemHeight}px`,
    paddingBottom: `${(totalCount - start) * itemHeight}px`,
  }
}

/**
 * 页面可见性监听
 * 返回清理函数
 */
export function onPageVisible(
  onShow: () => void,
  onHide?: () => void
): () => void {
  const handler = () => {
    if (!document.hidden) {
      onShow()
    } else if (onHide) {
      onHide()
    }
  }
  document.addEventListener('visibilitychange', handler)
  return () => document.removeEventListener('visibilitychange', handler)
}

/**
 * 惰性函数：检测设备是否为低端机（简化判断）
 */
export function isLowEndDevice(): boolean {
  let cached: boolean | null = null
  return () => {
    if (cached !== null) return cached
    // 简单判断：CPU 核数
    cached = (navigator.hardwareConcurrency || 4) <= 2
    return cached
  }
}

/**
 * 请求合并工具
 */
export function createMergedRequest<T>(
  fetcher: () => Promise<T>,
  ttl = 5000
): () => Promise<T> {
  let pending: Promise<T> | null = null
  let lastResult: T | null = null
  let lastTime = 0

  return async () => {
    const now = Date.now()
    if (lastResult && now - lastTime < ttl) {
      return lastResult
    }
    if (pending) return pending
    pending = fetcher()
      .then((data) => {
        lastResult = data
        lastTime = Date.now()
        return data
      })
      .finally(() => {
        pending = null
      })
    return pending
  }
}
