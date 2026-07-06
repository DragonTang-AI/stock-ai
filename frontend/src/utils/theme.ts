/**
 * 深色模式管理
 */

const THEME_KEY = 'ai-stock:theme'

export type ThemeMode = 'light' | 'dark' | 'system'

interface ThemeState {
  mode: ThemeMode
  isDark: boolean
}

let listeners: Array<(isDark: boolean) => void> = []

/**
 * 深色模式 CSS 变量映射
 */
const darkVars: Record<string, string> = {
  '--bg-page': '#0F0F23',
  '--bg-card': '#1A1A2E',
  '--bg-primary': '#16213E',
  '--bg-secondary': '#0F3460',
  '--text-primary': '#E0E0E0',
  '--text-secondary': '#A0A0A0',
  '--text-hint': '#666666',
  '--text-inverse': '#FFFFFF',
  '--border-color': '#2A2A3E',
}

const lightVars: Record<string, string> = {
  '--bg-page': '#F5F5F7',
  '--bg-card': '#FFFFFF',
  '--bg-primary': '#1A1A2E',
  '--bg-secondary': '#16213E',
  '--text-primary': '#1F1F1F',
  '--text-secondary': '#666666',
  '--text-hint': '#999999',
  '--text-inverse': '#FFFFFF',
  '--border-color': '#E5E5E5',
}

export function getThemeState(): ThemeState {
  const stored = uni.getStorageSync(THEME_KEY)
  if (stored) {
    const mode = stored as ThemeMode
    return {
      mode,
      isDark: mode === 'dark' || (mode === 'system' && prefersDark()),
    }
  }
  return { mode: 'light', isDark: false }
}

export function setThemeMode(mode: ThemeMode) {
  uni.setStorageSync(THEME_KEY, mode)
  applyTheme()
  notifyListeners()
}

function prefersDark(): boolean {
  // #ifdef H5
  return window.matchMedia?.('(prefers-color-scheme: dark)').matches ?? false
  // #endif
  // #ifndef H5
  return false
  // #endif
}

export function applyTheme() {
  const { isDark } = getThemeState()
  const vars = isDark ? darkVars : lightVars

  // #ifdef H5
  const root = document.documentElement
  Object.entries(vars).forEach(([key, value]) => {
    root.style.setProperty(key, value)
  })
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
