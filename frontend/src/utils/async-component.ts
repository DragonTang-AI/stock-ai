/**
 * 组件按需加载工具
 *
 * 在 uni-app 中使用 defineAsyncComponent 实现组件级别的代码分割。
 * 适用于体积较大的组件（图表、富文本编辑器等）。
 * Vue 3 标准 defineAsyncComponent 在 uni-app 中可用。
 */

import { defineAsyncComponent, type Component } from 'vue'

interface AsyncComponentOptions {
  /** 加载中组件 */
  loadingComponent?: Component
  /** 错误组件 */
  errorComponent?: Component
  /** 超时时间（ms），默认 10s */
  timeout?: number
  /** 加载失败重试次数 */
  retryCount?: number
}

/**
 * 创建异步组件
 *
 * @param loader 动态 import 函数
 * @param options 可选配置
 *
 * @example
 * const KlineChart = createAsyncComponent(
 *   () => import('@/components/market/KlineChart.vue'),
 *   { timeout: 8000 }
 * )
 */
export function createAsyncComponent(
  loader: () => Promise<{ default: Component }>,
  options: AsyncComponentOptions = {}
): Component {
  return defineAsyncComponent({
    loader,
    loadingComponent: options.loadingComponent,
    errorComponent: options.errorComponent,
    delay: 200, // 200ms 后才显示 loading 组件
    timeout: options.timeout ?? 10000,
    suspensible: true,
    onError(error, retry, fail, attempts) {
      const maxRetries = options.retryCount ?? 2
      if (attempts <= maxRetries) {
        // 重试
        retry()
      } else {
        fail()
      }
    },
  })
}

/**
 * 预加载组件（提前触发 import，不阻塞渲染）
 *
 * @param loader 动态 import 函数
 * @example
 * preloadComponent(() => import('@/components/market/KlineChart.vue'))
 */
export function preloadComponent(loader: () => Promise<any>): void {
  // H5 环境使用 requestIdleCallback 预加载
  // #ifdef H5
  if (typeof requestIdleCallback !== 'undefined') {
    requestIdleCallback(() => {
      loader().catch(() => { /* ignore */ })
    })
  } else {
    setTimeout(() => {
      loader().catch(() => { /* ignore */ })
    }, 300)
  }
  // #endif
  // #ifndef H5
  // 小程序环境延迟加载
  setTimeout(() => {
    loader().catch(() => { /* ignore */ })
  }, 500)
  // #endif
}
