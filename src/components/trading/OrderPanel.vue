<template>
  <view class="order-panel">
    <!-- 股票基本信息 -->
    <view class="stock-header">
      <view class="stock-main">
        <text class="stock-name">{{ stockInfo.name || '--' }}</text>
        <text class="stock-symbol">{{ stockInfo.symbol || '--' }}</text>
      </view>
      <view class="stock-price-col">
        <text class="stock-price" :class="priceClass">{{ formatPrice(stockInfo.price) }}</text>
        <text class="stock-change" :class="priceClass">{{ formatChange(stockInfo.change_pct) }}</text>
      </view>
    </view>
    <view class="market-tag">{{ marketLabel }}</view>

    <!-- 当前持仓（P1-5） -->
    <view class="position-card" v-if="currentPosition">
      <view class="position-header">
        <text class="position-title">我的持仓</text>
        <text class="position-pnl" :class="positionInfo.profit >= 0 ? 'up' : 'down'">
          {{ positionInfo.profit >= 0 ? '+' : '' }}{{ positionInfo.profit.toFixed(2) }}
          ({{ positionInfo.profit_pct >= 0 ? '+' : '' }}{{ positionInfo.profit_pct.toFixed(2) }}%)
        </text>
      </view>
      <view class="position-stats">
        <view class="pos-stat-item">
          <text class="pos-stat-label">持仓</text>
          <text class="pos-stat-value">{{ positionInfo.hold_qty }} 股</text>
        </view>
        <view class="pos-stat-item">
          <text class="pos-stat-label">可卖</text>
          <text class="pos-stat-value">{{ positionInfo.available }} 股</text>
        </view>
        <view class="pos-stat-item">
          <text class="pos-stat-label">成本</text>
          <text class="pos-stat-value">{{ positionInfo.avg_cost.toFixed(2) }}</text>
        </view>
        <view class="pos-stat-item">
          <text class="pos-stat-label">市值</text>
          <text class="pos-stat-value">{{ positionInfo.market_value.toFixed(2) }}</text>
        </view>
      </view>
    </view>

    <!-- 交易方向 -->
    <view class="side-switch">
      <view
        class="side-btn"
        :class="{ active: side === 'buy' }"
        @click="switchSide('buy')"
      >买入</view>
      <view
        class="side-btn"
        :class="{ active: side === 'sell' }"
        @click="switchSide('sell')"
      >卖出</view>
    </view>

    <!-- 数量选择 -->
    <view class="section">
      <text class="section-label">委托数量（股）</text>
      <view class="qty-presets">
        <view
          v-for="n in presetQtys"
          :key="n"
          class="qty-chip"
          :class="{ active: qty === n }"
          @click="setQty(n)"
        >{{ n }}</view>
        <view class="qty-chip custom" :class="{ active: customQty }" @click="focusCustom">
          <input
            ref="customInput"
            class="custom-input"
            type="number"
            :value="customQty || ''"
            placeholder="自定义"
            :adjust-position="true"
            :cursor-spacing="20"
            @input="onCustomQty"
          />
        </view>
      </view>
      <text v-if="qtyHint" class="qty-hint">{{ qtyHint }}</text>
    </view>

    <!-- 价格显示 -->
    <view class="section">
      <text class="section-label">委托价格（元）</text>
      <view class="price-display">
        <text class="price-value">{{ formatPrice(currentPrice) }}</text>
        <text class="price-note">市价单按撮合价成交</text>
      </view>
    </view>

    <!-- 预估金额 -->
    <view class="section">
      <view class="amount-row">
        <text class="amount-label">预估金额</text>
        <text class="amount-value">¥ {{ formatAmount(estimatedAmount) }}</text>
      </view>
      <view class="fee-breakdown">
        <view class="fee-row">
          <text class="fee-name">佣金（万2.5）</text>
          <text class="fee-val">¥ {{ formatAmount(estimatedCommission) }}</text>
        </view>
        <view v-if="side === 'sell'" class="fee-row">
          <text class="fee-name">印花税（卖出）</text>
          <text class="fee-val">¥ {{ formatAmount(estimatedStampTax) }}</text>
        </view>
        <view class="fee-row">
          <text class="fee-name">其他费用</text>
          <text class="fee-val">¥ {{ formatAmount(estimatedOtherFees) }}</text>
        </view>
        <view class="fee-row total">
          <text class="fee-name">总费用</text>
          <text class="fee-val">¥ {{ formatAmount(estimatedTotalFee) }}</text>
        </view>
      </view>
    </view>

    <!-- 可用资金 / 可用持仓 -->
    <view class="section balance-row">
      <view v-if="side === 'buy'" class="balance-item">
        <text class="balance-label">可用资金</text>
        <text class="balance-value" :class="{ danger: !sufficientCash }">¥ {{ formatAmount(accountCash) }}</text>
      </view>
      <view v-else class="balance-item">
        <text class="balance-label">可卖数量</text>
        <text class="balance-value">{{ availableQty }} 股</text>
      </view>
      <view class="balance-item">
        <text class="balance-label">所需资金</text>
        <text class="balance-value" :class="{ danger: !sufficientCash }">¥ {{ formatAmount(requiredFunds) }}</text>
      </view>
    </view>

    <!-- 余额不足提示 -->
    <view v-if="side === 'buy' && !sufficientCash" class="warn-box">
      <text class="warn-text">可用资金不足，当前可用 ¥{{ formatAmount(accountCash) }}，所需 ¥{{ formatAmount(requiredFunds) }}</text>
    </view>
    <view v-if="side === 'sell' && !sufficientPosition" class="warn-box">
      <text class="warn-text">可卖数量不足，当前可卖 {{ availableQty }} 股，委托 {{ qty }} 股</text>
    </view>

    <!-- MarketRule 规则提示 -->
    <view class="rule-box">
      <view class="rule-title">交易规则提示</view>
      <view class="rule-item" v-for="rule in ruleHints" :key="rule">{{ rule }}</view>
    </view>

    <!-- 确认按钮 -->
    <button
      class="confirm-btn"
      :class="{ buy: side === 'buy', sell: side === 'sell' }"
      :disabled="!canSubmit"
      @click="handleConfirm"
    >{{ side === 'buy' ? '确认买入' : '确认卖出' }}</button>
  </view>

  <!-- 确认弹窗 -->
  <OrderConfirm
    v-if="showConfirm"
    :visible="showConfirm"
    :order="pendingOrder"
    :account-cash="accountCash"
    :available-qty="availableQty"
    :estimated-fee="estimatedTotalFee"
    @confirm="handlePlaceOrder"
    @cancel="showConfirm = false"
  />
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import OrderConfirm from './OrderConfirm.vue'
import type {
  TradingStockInfo,
  OrderSide,
  FeeEstimateResponse,
  MarketRule,
} from '@/api/trading'
import { fetchSimulationPositions, type SimPosition } from '@/api/trading'
import {
  fetchTradingStockInfo,
  estimateFee,
  fetchAccount,
  fetchMarketRule,
} from '@/api/trading'

const props = defineProps<{
  symbol: string
  market?: 'A' | 'HK'
}>()

const emit = defineEmits<{
  (e: 'order-placed', order: any): void
}>()

// ─── 状态 ───
const side = ref<OrderSide>('buy')
const qty = ref(100)
const customQty = ref<number | null>(null)
const stockInfo = ref<TradingStockInfo>({} as TradingStockInfo)
const accountCash = ref(0)
const availableQty = ref(0)
const currentPosition = ref<SimPosition | null>(null)
const allPositions = ref<SimPosition[]>([])

// 当前股票的持仓信息
const positionInfo = computed(() => {
  if (!currentPosition.value) return null
  const pos = currentPosition.value
  return {
    hold_qty: pos.quantity,
    available: pos.available_quantity,
    avg_cost: pos.avg_cost,
    current_price: pos.current_price,
    market_value: pos.market_value,
    profit: pos.profit,
    profit_pct: pos.profit_pct,
  }
})
const showConfirm = ref(false)
const pendingOrder = ref<any>(null)
const ruleHints = ref<string[]>([])

// 费用预估
const estimatedCommission = ref(0)
const estimatedStampTax = ref(0)
const estimatedOtherFees = ref(0)
const estimatedTotalFee = ref(0)
const estimatedAmount = ref(0)

// 市场规则
const marketRule = ref<MarketRule | null>(null)

const presetQtys = [100, 200, 500]

// ─── 计算 ───
const currentPrice = computed(() => stockInfo.value?.price || 0)

const marketLabel = computed(() => {
  const m = stockInfo.value?.market || props.market || 'A'
  return m === 'A' ? 'A股' : '港股'
})

const priceClass = computed(() => {
  const pct = stockInfo.value?.change_pct || 0
  return pct > 0 ? 'up' : pct < 0 ? 'down' : ''
})

const sufficientCash = computed(() => {
  return accountCash.value >= requiredFunds.value
})

const sufficientPosition = computed(() => {
  return availableQty.value >= qty.value
})

const canSubmit = computed(() => {
  if (!qty.value || qty.value <= 0) return false
  if (side.value === 'buy') return sufficientCash.value
  return sufficientPosition.value
})

const requiredFunds = computed(() => {
  const price = currentPrice.value || 0
  return Math.round(price * qty.value * 100 + estimatedTotalFee.value * 100) / 100
})

// ─── 方法 ───
function switchSide(s: OrderSide) {
  side.value = s
  refreshFeeEstimate()
}

function setQty(n: number) {
  qty.value = n
  customQty.value = null
  refreshFeeEstimate()
}

function focusCustom() {
  // 让 input 获得焦点（uni-app 中通过 ref 处理）
}

function onCustomQty(e: any) {
  const v = parseInt(e.detail.value || e.target?.value || '0', 10)
  if (v > 0) {
    customQty.value = v
    qty.value = v
    refreshFeeEstimate()
  }
}

function formatPrice(v: number | null | undefined): string {
  if (v == null || isNaN(v)) return '--'
  return v.toFixed(2)
}

function formatChange(v: number | null | undefined): string {
  if (v == null || isNaN(v)) return ''
  const prefix = v > 0 ? '+' : ''
  return `${prefix}${v.toFixed(2)}%`
}

function formatAmount(v: number): string {
  if (isNaN(v)) return '0.00'
  return v.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ',')
}

async function loadPositionForSymbol() {
  try {
    const res = await fetchSimulationPositions()
    allPositions.value = res.data || []
    const match = allPositions.value.find(
      p => p.symbol === props.symbol || p.symbol.replace('.', '') === props.symbol
    )
    currentPosition.value = match || null
    availableQty.value = match?.available_quantity ?? 0
  } catch {
    availableQty.value = 0
  }
}

async function refreshFeeEstimate() {
  if (!stockInfo.value?.symbol || !qty.value) return
  try {
    const res = await estimateFee({
      symbol: stockInfo.value.symbol,
      side: side.value,
      price: currentPrice.value,
      qty: qty.value,
    })
    estimatedCommission.value = res.commission
    estimatedStampTax.value = res.stamp_tax
    estimatedOtherFees.value = res.other_fees
    estimatedTotalFee.value = res.total_fee
    estimatedAmount.value = res.amount
  } catch {
    // 本地兜底计算（A股规则）
    calcFeeLocal()
  }
}

function calcFeeLocal() {
  const price = currentPrice.value || 0
  const q = qty.value || 0
  const amount = Math.round(price * q * 100) / 100
  // A股：佣金万2.5，最低5元；印花税卖出0.1%
  const commissionRate = 0.00025
  let commission = Math.round(amount * commissionRate * 100) / 100
  if (commission > 0 && commission < 5) commission = 5
  const stampTax = side.value === 'sell' ? Math.round(amount * 0.001 * 100) / 100 : 0
  const otherFees = Math.round(amount * 0.00002 * 100) / 100 // 过户费万0.2
  estimatedCommission.value = commission
  estimatedStampTax.value = stampTax
  estimatedOtherFees.value = otherFees
  estimatedTotalFee.value = Math.round((commission + stampTax + otherFees) * 100) / 100
  estimatedAmount.value = amount
}

const qtyHint = computed(() => {
  if (!marketRule.value) return ''
  const lot = marketRule.value.lot_size
  if (qty.value % lot !== 0) {
    return `数量须为 ${lot} 的整数倍`
  }
  return ''
})

async function loadStockInfo() {
  try {
    const info = await fetchTradingStockInfo(props.symbol)
    stockInfo.value = info
    if (!props.market) {
      // 自动识别市场
    }
    refreshFeeEstimate()
  } catch {
    uni.showToast({ title: '获取行情失败', icon: 'none' })
  }
}

async function loadAccount() {
  try {
    const acct = await fetchAccount(props.market || 'A')
    accountCash.value = acct.cash
  } catch {
    // 使用模拟数据
    accountCash.value = 1000000
  }
}

async function loadMarketRule() {
  const m = props.market || stockInfo.value?.market || 'A'
  try {
    const rule = await fetchMarketRule(m)
    marketRule.value = rule
    buildRuleHints(rule)
  } catch {
    // 兜底提示
    buildRuleHints(null)
  }
}

function buildRuleHints(rule: MarketRule | null) {
  const m = props.market || stockInfo.value?.market || 'A'
  if (m === 'A') {
    ruleHints.value = [
      `结算规则：${rule?.settlement || 'T+1'}（当日买入次日可卖）`,
      `交易单位：${rule?.lot_size || 100}股整数倍`,
      `涨跌停限制：±${rule?.price_limit_pct || 10}%`,
      `佣金费率：${(rule ? rule.commission_rate * 10000 : 2.5).toFixed(1)}‱（最低¥${rule?.min_commission || 5}）`,
      `印花税：${rule?.stamp_tax_rate ? (rule.stamp_tax_rate * 100).toFixed(1) + '%' : '0.1%'}（仅卖出收取）`,
    ]
  } else {
    ruleHints.value = [
      `结算规则：${rule?.settlement || 'T+0'}（当日买入当日可卖）`,
      `交易单位：${rule?.lot_size || 100}股整数倍`,
      `印花税费率：${(rule?.stamp_tax_rate ? rule.stamp_tax_rate * 100 : 0.13).toFixed(2)}%`,
    ]
  }
}

function handleConfirm() {
  if (!canSubmit.value) return
  pendingOrder.value = {
    symbol: stockInfo.value.symbol,
    name: stockInfo.value.name,
    side: side.value,
    qty: qty.value,
    price: currentPrice.value,
    amount: estimatedAmount.value,
    totalFee: estimatedTotalFee.value,
    commission: estimatedCommission.value,
    stamp_tax: estimatedStampTax.value,
    other_fees: estimatedOtherFees.value,
    market: stockInfo.value.market || props.market || 'A',
  }
  showConfirm.value = true
}

async function handlePlaceOrder() {
  showConfirm.value = false
  try {
    // 调用下单 API
    uni.showLoading({ title: '提交中...' })
    const { placeOrder } = await import('@/api/trading')
    const order = await placeOrder({
      symbol: stockInfo.value.symbol,
      side: side.value,
      order_type: 'MARKET',
      qty: qty.value,
    })
    uni.hideLoading()
    uni.showToast({ title: '下单成功', icon: 'success' })
    emit('order-placed', order)
    // 刷新账户资金
    loadAccount()
  } catch (err: any) {
    uni.hideLoading()
    uni.showToast({ title: err?.message || '下单失败', icon: 'none' })
  }
}

// ─── 生命周期 ───
onMounted(() => {
  loadStockInfo()
  loadAccount()
  loadMarketRule()
  loadPositionForSymbol()
})
</script>

<style lang="scss" scoped>
.order-panel {
  background: $bg-card;
  border-radius: $border-radius;
  padding: 28rpx;
  margin: 0 24rpx 24rpx;
}

// ─── 股票头部 ───
.stock-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12rpx;
}

.stock-main {
  display: flex;
  flex-direction: column;
  gap: 6rpx;
}

.stock-name {
  font-size: $font-size-lg;
  font-weight: 700;
  color: $text-primary;
}

.stock-symbol {
  font-size: $font-size-xs;
  color: $text-hint;
}

.stock-price-col {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4rpx;
}

.stock-price {
  font-size: 40rpx;
  font-weight: 700;
  color: $text-primary;

  &.up { color: #EF5350; }
  &.down { color: #26A69A; }
}

.stock-change {
  font-size: $font-size-sm;
  font-weight: 600;

  &.up { color: #EF5350; }
  &.down { color: #26A69A; }
}

.market-tag {
  display: inline-block;
  padding: 4rpx 14rpx;
  border-radius: 6rpx;
  font-size: 20rpx;
  font-weight: 600;
  color: $color-primary;
  background: rgba(74, 144, 226, 0.1);
  margin-bottom: 16rpx;
}

/* Position Card (P1-5) */
.position-card {
  background: linear-gradient(135deg, #f8fafc 0%, #eef2ff 100%);
  border: 1rpx solid #dbeafe;
  border-radius: 12rpx;
  padding: 20rpx;
  margin-bottom: 20rpx;
}
.position-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16rpx;
}
.position-title {
  font-size: 24rpx;
  font-weight: 600;
  color: $text-primary;
}
.position-pnl {
  font-size: 24rpx;
  font-weight: 700;
  &.up { color: $color-up; }
  &.down { color: $color-down; }
}
.position-stats {
  display: flex;
  gap: 8rpx;
}
.pos-stat-item {
  flex: 1;
  text-align: center;
  background: #fff;
  border-radius: 8rpx;
  padding: 12rpx 4rpx;
}
.pos-stat-label {
  display: block;
  font-size: 20rpx;
  color: $text-hint;
  margin-bottom: 4rpx;
}
.pos-stat-value {
  display: block;
  font-size: 22rpx;
  font-weight: 600;
  color: $text-primary;
}

// ─── 方向切换 ───
.side-switch {
  display: flex;
  gap: 0;
  margin-bottom: 28rpx;
  border-radius: 10rpx;
  overflow: hidden;
  border: 1rpx solid $border-color;
}

.side-btn {
  flex: 1;
  text-align: center;
  padding: 18rpx 0;
  font-size: $font-size-base;
  font-weight: 600;
  color: $text-secondary;
  background: $bg-card;
  transition: all 0.2s;

  &.active.buy {
    background: #EF5350;
    color: #fff;
  }
  &.active.sell {
    background: #26A69A;
    color: #fff;
  }
}

// ─── 区块 ───
.section {
  margin-bottom: 24rpx;
}

.section-label {
  display: block;
  font-size: $font-size-sm;
  color: $text-hint;
  margin-bottom: 12rpx;
}

// ─── 数量预设 ───
.qty-presets {
  display: flex;
  gap: 16rpx;
  flex-wrap: wrap;
}

.qty-chip {
  padding: 14rpx 32rpx;
  border-radius: 8rpx;
  font-size: $font-size-sm;
  font-weight: 600;
  color: $text-secondary;
  background: rgba(0, 0, 0, 0.04);
  border: 1rpx solid transparent;
  transition: all 0.15s;

  &.active {
    color: $color-primary;
    background: rgba(74, 144, 226, 0.1);
    border-color: $color-primary;
  }

  &.custom {
    padding: 0;
    background: transparent;
    border: none;
  }
}

.custom-input {
  width: 160rpx;
  padding: 14rpx 20rpx;
  border-radius: 8rpx;
  font-size: $font-size-sm;
  background: rgba(0, 0, 0, 0.04);
  text-align: center;
}

.qty-hint {
  display: block;
  font-size: 20rpx;
  color: $color-danger;
  margin-top: 8rpx;
}

// ─── 价格显示 ───
.price-display {
  display: flex;
  align-items: baseline;
  gap: 12rpx;
}

.price-value {
  font-size: $font-size-lg;
  font-weight: 700;
  color: $text-primary;
}

.price-note {
  font-size: 20rpx;
  color: $text-hint;
}

// ─── 金额 + 费用 ───
.amount-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16rpx;
}

.amount-label {
  font-size: $font-size-sm;
  color: $text-hint;
}

.amount-value {
  font-size: $font-size-lg;
  font-weight: 700;
  color: $text-primary;
}

.fee-breakdown {
  background: rgba(0, 0, 0, 0.02);
  border-radius: 8rpx;
  padding: 16rpx 20rpx;
}

.fee-row {
  display: flex;
  justify-content: space-between;
  padding: 6rpx 0;
}

.fee-row.total {
  border-top: 1rpx solid $border-color;
  margin-top: 8rpx;
  padding-top: 14rpx;
}

.fee-name {
  font-size: $font-size-sm;
  color: $text-secondary;
}

.fee-val {
  font-size: $font-size-sm;
  color: $text-primary;
  font-weight: 600;
}

// ─── 资金行 ───
.balance-row {
  display: flex;
  justify-content: space-between;
}

.balance-item {
  display: flex;
  flex-direction: column;
  gap: 6rpx;
}

.balance-label {
  font-size: 20rpx;
  color: $text-hint;
}

.balance-value {
  font-size: $font-size-base;
  font-weight: 700;
  color: $text-primary;

  &.danger {
    color: $color-danger;
  }
}

// ─── 警告 ───
.warn-box {
  background: rgba(244, 67, 54, 0.08);
  border-radius: 8rpx;
  padding: 16rpx 20rpx;
  margin-bottom: 20rpx;
}

.warn-text {
  font-size: $font-size-sm;
  color: $color-danger;
  line-height: 1.5;
}

// ─── 规则提示 ───
.rule-box {
  background: rgba(74, 144, 226, 0.06);
  border-radius: 8rpx;
  padding: 16rpx 20rpx;
  margin-bottom: 28rpx;
}

.rule-title {
  font-size: $font-size-sm;
  font-weight: 600;
  color: $text-primary;
  margin-bottom: 10rpx;
}

.rule-item {
  font-size: 20rpx;
  color: $text-secondary;
  line-height: 1.7;
}

// ─── 确认按钮 ───
.confirm-btn {
  width: 100%;
  padding: 24rpx 0;
  border-radius: 12rpx;
  font-size: $font-size-base;
  font-weight: 700;
  color: #fff;
  border: none;
  transition: opacity 0.2s;

  &.buy {
    background: linear-gradient(135deg, #EF5350, #E53935);
  }
  &.sell {
    background: linear-gradient(135deg, #26A69A, #00897B);
  }

  &:disabled {
    opacity: 0.5;
  }

  &::after { border: none; }
}
</style>
