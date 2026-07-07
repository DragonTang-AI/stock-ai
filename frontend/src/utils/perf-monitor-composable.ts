/**
 * 性能监控 composable
 *
 * 用于页面中接入性能监控，自动采集首屏渲染时间
 *
 * @example
 * // 在页面的 <script setup> 中：
 * import { usePerfMonitor } from '@/utils/perf-monitor-composable'
 * const { onPageLoad } = usePerfMonitor()
 *
 * // 在 <script> 中：
 * export default {
 *   setup() {
 *     usePerfMonitor()
 *   },
 *   onLoad() { markPageLoadStart() },
 *   onReady() { markPageReady('pages/market/index') }
 * }
 */
import { onMounted, onUnmounted } from 'vue'
import {
  markPageLoadStart,
  markPageReady,
  startFpsMonitor,
  recordMemory,
} from './perf-monitor'

export function usePerfMonitor(pagePath?: string) {
  let stopFps: (() => void) | null = null

  onMounted(() => {
    markPageLoadStart()

    // 启动 FPS 监控（仅对有滚动的页面）
    if (pagePath) {
      // FPS 监控由需要监控的页面自行启动，此处仅初始化
    }
  })

  onUnmounted(() => {
    if (pagePath) {
      markPageReady(pagePath)
    }
    stopFps?.()
    recordMemory(pagePath)
  })

  /**
   * 标记页面渲染完成（在数据加载后调用）
   */
  function onPageReady(customPath?: string) {
    markPageReady(customPath || pagePath)
  }

  /**
   * 开始监控 FPS
   */
  function trackFps() {
    stopFps = startFpsMonitor()
  }

  return {
    onPageReady,
    trackFps,
    stopFps: () => {
      stopFps?.()
      stopFps = null
    },
  }
}
