/**
 * 交易 API
 * 对应后端 /api/v1/trading
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
  | 'insufficient_cash'
  | 'insufficient_position'
  | 'price_limit'
  | 'lot_size'
  | 'market_closed'
  | 'suspended'
  | 'signal_expired'
  | 'risk_position_cap'
  | 'invalid_symbol'

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
  price?: number   // LIMIT 必填
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
  lot_size: number        // 最小交易单位
  price_limit_pct: number // 涨跌停幅度 %
  commission_rate: number // 佣金费率（小数）
  min_commission: number  // 最低佣金
  stamp_tax_rate: number  // 印花税费率
  stamp_tax_side: 'SELL' | 'BOTH'
  settlement: 'T+0' | 'T+1'
}

// ─── API ───

/** 获取账户信息（缓存 1 分钟） */
export function fetchAccount(market?: 'A' | 'HK'): Promise<Account> {
  return cachedRequest(
    'trading:account',
    () => request<{ success: boolean; data: Account }>(
      '/trading/account',
      { method: 'GET', params: market ? { market } : undefined }
    ).then(res => res.data),
    { market },
    { ttl: 60 * 1000 }
  )
}

/** 获取持仓列表（缓存 30 秒） */
export function fetchPositions(): Promise<Position[]> {
  return cachedRequest(
    'trading:positions',
    () => request<{ success: boolean; data: Position[] }>(
      '/trading/positions',
      { method: 'GET' }
    ).then(res => res.data),
    undefined,
    { ttl: 30 * 1000 }
  )
}

/** 获取交易标的行情 */
export function fetchTradingStockInfo(symbol: string): Promise<TradingStockInfo> {
  return request<{ success: boolean; data: TradingStockInfo }>(
    `/trading/stock/${symbol}`,
    { method: 'GET' }
  ).then(res => res.data)
}

/** 预估费用 */
export function estimateFee(params: FeeEstimateRequest): Promise<FeeEstimateResponse> {
  return request<{ success: boolean; data: FeeEstimateResponse }>(
    '/trading/estimate-fee',
    { method: 'POST', data: params }
  ).then(res => res.data)
}

/** 下单 */
export function placeOrder(params: PlaceOrderRequest): Promise<Order> {
  return request<{ success: boolean; data: Order }>(
    '/trading/order',
    { method: 'POST', data: params }
  ).then(res => res.data)
}

/** 获取市场规则（缓存 1 小时，规则基本不变） */
export function fetchMarketRule(market: 'A' | 'HK'): Promise<MarketRule> {
  return cachedRequest(
    'trading:marketRule',
    () => request<{ success: boolean; data: MarketRule }>(
      `/trading/market-rule/${market}`,
      { method: 'GET' }
    ).then(res => res.data),
    { market },
    { ttl: 60 * 60 * 1000 }
  )
}

/** 清除交易相关缓存（下单/撤单后调用） */
export function clearTradingCache(): void {
  clearCache('trading:account')
  clearCache('trading:positions')
}
