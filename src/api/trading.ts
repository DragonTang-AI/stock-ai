/**
 * 交易 API
 * 后端端点: /api/v1/portfolio/account, /positions, /orders
 *          /api/v1/simulation/orders, /api/v1/market/detail/{symbol}
 */
import { request } from '@/utils/request'
import { cachedRequest, clearCache } from '@/utils/cache'

// ─── 账户 ───

export interface Account {
  id: string
  user_id: string
  account_type: 'PAPER' | 'LIVE'
  mode: 'MANUAL' | 'AI_HOSTED'
  market: 'A' | 'HK'
  currency: 'CNY' | 'HKD'
  initial_cash: number
  cash: number
  frozen_cash: number
  status: 'ACTIVE' | 'SUSPENDED' | 'CLOSED'
}

// ─── 持仓 ───

export interface Position {
  id: string
  account_id: string
  symbol: string
  market: 'A' | 'HK'
  qty: number
  available_qty: number
  frozen_qty: number
  avg_cost: number
  last_price: number | null
  market_value: number
  realized_pnl: number
  unrealized_pnl: number
}

// ─── 订单 ───

export type OrderSide = 'buy' | 'sell'
export type OrderType = 'MARKET' | 'LIMIT'
export type OrderStatus = 'PENDING' | 'PARTIAL' | 'FILLED' | 'CANCELLED' | 'REJECTED' | 'EXPIRED'
export type OrderSource = 'MANUAL' | 'AI_HOSTED'
export type RejectReason =
  | 'insufficient_cash' | 'insufficient_position' | 'price_limit'
  | 'lot_size' | 'market_closed' | 'suspended' | 'signal_expired'
  | 'risk_position_cap' | 'invalid_symbol'

export interface Order {
  id: string
  account_id: string
  symbol: string
  market: 'A' | 'HK'
  currency: string
  side: OrderSide
  order_type: OrderType
  price: number | null
  qty: number
  filled_qty: number
  avg_fill_price: number | null
  status: OrderStatus
  source: OrderSource
  reject_reason: RejectReason | null
  created_at: string
}

// ─── 成交 ───

export interface Trade {
  id: string
  order_id: string
  account_id: string
  symbol: string
  market: string
  side: string
  price: number
  qty: number
  amount: number
  commission: number
  stamp_tax: number
  other_fees: number
  net_amount: number
  realized_pnl: number
  traded_at: string
}

// ─── 行情快照（下单面板用） ───

export interface TradingStockInfo {
  symbol: string
  name: string
  market: 'A' | 'HK'
  price: number
  change_pct: number
  pre_close: number
  high: number
  low: number
  currency: 'CNY' | 'HKD'
}

// ─── 下单请求 ───
// 字段名与后端 /simulation/orders 接口对齐:
//   action  小写 'buy'|'sell'
//   quantity 整数，100 的整数倍
//   order_type  大写 'MARKET'|'LIMIT'

export interface PlaceOrderRequest {
  symbol: string
  action: 'buy' | 'sell'
  order_type: 'MARKET' | 'LIMIT'
  quantity: number
  price?: number
}

// ─── 费用预估请求/响应 ───

export interface FeeEstimateRequest {
  symbol: string
  side: OrderSide
  price: number
  qty: number
}

export interface FeeEstimateResponse {
  amount: number
  commission: number
  stamp_tax: number
  other_fees: number
  total_fee: number
  net_amount: number
}

// ─── 市场规则 ───

export interface MarketRule {
  market: 'A' | 'HK'
  lot_size: number
  price_limit_pct: number
  commission_rate: number
  min_commission: number
  stamp_tax_rate: number
  stamp_tax_side: 'SELL' | 'BOTH'
  settlement: 'T+0' | 'T+1'
}

// ─── API ───

/** 获取账户信息 → /portfolio/account */
export function fetchAccount(market?: 'A' | 'HK'): Promise<Account> {
  return cachedRequest(
    'trading:account',
    () => request<any>('/portfolio/account', { method: 'GET' })
      .then(res => {
        const d = res?.data || res || {}
        return {
          id: d.id || d.account_id || '',
          user_id: d.user_id || '',
          account_type: d.account_type || 'PAPER',
          mode: d.mode || 'MANUAL',
          market: d.market || market || 'A',
          currency: d.currency || 'CNY',
          initial_cash: d.initial_cash ?? 0,
          cash: d.cash ?? d.available_cash ?? 0,
          frozen_cash: d.frozen_cash ?? 0,
          status: d.status || 'ACTIVE',
        }
      }),
    { market },
    { ttl: 60 * 1000 }
  )
}

/** 获取持仓列表 → /portfolio/positions */
export function fetchPositions(): Promise<Position[]> {
  return cachedRequest(
    'trading:positions',
    () => request<any>('/portfolio/positions', { method: 'GET' })
      .then(res => {
        const d = res?.data || res || {}
        const positions = d.positions || d || []
        const list = Array.isArray(positions) ? positions : []
        return list.map((item: any) => ({
          id: item.id || '',
          account_id: item.account_id || '',
          symbol: item.symbol || '',
          market: item.market || 'A',
          qty: item.qty ?? item.quantity ?? 0,
          available_qty: item.available_qty ?? item.qty ?? 0,
          frozen_qty: item.frozen_qty ?? 0,
          avg_cost: item.avg_cost ?? item.cost ?? 0,
          last_price: item.last_price ?? item.current_price ?? null,
          market_value: item.market_value ?? 0,
          realized_pnl: item.realized_pnl ?? 0,
          unrealized_pnl: item.unrealized_pnl ?? 0,
        }))
      }),
    undefined,
    { ttl: 30 * 1000 }
  )
}

/** 获取交易标的行情 → /market/detail/{symbol} */
export function fetchTradingStockInfo(symbol: string): Promise<TradingStockInfo> {
  return request<any>(`/market/detail/${encodeURIComponent(symbol)}`, { method: 'GET' })
    .then(res => {
      const d = res?.data || res || {}
      return {
        symbol: d.symbol || symbol,
        name: d.name || symbol,
        market: d.market || 'A',
        price: d.price ?? 0,
        change_pct: d.change_pct ?? 0,
        pre_close: d.prev_close ?? 0,
        high: d.high ?? 0,
        low: d.low ?? 0,
        currency: d.currency || 'CNY',
      }
    })
}

/** 预估费用（模拟计算，后端暂无此端点） */
export function estimateFee(params: FeeEstimateRequest): Promise<FeeEstimateResponse> {
  const { price, qty } = params
  const amount = price * qty
  const commission = Math.max(5, amount * 0.00025)
  const stampTax = amount * 0.001
  const otherFees = amount * 0.00002
  const totalFee = commission + stampTax + otherFees
  return Promise.resolve({
    amount,
    commission: Math.round(commission * 100) / 100,
    stamp_tax: Math.round(stampTax * 100) / 100,
    other_fees: Math.round(otherFees * 100) / 100,
    total_fee: Math.round(totalFee * 100) / 100,
    net_amount: Math.round((amount - totalFee) * 100) / 100,
  })
}

/** 下单 → /simulation/orders
 * @description 将前端 PlaceOrderRequest 映射为后端期望的请求体:
 *   - action: 小写 'buy'|'sell'
 *   - quantity: 整数（100 的整数倍，由调用方保证）
 *   - order_type: 大写 'MARKET'|'LIMIT'
 *   - price: 数字
 */
export function placeOrder(params: PlaceOrderRequest): Promise<Order> {
  const q = new URLSearchParams()
  q.set('symbol', params.symbol)
  q.set('side', params.action)
  q.set('qty', String(params.quantity))
  if (params.price != null) q.set('price', String(params.price))
  return request<any>(`/simulation/orders?${q.toString()}`, { method: 'POST', silent: true })
    .then(res => {
      const data = res?.data || res
      if (!data || data.success === false) {
        const err: any = new Error(data?.message || 'Place order failed')
        err.errorCode = data?.code || 'ORDER_FAILED'
        err.detail = data?.message
        throw err
      }
      return data
    })
}


// ──────────────────────────────────────────────────
// 模拟持仓 / 订单 / 成交（P1-5）
// ──────────────────────────────────────────────────

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

export interface SimPosition {
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

export interface SimOrder {
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

export interface SimTrade {
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

/** 模拟账户 → /simulation/account */
export function fetchSimulationAccount(): Promise<AccountInfo> {
  return request<any>('/simulation/account', { method: 'GET' })
    .then(res => (res?.data || res || {}))
}

/** 模拟持仓 → /simulation/positions */
export function fetchSimulationPositions(): Promise<{ data: SimPosition[]; summary: any }> {
  return request<any>('/simulation/positions', { method: 'GET' })
    .then(res => ({ data: res?.data || [], summary: res?.summary || {} }))
}

/** 模拟订单历史 → /simulation/orders */
export function fetchSimulationOrders(status?: string): Promise<{ data: SimOrder[]; total: number }> {
  const params: Record<string, string> = {}
  if (status && status !== 'all') params.status = status
  return request<any>('/simulation/orders', { method: 'GET', params })
    .then(res => ({ data: res?.data || [], total: res?.total || 0 }))
}

/** 模拟成交记录 → /simulation/trades */
export function fetchSimulationTrades(): Promise<{ data: SimTrade[]; total: number }> {
  return request<any>('/simulation/trades', { method: 'GET' })
    .then(res => ({ data: res?.data || [], total: res?.total || 0 }))
}

/** 获取市场规则 → /market/rules/{market} */
export function fetchMarketRule(market: 'A' | 'HK'): Promise<MarketRule> {
  return request<any>(`/market/rules/${market}`, { method: 'GET' })
    .then(res => res?.data || res || {})
}

/** 清除交易相关缓存 */
export function clearTradingCache(): void {
  clearCache('trading:account')
  clearCache('trading:positions')
}
