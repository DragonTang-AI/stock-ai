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

export interface PlaceOrderRequest {
  symbol: string
  side: OrderSide
  order_type: OrderType
  qty: number
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

/** 下单 → /simulation/orders */
export function placeOrder(params: PlaceOrderRequest): Promise<Order> {
  return request<any>('/simulation/orders', { method: 'POST', data: params })
    .then(res => res?.data || res || {})
}

/** 获取市场规则（使用常量，后端暂无此端点） */
export function fetchMarketRule(market: 'A' | 'HK'): Promise<MarketRule> {
  const rules: Record<string, MarketRule> = {
    A: {
      market: 'A', lot_size: 100, price_limit_pct: 10,
      commission_rate: 0.00025, min_commission: 5, stamp_tax_rate: 0.001,
      stamp_tax_side: 'SELL', settlement: 'T+1',
    },
    HK: {
      market: 'HK', lot_size: 100, price_limit_pct: 0,
      commission_rate: 0.0003, min_commission: 5, stamp_tax_rate: 0.0013,
      stamp_tax_side: 'BOTH', settlement: 'T+0',
    },
  }
  return Promise.resolve(rules[market])
}

/** 清除交易相关缓存 */
export function clearTradingCache(): void {
  clearCache('trading:account')
  clearCache('trading:positions')
}
