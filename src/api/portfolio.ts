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

export async function getAccount(market?: string): Promise<AccountInfo> {
  const params: Record<string, string> = {}
  if (market) params.market = market
  const res = await request<{ success: boolean; data: AccountInfo }>('/portfolio/account', { method: 'GET', params })
  return (res as any).data
}

/** 初始化港股账户 */
export async function initHKAccount(): Promise<AccountInfo> {
  const res = await request<{ success: boolean; data: AccountInfo }>('/portfolio/account/init-hk', { method: 'POST' })
  return (res as any).data
}

// ---- 市场规则 ----
export interface MarketRules {
  market: string
  lot_size: number | null
  price_limit_pct: number | null
  commission_rate: number
  min_commission: number
  stamp_tax_rate: number
  stamp_tax_side: 'BOTH' | 'SELL'
  settlement: string
  trading_hours: {
    morning: string
    afternoon: string
  }
  trading_currency: string
  trading_currency_symbol: string
}

export async function getMarketRules(market: string): Promise<MarketRules> {
  const res = await request<{ success: boolean; data: MarketRules }>(`/market/rules/${market}`, { method: 'GET' })
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

export async function getPositions(market?: string): Promise<PositionsResponse> {
  const params: Record<string, string> = {}
  if (market) params.market = market
  const res = await request<{ success: boolean; data: PositionItem[]; summary: any }>('/portfolio/positions', { method: 'GET', params })
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
  market?: string
}

export async function getOrders(status?: string, market?: string): Promise<{ data: OrderItem[]; total: number }> {
  const params: Record<string, string> = {}
  if (status && status !== 'all') params.status = status
  if (market) params.market = market
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
  source?: 'agent' | 'user'
  trader_name?: string | null
}

export async function getTrades(market?: string): Promise<{ data: TradeItem[]; total: number }> {
  const params: Record<string, string> = {}
  if (market) params.market = market
  const res = await request<{ success: boolean; data: TradeItem[]; total: number }>('/portfolio/trades', { method: 'GET', params })
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

export async function getPortfolioAnalytics(market?: string): Promise<PositionAnalytics> {
  const params = market ? `?market=${market}` : ''
  const res = await request<{ success: boolean; data: PositionAnalytics }>(`/portfolio/analytics${params}`, { method: 'GET' })
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

export async function topupAccount(amount: number, market?: string): Promise<TopupResult> {
  const params = market ? `&market=${market}` : ''
  const res = await request<TopupResult>(
    `/portfolio/topup?amount=${amount}${params}`,
    { method: 'POST' }
  )
  return res as any
}
