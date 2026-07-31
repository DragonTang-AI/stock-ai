// useShowRefresh - onShow 防抖刷新 composable
// 防止页面切换时 onShow 重复触发全量加载
// 在冷却时间内重复显示跳过加载，超时后自动刷新

const refreshTimers = new Map<string, number>()

/**
 * onShow 防抖：同一页面在冷却时间内从后切回不再重复加载
 * @param key 唯一标识（通常传页面路由名或 __file__）
 * @param fn 实际加载函数
 * @param cooldown 冷却毫秒数，默认 30 秒
 *
 * 用法：
 *   onShow(() => useShowRefresh('portfolio', () => loadOrders()))
 */
export function useShowRefresh(key: string, fn: () => void | Promise<void>, cooldown = 30000) {
  const now = Date.now()
  const last = refreshTimers.get(key) || 0
  if (now - last > cooldown) {
    refreshTimers.set(key, now)
    const result = fn()
    if (result instanceof Promise) {
      result.catch(() => {
        // 加载失败时回退冷却时间，允许下次重试
        refreshTimers.set(key, 0)
      })
    }
  }
}

/**
 * 强制刷新某页面的缓存时间戳。
 * 用于页面自身的 onPullDownRefresh 手动下拉时重置冷却。
 */
export function touchRefreshKey(key: string) {
  refreshTimers.set(key, 0)
}
