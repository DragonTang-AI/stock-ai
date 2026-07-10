/**
 * AI-Stock 国际化入口
 * 使用方式: import { t } from '@/locale'; t('settings.title')
 */
import zhCN from './zh-CN'

export type Locale = 'zh-CN' | 'zh-TW' | 'en'
export type LocaleMessages = typeof zhCN

const messages: Record<Locale, LocaleMessages> = {
  'zh-CN': zhCN,
  'zh-TW': null as any, // lazy load
  'en': null as any,    // lazy load
}

let currentLocale: Locale = 'zh-CN'

const LOCALE_KEY = 'ai-stock:locale'

/** 获取当前语言 */
export function getLocale(): Locale {
  try {
    const stored = uni.getStorageSync(LOCALE_KEY)
    if (stored && ['zh-CN', 'zh-TW', 'en'].includes(stored)) {
      currentLocale = stored as Locale
    }
  } catch { /* ignore */ }
  return currentLocale
}

/** 设置语言 */
export async function setLocale(locale: Locale) {
  currentLocale = locale
  uni.setStorageSync(LOCALE_KEY, locale)

  // 延迟加载非默认语言
  if (locale === 'zh-TW' && !messages['zh-TW']) {
    messages['zh-TW'] = (await import('./zh-TW')).default
  } else if (locale === 'en' && !messages['en']) {
    messages['en'] = (await import('./en')).default
  }
}

/**
 * 获取翻译文本
 * 支持路径嵌套：t('settings.preference') => 偏好设置
 */
export function t(key: string): string {
  const locale = currentLocale
  const msg = messages[locale]
  if (!msg) return key

  const parts = key.split('.')
  let result: any = msg
  for (const part of parts) {
    if (result && typeof result === 'object' && part in result) {
      result = result[part]
    } else {
      return key
    }
  }
  return typeof result === 'string' ? result : key
}

/**
 * 带参数插值
 * 用法: tc('time.minutesAgo', { n: 5 }) => '5分钟前'
 */
export function tc(key: string, params: Record<string, string | number>): string {
  let text = t(key)
  Object.entries(params).forEach(([k, v]) => {
    text = text.replace(`{${k}}`, String(v))
  })
  return text
}

/** 初始化语言 */
export function initLocale() {
  const locale = getLocale()
  if (locale !== 'zh-CN') {
    setLocale(locale)
  }
}
