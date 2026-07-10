/**
 * API 请求缓存工具
 *
 * 功能：
 * - 基于 key 的内存缓存 + Storage 持久化
 * - TTL 过期机制（默认 5 分钟）
 * - 请求去重（并发相同请求只发一次）
 * - 缓存失效/清除方法
 */

interface CacheEntry<T = any> {
  data: T
  timestamp: number
  ttl: number
}

interface CacheConfig {
  /** 缓存有效期（毫秒），默认 5 分钟 */
  ttl?: number
  /** 是否持久化到本地存储 */
  persist?: boolean
}

const DEFAULT_TTL = 5 * 60 * 1000 // 5 分钟

/** 内存缓存 */
const memoryCache = new Map<string, CacheEntry>()

/** 正在进行的请求（请求去重） */
const pendingRequests = new Map<string, Promise<any>>()

/** 序列化 key */
function serializeKey(apiKey: string, params?: Record<string, any>): string {
  if (!params) return apiKey
  const sorted = Object.keys(params)
    .sort()
    .reduce((acc, k) => {
      acc[k] = params[k]
      return acc
    }, {} as Record<string, any>)
  return `${apiKey}:${JSON.stringify(sorted)}`
}

/**
 * 检查缓存是否有效
 */
function isCacheValid(entry: CacheEntry): boolean {
  return Date.now() - entry.timestamp < entry.ttl
}

/**
 * 从 storage 加载缓存到内存
 */
function loadFromStorage(key: string): CacheEntry | null {
  try {
    const raw = uni.getStorageSync(`_apicache:${key}`)
    if (!raw) return null
    const entry = JSON.parse(raw) as CacheEntry
    if (!isCacheValid(entry)) {
      uni.removeStorageSync(`_apicache:${key}`)
      return null
    }
    return entry
  } catch {
    return null
  }
}

/**
 * 写入 storage
 */
function saveToStorage(key: string, entry: CacheEntry): void {
  try {
    uni.setStorageSync(`_apicache:${key}`, JSON.stringify(entry))
  } catch {
    // storage 满了或其他异常，静默失败
  }
}

/**
 * 带缓存的请求包装器
 *
 * @param apiKey   API 标识（如 'market:quote'）
 * @param fetcher  实际的请求函数
 * @param params   请求参数（用于生成缓存 key）
 * @param config   缓存配置
 */
export async function cachedRequest<T>(
  apiKey: string,
  fetcher: () => Promise<T>,
  params?: Record<string, any>,
  config: CacheConfig = {}
): Promise<T> {
  const ttl = config.ttl ?? DEFAULT_TTL
  const persist = config.persist ?? true
  const cacheKey = serializeKey(apiKey, params)

  // 1. 检查内存缓存
  const memEntry = memoryCache.get(cacheKey)
  if (memEntry && isCacheValid(memEntry)) {
    return memEntry.data as T
  }

  // 2. 检查持久化存储
  if (persist) {
    const storageEntry = loadFromStorage(cacheKey)
    if (storageEntry) {
      memoryCache.set(cacheKey, storageEntry)
      return storageEntry.data as T
    }
  }

  // 3. 请求去重：若有相同请求正在进行，复用
  const pending = pendingRequests.get(cacheKey)
  if (pending) {
    return pending as Promise<T>
  }

  // 4. 发起请求
  const promise = fetcher()
    .then((data) => {
      const entry: CacheEntry = { data, timestamp: Date.now(), ttl }
      memoryCache.set(cacheKey, entry)
      if (persist) {
        saveToStorage(cacheKey, entry)
      }
      return data
    })
    .finally(() => {
      pendingRequests.delete(cacheKey)
    })

  pendingRequests.set(cacheKey, promise)
  return promise
}

/**
 * 清除指定 API 的缓存
 */
export function clearCache(apiKey: string, params?: Record<string, any>): void {
  const cacheKey = serializeKey(apiKey, params)

  // 如果有 params，精确清除
  if (params) {
    memoryCache.delete(cacheKey)
    try {
      uni.removeStorageSync(`_apicache:${cacheKey}`)
    } catch { /* ignore */ }
    return
  }

  // 无 params，清除该 apiKey 下所有缓存
  const prefix = `${apiKey}:`
  for (const key of memoryCache.keys()) {
    if (key === apiKey || key.startsWith(prefix)) {
      memoryCache.delete(key)
    }
  }
  // 清除 storage 中的匹配项
  try {
    const { keys } = uni.getStorageInfoSync()
    for (const k of keys) {
      if (k.startsWith(`_apicache:${apiKey}`)) {
        uni.removeStorageSync(k)
      }
    }
  } catch { /* ignore */ }
}

/**
 * 清除所有缓存
 */
export function clearAllCache(): void {
  memoryCache.clear()
  try {
    const { keys } = uni.getStorageInfoSync()
    for (const k of keys) {
      if (k.startsWith('_apicache:')) {
        uni.removeStorageSync(k)
      }
    }
  } catch { /* ignore */ }
}

/**
 * 强制刷新（忽略缓存，重新请求并更新缓存）
 */
export async function forceRefresh<T>(
  apiKey: string,
  fetcher: () => Promise<T>,
  params?: Record<string, any>,
  config: CacheConfig = {}
): Promise<T> {
  const ttl = config.ttl ?? DEFAULT_TTL
  const persist = config.persist ?? true
  const cacheKey = serializeKey(apiKey, params)

  const data = await fetcher()
  const entry: CacheEntry = { data, timestamp: Date.now(), ttl }
  memoryCache.set(cacheKey, entry)
  if (persist) {
    saveToStorage(cacheKey, entry)
  }
  return data
}
