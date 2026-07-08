/**
 * 离线模式管理
 *
 * 功能：
 * - 离线数据缓存（Storage 持久化）
 * - 离线状态关键数据保留
 * - 在线后自动同步
 * - 离线提示 UI
 */

import { isOnline, onNetworkChange } from './network'
import type { NetworkInfo } from './network'

interface CacheRecord<T = any> {
  data: T
  cachedAt: number
  /** 缓存键（用于清理） */
  key: string
}

interface OfflineConfig {
  /** 最大缓存条目数 */
  maxEntries?: number
  /** 缓存有效期（毫秒），默认 7 天 */
  ttl?: number
}

const DEFAULT_MAX_ENTRIES = 50
const DEFAULT_TTL = 7 * 24 * 60 * 60 * 1000 // 7 天

const STORAGE_PREFIX = '_offline:'
const INDEX_KEY = `${STORAGE_PREFIX}__index`

/** 离线缓存索引 */
let cacheIndex: string[] = []

/** 当前是否处于离线模式 */
let _isOfflineMode = !isOnline()

// 初始化：加载已有索引
try {
  const raw = uni.getStorageSync(INDEX_KEY)
  if (raw) {
    cacheIndex = JSON.parse(raw)
  }
} catch {
  cacheIndex = []
}

// 监听网络变化
onNetworkChange((info: NetworkInfo) => {
  const wasOffline = _isOfflineMode
  _isOfflineMode = !info.isConnected

  // 从离线恢复到在线
  if (wasOffline && !_isOfflineMode) {
    onReconnected()
  }
})

/**
 * 判断是否处于离线模式
 */
export function isOfflineMode(): boolean {
  return _isOfflineMode
}

/**
 * 将数据存入离线缓存
 * @param key   缓存键（建议使用 apiKey 或唯一标识）
 * @param data  要缓存的数据
 * @param config 缓存配置
 */
export function saveOfflineData<T = any>(
  key: string,
  data: T,
  config: OfflineConfig = {}
): void {
  const { maxEntries = DEFAULT_MAX_ENTRIES, ttl = DEFAULT_TTL } = config
  const storageKey = `${STORAGE_PREFIX}${key}`

  const record: CacheRecord<T> = {
    data,
    cachedAt: Date.now(),
    key,
  }

  try {
    uni.setStorageSync(storageKey, JSON.stringify(record))
  } catch {
    // storage 满时清理旧缓存重试一次
    trimOldest(maxEntries)
    try {
      uni.setStorageSync(storageKey, JSON.stringify(record))
    } catch {
      // 仍然失败则静默
    }
  }

  // 更新索引
  updateIndex(key, maxEntries)
}

/**
 * 读取离线缓存数据
 * @param key  缓存键
 * @param ttl  缓存有效期（毫秒），过期返回 null
 */
export function loadOfflineData<T = any>(key: string, ttl?: number): T | null {
  const storageKey = `${STORAGE_PREFIX}${key}`
  try {
    const raw = uni.getStorageSync(storageKey)
    if (!raw) return null

    const record: CacheRecord<T> = JSON.parse(raw)

    // 过期检查
    const effectiveTTL = ttl ?? DEFAULT_TTL
    if (Date.now() - record.cachedAt > effectiveTTL) {
      removeOfflineData(key)
      return null
    }

    return record.data
  } catch {
    return null
  }
}

/**
 * 删除指定离线缓存
 */
export function removeOfflineData(key: string): void {
  const storageKey = `${STORAGE_PREFIX}${key}`
  try {
    uni.removeStorageSync(storageKey)
  } catch {
    // ignore
  }
  cacheIndex = cacheIndex.filter((k) => k !== key)
  try {
    uni.setStorageSync(INDEX_KEY, JSON.stringify(cacheIndex))
  } catch {
    // ignore
  }
}

/**
 * 清理所有离线缓存
 */
export function clearAllOfflineData(): void {
  for (const key of cacheIndex) {
    try {
      uni.removeStorageSync(`${STORAGE_PREFIX}${key}`)
    } catch {
      // ignore
    }
  }
  cacheIndex = []
  try {
    uni.removeStorageSync(INDEX_KEY)
  } catch {
    // ignore
  }
}

/**
 * 获取离线缓存条数
 */
export function getOfflineCacheCount(): number {
  return cacheIndex.length
}

/**
 * 显示离线提示 Toast
 */
export function showOfflineToast(duration = 2000): void {
  uni.showToast({
    title: '当前处于离线模式，数据显示可能不全',
    icon: 'none',
    duration,
  })
}

/**
 * 显示离线 Modal
 */
export function showOfflineModal(): void {
  uni.showModal({
    title: '网络连接不可用',
    content: '当前处于离线模式，部分功能可能受限。请检查网络连接后重试。',
    showCancel: false,
    confirmText: '我知道了',
  })
}

// ─── 内部方法 ───

/**
 * 更新离线缓存索引
 */
function updateIndex(key: string, maxEntries: number): void {
  // 去重
  cacheIndex = cacheIndex.filter((k) => k !== key)
  cacheIndex.push(key)

  // 限制条目数
  if (cacheIndex.length > maxEntries) {
    const removed = cacheIndex.splice(0, cacheIndex.length - maxEntries)
    for (const oldKey of removed) {
      try {
        uni.removeStorageSync(`${STORAGE_PREFIX}${oldKey}`)
      } catch {
        // ignore
      }
    }
  }

  try {
    uni.setStorageSync(INDEX_KEY, JSON.stringify(cacheIndex))
  } catch {
    // ignore
  }
}

/**
 * 网络恢复后的回调
 */
function onReconnected(): void {
  uni.showToast({
    title: '网络已恢复',
    icon: 'success',
    duration: 2000,
  })

  if (import.meta.env.DEV) {
    console.log('[Offline] 网络恢复，离线缓存条目:', cacheIndex.length)
  }
}

/**
 * 清理最旧的缓存
 */
function trimOldest(count: number): void {
  const entries: { key: string; cachedAt: number }[] = []

  for (const key of cacheIndex) {
    try {
      const raw = uni.getStorageSync(`${STORAGE_PREFIX}${key}`)
      if (raw) {
        const record = JSON.parse(raw) as CacheRecord
        entries.push({ key, cachedAt: record.cachedAt })
      }
    } catch {
      // ignore
    }
  }

  // 按时间排序，删除最旧的
  entries.sort((a, b) => a.cachedAt - b.cachedAt)
  const toRemove = entries.slice(0, Math.min(count, entries.length))
  for (const { key } of toRemove) {
    removeOfflineData(key)
  }
}
export { isOnline, onNetworkChange } from './network';
