/**
 * 深色模式管理
 *
 * 主题切换通过 CSS class (.dark) 驱动，SCSS 变量定义在 styles/dark-theme.scss 中。
 * 本模块仅负责：
 *   1. 持久化用户偏好 (localStorage)
 *   2. 在 documentElement 上切换 .dark class
 *   3. 监听系统主题变化（跟随系统模式）
 *   4. 通知订阅者主题变化
 */

const THEME_KEY = 'ai-stock:theme'

export type ThemeMode = 'light' | 'dark' | 'system'

interface ThemeState {
  mode: ThemeMode
  isDark: boolean
}

let listeners: Array<(isDark: boolean) => void> = []

function prefersDark(): boolean {
  // #ifdef H5
  return window.matchMedia?.('(prefers-color-scheme: dark)').matches ?? false
  // #endif
  // #ifndef H5
  return false
  // #endif
}

export function getThemeState(): ThemeState {
  const stored = uni.getStorageSync(THEME_KEY)
  if (stored) {
    const mode = stored as ThemeMode
    const isDark = mode === 'dark' || (mode === 'system' && prefersDark())
    return { mode, isDark }
  }
  return { mode: 'light', isDark: false }
}

export function setThemeMode(mode: ThemeMode) {
  uni.setStorageSync(THEME_KEY, mode)
  applyTheme()
  notifyListeners()
}

/**
 * 应用主题：仅通过 .dark class 驱动 SCSS 变量切换。
 * 不手动设置 style.setProperty —— 所有变量由 light-theme.scss / dark-theme.scss 负责。
 */
export function applyTheme() {
  // #ifdef H5
  const root = document.documentElement
  const { isDark } = getThemeState()
  if (isDark) {
    root.classList.add('dark')
  } else {
    root.classList.remove('dark')
  }
  // #endif
}

export function toggleDarkMode(): boolean {
  const current = getThemeState()
  const newMode = current.isDark ? 'light' : 'dark'
  setThemeMode(newMode)
  return !current.isDark
}

export function onThemeChange(callback: (isDark: boolean) => void) {
  listeners.push(callback)
  return () => {
    listeners = listeners.filter(l => l !== callback)
  }
}

function notifyListeners() {
  const { isDark } = getThemeState()
  listeners.forEach(fn => fn(isDark))
}

// 监听系统主题变化
// #ifdef H5
if (window.matchMedia) {
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
    const { mode } = getThemeState()
    if (mode === 'system') {
      applyTheme()
      notifyListeners()
    }
  })
}
// #endif
