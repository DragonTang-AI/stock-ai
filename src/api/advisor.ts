/**
 * 智能投资助手 API
 * T-M012
 */
import { request } from '@/utils/request'

// ============ 类型定义 ============

export interface MarketIndices {
  name: string
  price: number
  change_pct: number
}

export interface MarketTemperature {
  emoji: string
  temperature_text: string
  avg_change_pct: number
  indices: MarketIndices[]
}

export interface Signal {
  type: 'bullish' | 'bearish' | 'warning' | 'info'
  name: string
  desc: string
}

export interface PositionDiagnosis {
  symbol: string
  name: string
  profit_pct: number
  weight: number
  rating: 'healthy' | 'neutral' | 'caution' | 'risk'
  rating_text: string
  confidence: number
  signals: Signal[]
  action: {
    action: string
    text: string
    reason: string
  }
}

export interface RiskItem {
  level: 'high' | 'medium' | 'low' | 'info'
  title: string
  desc: string
  action: string
}

export interface SuggestionItem {
  priority: 'high' | 'medium' | 'low'
  text: string
  reason: string
}

export interface DiagnosisSummary {
  total_equity: number
  cash: number
  market_value: number
  total_profit: number
  total_profit_pct: number
  position_count: number
  win_rate: number
  cash_ratio: number
}

export interface DiagnosisData {
  summary: DiagnosisSummary
  positions: PositionDiagnosis[]
  risks: RiskItem[]
  suggestions: SuggestionItem[]
  market_temperature: MarketTemperature
  disclaimer: string
}

export interface DiagnosisResponse {
  success: boolean
  data: DiagnosisData
}

// ============ API ============

export async function getDiagnosis(): Promise<DiagnosisData> {
  const res = await request<DiagnosisResponse>('/analysis/diagnose', { method: 'GET' })
  return (res as any).data || res
}

export async function getMarketTemperature(): Promise<MarketTemperature> {
  const res = await request<{ success: boolean; data: MarketTemperature }>('/analysis/market/temperature', { method: 'GET' })
  return (res as any).data || res
}

export async function getChatContext(question: string, model: string = 'deepseek-v4-flash'): Promise<any> {
  const res = await request('/analysis/chat/context', {
    method: 'POST',
    data: { question, model },
  })
  return res
}

// ============ SSE 流式对话 ============

const SSE_BASE = import.meta.env.VITE_API_BASE_URL || '/api/v1'

export function chatStream(
  question: string,
  model: string,
  onToken: (token: string) => void,
  onDone: () => void,
  onError: (err: string) => void
): AbortController {
  const token = uni.getStorageSync('accessToken')
  const ctrl = new AbortController()

  fetch(`${SSE_BASE}/analysis/chat/stream`, {
    method: 'POST',
    headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}), 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, model }),
    signal: ctrl.signal,
  }).then(async res => {
    if (!res.ok) { onError(`请求失败: HTTP ${res.status}`); return }

    const reader = res.body!.getReader()
    const decoder = new TextDecoder()
    let buf = ''

    try {
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buf += decoder.decode(value, { stream: true })
        const lines = buf.split('\n')
        buf = lines.pop() || ''
        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const payload = line.slice(6).trim()
          if (payload === '[DONE]') { onDone(); return }
          try {
            const data = JSON.parse(payload)
            if (data.token) onToken(data.token)
            else if (data.error) onError(data.error)
          } catch { /* skip unparseable */ }
        }
      }
      onDone()
    } catch (err: any) {
      if (err.name !== 'AbortError') onError(err.message || '读取流失败')
    }
  }).catch(err => {
    if (err.name !== 'AbortError') onError(err.message || '网络错误')
  })

  return ctrl
}
