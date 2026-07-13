/**
 * 持仓/交易 API
 * 对接后端 /api/v1/portfolio/*
 */
import { request } from '@/utils/request'

// ---- 账户 ----
export interface AccountInfo {
  account_id: number
  balance: number
  frozen: number
  total_equity: number
  market_value: number
  profit: number
  profit_pct: number
  market: string
  created_at: string
}

export async function getAccount(): Promise<AccountInfo> {
  const res = await request<{ success: boolean; data: AccountInfo }>('/portfolio/account', { method: 'GET' })
  return (res as any).data
}

// ---- 持仓 ----
export interface PositionItem {
  id: number
  symbol: string
  name: string
  quantity: number
  available_quantity: number
  avg_cost: number
  current_price: number
  market_value: number
  profit: number
  profit_pct: number
  market: string
}

export interface PositionsResponse {
  data: PositionItem[]
  summary: {
    total_market_value: number
    total_profit: number
    total_cost: number
    total_profit_pct: number
  }
}

export async function getPositions(): Promise<PositionsResponse> {
  const res = await request<{ success: boolean; data: PositionItem[]; summary: any }>('/portfolio/positions', { method: 'GET' })
  return { data: (res as any).data || [], summary: (res as any).summary || {} }
}

// ---- 订单 ----
export interface OrderItem {
  id: number
  symbol: string
  name?: string
  side: 'buy' | 'sell'
  order_type: string
  quantity: number
  filled_quantity: number
  price: number | null
  status: string
  created_at: string
  updated_at: string
  error_msg?: string
}

export async function getOrders(status?: string): Promise<{ data: OrderItem[]; total: number }> {
  const params: Record<string, string> = {}
  if (status && status !== 'all') params.status = status
  const res = await request<{ success: boolean; data: OrderItem[]; total: number }>('/portfolio/orders', { method: 'GET', params })
  return { data: (res as any).data || [], total: (res as any).total || 0 }
}

export interface PlaceOrderRequest {
  symbol: string
  side: 'buy' | 'sell'
  quantity: number
  order_type: string
}

export async function placeOrder(order: PlaceOrderRequest, silent = false): Promise<OrderItem> {
  const res = await request<{ success: boolean; data: OrderItem }>('/portfolio/orders', {
    method: 'POST',
    data: order,
    silent,
  })
  return (res as any).data
}

export async function cancelOrder(orderId: number): Promise<void> {
  await request(`/portfolio/orders/${orderId}`, { method: 'DELETE' })
}

// ---- 成交 ----
export interface TradeItem {
  id: number
  order_id: number
  symbol: string
  name?: string
  side: 'buy' | 'sell'
  quantity: number
  price: number
  amount: number
  created_at: string
}

export async function getTrades(): Promise<{ data: TradeItem[]; total: number }> {
  const res = await request<{ success: boolean; data: TradeItem[]; total: number }>('/portfolio/trades', { method: 'GET' })
  return { data: (res as any).data || [], total: (res as any).total || 0 }
}

// T-M011 持仓分析

export interface PositionAnalytics {
  position_count: number
  total_market_value: number
  total_profit: number
  total_profit_pct: number
  daily_profit: number
  daily_profit_pct: number
  win_rate: number
  best_position: {
    symbol: string
    name: string
    profit: number
    profit_pct: number
    market_value: number
    weight: number
  } | null
  worst_position: {
    symbol: string
    name: string
    profit: number
    profit_pct: number
    market_value: number
    weight: number
  } | null
  top_holdings_concentration: number
  top_holdings: Array<{
    symbol: string
    name: string
    market_value: number
    weight: number
    profit: number
  }>
  holdings_distribution: Array<{
    sector: string
    market_value: number
    weight: number
    profit: number
    count: number
  }>
}

export async function getPortfolioAnalytics(): Promise<PositionAnalytics> {
  const res = await request<{ success: boolean; data: PositionAnalytics }>('/portfolio/analytics', { method: 'GET' })
  return (res as any).data || {}
}


/** 模拟充值 → /portfolio/topup */
export interface TopupResult {
  success: boolean
  balance: number
  initial_cash: number
  topup_amount: number
  message: string
}

export async function topupAccount(amount: number): Promise<TopupResult> {
  const res = await request<TopupResult>(
    `/portfolio/topup?amount=${amount}`,
    { method: 'POST' }
  )
  return res as any
}
