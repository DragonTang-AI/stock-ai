/**
 * 网络状态检测工具
 *
 * 功能：
 * - 实时监测网络连接状态（Online/Offline）
 * - 网络类型识别（WiFi / 4G / 5G / unknown）
 * - 网络变化回调注册
 * - 弱网检测
 */

type NetworkType = 'wifi' | '4g' | '5g' | '3g' | '2g' | 'none' | 'unknown'

interface NetworkInfo {
  isConnected: boolean
  networkType: NetworkType
  /** Unix 时间戳，最后一次状态变化时间 */
  lastChangeAt: number
}

type NetworkChangeCallback = (info: NetworkInfo) => void

/** 当前网络状态 */
let currentNetwork: NetworkInfo = {
  isConnected: true,
  networkType: 'unknown',
  lastChangeAt: Date.now(),
}

/** 网络变化监听器列表 */
const listeners: Set<NetworkChangeCallback> = new Set()

/**
 * 初始化网络监听
 * 应在 App.vue onLaunch 中调用
 */
export function initNetworkMonitor(): void {
  // 获取初始网络状态
  updateNetworkStatus()

  // 监听网络状态变化
  uni.onNetworkStatusChange((res) => {
    const wasConnected = currentNetwork.isConnected
    currentNetwork.isConnected = res.isConnected
    currentNetwork.networkType = (res.networkType || 'unknown') as NetworkType
    currentNetwork.lastChangeAt = Date.now()

    // 网络恢复时触发通知
    if (!wasConnected && res.isConnected) {
      notifyReconnected()
    }

    // 断网时触发通知
    if (wasConnected && !res.isConnected) {
      notifyDisconnected()
    }

    // 通知所有监听器
    notifyListeners()
  })
}

/**
 * 手动更新网络状态（初始化时调用）
 */
function updateNetworkStatus(): void {
  try {
    uni.getNetworkType({
      success: (res) => {
        currentNetwork = {
          isConnected: res.networkType !== 'none',
          networkType: (res.networkType || 'unknown') as NetworkType,
          lastChangeAt: Date.now(),
        }
      },
      fail: () => {
        // 无法获取时假设在线
        currentNetwork = {
          isConnected: true,
          networkType: 'unknown',
          lastChangeAt: Date.now(),
        }
      },
    })
  } catch {
    // 兜底
  }
}

/**
 * 获取当前网络状态
 */
export function getNetworkInfo(): NetworkInfo {
  return { ...currentNetwork }
}

/**
 * 判断当前是否在线
 */
export function isOnline(): boolean {
  return currentNetwork.isConnected
}

/**
 * 判断当前是否为 WiFi
 */
export function isWifi(): boolean {
  return currentNetwork.networkType === 'wifi'
}

/**
 * 判断当前是否为移动网络（非 WiFi）
 */
export function isCellular(): boolean {
  return ['4g', '5g', '3g', '2g'].includes(currentNetwork.networkType)
}

/**
 * 注册网络状态变化回调
 * @returns 取消监听的函数
 */
export function onNetworkChange(callback: NetworkChangeCallback): () => void {
  listeners.add(callback)
  // 立即回调一次当前状态
  callback({ ...currentNetwork })
  return () => {
    listeners.delete(callback)
  }
}

/**
 * 等待网络恢复（Promise 形式）
 * @param timeout 超时时间（毫秒），默认 30 秒
 */
export function waitForReconnect(timeout = 30000): Promise<boolean> {
  if (currentNetwork.isConnected) return Promise.resolve(true)

  return new Promise((resolve) => {
    const timer = setTimeout(() => {
      cleanup()
      resolve(false)
    }, timeout)

    const handler: NetworkChangeCallback = (info) => {
      if (info.isConnected) {
        cleanup()
        resolve(true)
      }
    }

    const cleanup = () => {
      clearTimeout(timer)
      listeners.delete(handler)
    }

    listeners.add(handler)
  })
}

/**
 * 网络恢复后的通知
 */
function notifyReconnected(): void {
  if (import.meta.env.DEV) {
    console.log('[Network] 网络已恢复')
  }
}

/**
 * 断网通知
 */
function notifyDisconnected(): void {
  if (import.meta.env.DEV) {
    console.log('[Network] 网络已断开')
  }
  // 全局 Toast 提示
  uni.showToast({
    title: '网络连接已断开',
    icon: 'none',
    duration: 2500,
  })
}

/**
 * 通知所有监听器
 */
function notifyListeners(): void {
  const snapshot = { ...currentNetwork }
  for (const cb of listeners) {
    try {
      cb(snapshot)
    } catch {
      // 单个监听器异常不应影响其他
    }
  }
}

/**
 * 网络类型中文本地化
 */
export function getNetworkTypeLabel(type: NetworkType): string {
  const labels: Record<NetworkType, string> = {
    wifi: 'WiFi',
    '5g': '5G',
    '4g': '4G',
    '3g': '3G',
    '2g': '2G',
    none: '无网络',
    unknown: '未知',
  }
  return labels[type] || '未知'
}
