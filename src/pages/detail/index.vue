<template>
  <view class="detail-page">
    <!-- 加载中 -->
    <view v-if="loading" class="loading-view">
      <text>加载中...</text>
    </view>

    <!-- 行情头部 -->
    <view v-else-if="quote && !isFullscreen" class="quote-header">
      <view class="header-top">
        <text class="stock-name">{{ quote.name }}</text>
        <text class="stock-code">{{ quote.code }}</text>
      </view>
      <view class="header-price">
        <text class="price-value">{{ formatPrice(quote.price) }}</text>
        <view class="price-change" :class="changeClass">
          <text class="change-value">{{ formatChange(quote.change) }}</text>
          <text class="change-pct">{{ formatChangePct(quote.change_pct) }}</text>
        </view>
      </view>
      <view class="header-grid">
        <view class="grid-cell">
          <text class="cell-label">今开</text>
          <text class="cell-value">{{ formatPrice(quote.open) }}</text>
        </view>
        <view class="grid-cell">
          <text class="cell-label">最高</text>
          <text class="cell-value up">{{ formatPrice(quote.high) }}</text>
        </view>
        <view class="grid-cell">
          <text class="cell-label">最低</text>
          <text class="cell-value down">{{ formatPrice(quote.low) }}</text>
        </view>
        <view class="grid-cell">
          <text class="cell-label">昨收</text>
          <text class="cell-value">{{ formatPrice(quote.pre_close) }}</text>
        </view>
        <view class="grid-cell">
          <text class="cell-label">成交量</text>
          <text class="cell-value">{{ formatVolume(quote.volume) }}</text>
        </view>
        <view class="grid-cell">
          <text class="cell-label">成交额</text>
          <text class="cell-value">{{ formatAmount(quote.amount) }}</text>
        </view>
        <view class="grid-cell">
          <text class="cell-label">换手率</text>
          <text class="cell-value">{{ formatPct(quote.turnover) }}</text>
        </view>
        <view class="grid-cell">
          <text class="cell-label">振幅</text>
          <text class="cell-value">{{ formatPct(quote.high_low) }}</text>
        </view>
      </view>
    </view>

    <!-- 周期切换 + 全屏按钮 -->
    <view v-if="quote && !isFullscreen" class="period-bar">
      <view
        v-for="p in periods"
        :key="p.value"
        class="period-item"
        :class="{ active: period === p.value }"
        @click="switchPeriod(p.value)"
      >
        <text>{{ p.label }}</text>
      </view>
      <view class="fullscreen-toggle" @click="toggleFullscreen">
        <text>{{ isLandscape ? '退出全屏' : '全屏' }}</text>
      </view>
    </view>

    <!-- K线图（普通模式） -->
    <view v-if="quote && !isFullscreen" class="chart-area">
      <KlineChart :points="klinePoints" :loading="klineLoading" :period="period" />
    </view>

    <!-- K线图（全屏横屏模式） -->
    <view v-if="isFullscreen" class="fullscreen-chart safe-fullscreen">
      <view class="fullscreen-topbar">
        <text class="fs-stock-name">{{ quote?.name }} {{ quote?.code }}</text>
        <view class="fs-price-info">
          <text class="fs-price">{{ formatPrice(quote?.price ?? 0) }}</text>
          <text class="fs-change" :class="changeClass">{{ formatChangePct(quote?.change_pct ?? 0) }}</text>
        </view>
        <view class="fs-periods">
          <text
            v-for="p in periods"
            :key="p.value"
            class="fs-period"
            :class="{ active: period === p.value }"
            @click="switchPeriod(p.value)"
          >{{ p.label }}</text>
        </view>
        <view class="fs-close" @click="toggleFullscreen">
          <text>退出</text>
        </view>
      </view>
      <view class="fullscreen-chart-body">
        <KlineChart :points="klinePoints" :loading="klineLoading" :period="period" />
      </view>
    </view>

    <!-- 操作按钮 -->
    <view v-if="quote && !isFullscreen" class="action-bar">
      <button class="btn-secondary" @click="handleAddWatchlist">
        <text>{{ isInWatchlist ? '已加入自选' : '加入自选' }}</text>
      </button>
      <button class="btn-primary" @click="showTradeModal = true">
        <text>快速买入</text>
      </button>
    </view>

    <!-- 快速买入弹窗 -->
    <view v-if="showTradeModal" class="modal-overlay" @click="showTradeModal = false">
      <view class="trade-modal" @click.stop>
        <view class="modal-header">
          <text class="modal-title">快速下单 - {{ quote?.name }}</text>
          <text class="modal-close" @click="showTradeModal = false">✕</text>
        </view>
        <view class="modal-body">
          <!-- 方向切换 -->
          <view class="trade-section">
            <view class="side-tabs">
              <view class="side-tab" :class="{ active: tradeSide === 'buy' }" @click="tradeSide = 'buy'">买入</view>
              <view class="side-tab" :class="{ active: tradeSide === 'sell' }" @click="tradeSide = 'sell'">卖出</view>
            </view>
          </view>

          <!-- 价格输入（带 +/- 步进） -->
          <view class="trade-section">
            <text class="section-label">限价</text>
            <view class="stepper-row">
              <view class="stepper-btn" @click="adjustPrice(-0.01)">−</view>
              <input v-model="tradePrice" class="stepper-input" type="digit" placeholder="输入价格" />
              <view class="stepper-btn" @click="adjustPrice(0.01)">+</view>
            </view>
            <view class="price-hint" v-if="quote?.price">
              <text class="hint-text">涨停 {{ formatPrice((quote?.price || 0) * 1.1) }}</text>
              <text class="hint-text down">跌停 {{ formatPrice((quote?.price || 0) * 0.9) }}</text>
            </view>
          </view>

          <!-- 数量输入（带 +/- 步进） -->
          <view class="trade-section">
            <text class="section-label">数量（股）</text>
            <view class="stepper-row">
              <view class="stepper-btn" @click="adjustQty(-1)">−</view>
              <input v-model="tradeQty" class="stepper-input" type="digit" placeholder="100" />
              <view class="stepper-btn" @click="adjustQty(1)">+</view>
            </view>
            <view class="qty-actions">
              <view class="qty-info">
                <text class="qty-info-text" v-if="maxBuyQty > 0">可买 {{ maxBuyQty }} 股</text>
                <text class="qty-info-text dim" v-else>可买 0 股</text>
                <text class="qty-info-text cash">可用 {{ accountCash.toFixed(2) }} 元</text>
              </view>
              <view class="qty-shortcuts">
                <view class="shortcut-btn" @click="fillQuarter()">1/4</view>
                <view class="shortcut-btn" @click="fillThird()">1/3</view>
                <view class="shortcut-btn" @click="fillHalf()">1/2</view>
                <view class="shortcut-btn primary" @click="fillFullPosition()">全仓</view>
              </view>
            </view>
          </view>

          <!-- 预估金额 -->
          <view class="estimate-row" v-if="estimatedAmount !== '0.00'">
            <text class="estimate-label">预估金额</text>
            <text class="estimate-value">{{ estimatedAmount }} 元</text>
          </view>

          <view v-if="tradeError" class="trade-error">{{ tradeError }}</view>
          <button class="btn-confirm" :disabled="tradeSubmitting" @click="handlePlaceOrder">
            {{ tradeSide === 'buy' ? '买入' : '卖出' }}
          </button>
        </view>
      </view>
    </view>

    <!-- 错误状态 -->
    <view v-if="error" class="error-view">
      <text class="error-text">{{ error }}</text>
      <button class="btn-retry" @click="loadData">重试</button>
    </view>
  </view>
  <Disclaimer />
</template>

<script setup lang="ts">
import Disclaimer from '@/components/compliance/Disclaimer.vue'
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import KlineChart from '@/components/market/KlineChart.vue'
import { fetchQuote, fetchKline, type QuoteSnapshot, type KlinePoint } from '@/api/market'
import { placeOrder, fetchAccount, type OrderSide } from '@/api/trading'
import { trackPageView } from '@/utils/tracker'

const code = ref('')
const quote = ref<QuoteSnapshot | null>(null)
const klinePoints = ref<KlinePoint[]>([])
const period = ref<'day' | 'week' | 'month'>('day')
const loading = ref(true)
const klineLoading = ref(false)
const error = ref('')
const isInWatchlist = ref(false)

// 快速交易弹窗
const showTradeModal = ref(false)
const tradeSide = ref<OrderSide>('buy')
const tradePrice = ref('')
const tradeQty = ref('')
const tradeError = ref('')
const tradeSubmitting = ref(false)

// 账户可用资金
const accountCash = ref(0)
const loadingAccount = ref(false)

// 最大可买股数
const maxBuyQty = computed(() => {
  const price = parseFloat(tradePrice.value)
  if (!price || price <= 0 || accountCash.value <= 0) return 0
  return Math.floor(accountCash.value / price / 100) * 100
})

// 横屏全屏模式
const isFullscreen = ref(false)
const isLandscape = ref(false)

const periods = [
  { label: '日K', value: 'day' as const },
  { label: '周K', value: 'week' as const },
  { label: '月K', value: 'month' as const },
]

const changeClass = computed(() => {
  if (!quote.value) return ''
  return quote.value.change >= 0 ? 'up' : 'down'
})

// 检测屏幕方向
function checkOrientation() {
  // #ifdef H5
  isLandscape.value = window.innerWidth > window.innerHeight
  // #endif
  // #ifdef APP-PLUS
  isLandscape.value = window.innerWidth > window.innerHeight
  // #endif
}

function toggleFullscreen() {
  isFullscreen.value = !isFullscreen.value
  // #ifdef APP-PLUS
  if (isFullscreen.value) {
    plus.screen.lockOrientation('landscape')
  } else {
    plus.screen.lockOrientation('portrait-primary')
  }
  // #endif
}

onMounted(() => {
  checkOrientation()
  // 监听屏幕旋转
  // #ifdef H5
  window.addEventListener('orientationchange', checkOrientation)
  window.addEventListener('resize', checkOrientation)
  // #endif
  // #ifdef APP-PLUS
  window.addEventListener('orientationchange', checkOrientation)
  window.addEventListener('resize', checkOrientation)
  // #endif

  // 从路由参数获取股票代码
  const pages = getCurrentPages()
  const currentPage = pages[pages.length - 1] as any
  const query = currentPage?.$page?.options || currentPage?.options || {}
  code.value = query.symbol || query.code || ''
  if (code.value) {
    loadData()
  } else {
    error.value = '缺少股票代码参数'
    loading.value = false
  }
})

onUnmounted(() => {
  // 清理监听
  // #ifdef H5
  window.removeEventListener('orientationchange', checkOrientation)
  window.removeEventListener('resize', checkOrientation)
  // #endif
  // #ifdef APP-PLUS
  window.removeEventListener('orientationchange', checkOrientation)
  window.removeEventListener('resize', checkOrientation)
  // 退出全屏时恢复竖屏
  plus.screen.lockOrientation('portrait-primary')
  // #endif
})

async function loadData() {
  loading.value = true
  error.value = ''
  try {
    const [quoteData] = await Promise.all([
      fetchQuote(code.value),
    ])
    quote.value = quoteData
    await loadKline()
  } catch (e: any) {
    error.value = e?.message || '加载失败'
  } finally {
    loading.value = false
  }
}

async function loadKline() {
  klineLoading.value = true
  try {
    const data = await fetchKline({ symbol: code.value, period: period.value, count: 200 })
    klinePoints.value = data.points
  } catch {
    uni.showToast({ title: 'K线加载失败', icon: 'none' })
  } finally {
    klineLoading.value = false
  }
}

function switchPeriod(p: 'day' | 'week' | 'month') {
  period.value = p
  loadKline()
}

function handleAddWatchlist() {
  isInWatchlist.value = !isInWatchlist.value
  uni.showToast({
    title: isInWatchlist.value ? '已加入自选' : '已取消自选',
    icon: 'success',
  })
}

// ---- 弹窗打开时初始化 ----
watch(showTradeModal, async (open) => {
  if (!open) return
  if (quote.value?.price) {
    tradePrice.value = quote.value.price.toFixed(2)
  }
  tradeQty.value = ''
  tradeError.value = ''
  loadingAccount.value = true
  try {
    const account = await fetchAccount()
    accountCash.value = account.cash
  } catch {
    accountCash.value = 0
  } finally {
    loadingAccount.value = false
  }
})

function adjustPrice(delta: number) {
  const current = parseFloat(tradePrice.value) || 0
  const next = Math.max(0.01, current + delta)
  tradePrice.value = next.toFixed(2)
}

function adjustQty(delta: number) {
  const current = parseInt(tradeQty.value) || 0
  const next = Math.max(0, current + delta * 100)
  tradeQty.value = String(next)
}

function fillFullPosition() {
  if (maxBuyQty.value > 0) tradeQty.value = String(maxBuyQty.value)
}

function fillHalf() {
  const qty = Math.floor(maxBuyQty.value / 200) * 100
  tradeQty.value = String(Math.max(100, qty))
}

function fillThird() {
  const qty = Math.floor(maxBuyQty.value / 300) * 100
  tradeQty.value = String(Math.max(100, qty))
}

function fillQuarter() {
  const qty = Math.floor(maxBuyQty.value / 400) * 100
  tradeQty.value = String(Math.max(100, qty))
}

const estimatedAmount = computed(() => {
  const price = parseFloat(tradePrice.value) || 0
  const qty = parseInt(tradeQty.value) || 0
  return (price * qty).toFixed(2)
})

async function handlePlaceOrder() {
  tradeError.value = ''
  const quantity = parseInt(tradeQty.value)
  const price = parseFloat(tradePrice.value)
  if (!quantity || quantity < 100) { tradeError.value = '数量不能少于100股'; return }
  if (quantity % 100 !== 0) { tradeError.value = '数量必须是100的整数倍'; return }
  if (!price || price <= 0) { tradeError.value = '请输入有效价格'; return }
  tradeSubmitting.value = true
  try {
    // action: 小写 'buy'|'sell'，order_type: 大写
    await placeOrder({ symbol: code.value, action: tradeSide.value, order_type: "LIMIT", quantity, price })
    showTradeModal.value = false
    uni.showToast({ title: '下单成功', icon: 'success' })
  } catch (e: any) {
    tradeError.value = e?.message || '下单失败，请重试'
  } finally {
    tradeSubmitting.value = false
  }
}

// ---- 格式化 ----
function formatPrice(v: number): string {
  if (v == null) return '--'
  return v.toFixed(2)
}

function formatChange(v: number): string {
  if (v == null) return '--'
  const sign = v >= 0 ? '+' : ''
  return sign + v.toFixed(2)
}

function formatChangePct(v: number): string {
  if (v == null) return '--'
  const sign = v >= 0 ? '+' : ''
  return sign + v.toFixed(2) + '%'
}

function formatVolume(v: number): string {
  if (v == null) return '--'
  if (v >= 10000) return (v / 10000).toFixed(1) + '万手'
  return v + '手'
}

function formatAmount(v: number): string {
  if (v == null) return '--'
  if (v >= 1e8) return (v / 1e8).toFixed(2) + '亿'
  if (v >= 1e4) return (v / 1e4).toFixed(1) + '万'
  return v.toString()
}

function formatPct(v: number): string {
  if (v == null) return '--'
  return v.toFixed(2) + '%'
}

onShow(() => {
  trackPageView('trade_detail', { code: code.value })
})
</script>

<style lang="scss" scoped>
.detail-page {
  min-height: 100vh;
  background: $bg-page;
  padding-bottom: env(safe-area-inset-bottom);
}

.loading-view {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 200rpx 0;
  font-size: $font-size-base;
  color: $text-hint;
}

.error-view {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 200rpx 0;
}

.error-text {
  font-size: $font-size-base;
  color: $text-secondary;
  margin-bottom: 32rpx;
}

.btn-retry {
  padding: 12rpx 48rpx;
  font-size: $font-size-sm;
  color: $color-primary;
  background: rgba(74, 144, 226, 0.1);
  border-radius: 8rpx;
  border: none;

  &::after { border: none; }
}

// ---- 行情头部 ----
.quote-header {
  background: $bg-card;
  padding: 24rpx 32rpx;
  border-bottom: 1rpx solid $border-color;
}

.header-top {
  display: flex;
  align-items: baseline;
  gap: 12rpx;
  margin-bottom: 16rpx;
}

.stock-name {
  font-size: $font-size-xl;
  font-weight: 700;
  color: $text-primary;
}

.stock-code {
  font-size: $font-size-sm;
  color: $text-hint;
}

.header-price {
  display: flex;
  align-items: baseline;
  gap: 16rpx;
  margin-bottom: 24rpx;
}

.price-value {
  font-size: 56rpx;
  font-weight: 700;
  color: $text-primary;
  line-height: 1;
}

.price-change {
  display: flex;
  gap: 8rpx;
  padding: 4rpx 12rpx;
  border-radius: 6rpx;

  &.up {
    background: rgba(239, 83, 80, 0.1);
    color: var(--color-up, #EF5350);
  }

  &.down {
    background: rgba(38, 166, 154, 0.1);
    color: var(--color-down, #26A69A);
  }
}

.change-value,
.change-pct {
  font-size: $font-size-base;
  font-weight: 600;
}

.header-grid {
  display: flex;
  flex-wrap: wrap;
}

.grid-cell {
  width: 25%;
  padding: 12rpx 0;
  display: flex;
  flex-direction: column;
  gap: 4rpx;
}

.cell-label {
  font-size: $font-size-xs;
  color: $text-hint;
}

.cell-value {
  font-size: $font-size-sm;
  color: $text-primary;
  font-weight: 500;

  &.up { color: var(--color-up, #EF5350); }
  &.down { color: var(--color-down, #26A69A); }
}

// ---- 周期切换 ----
.period-bar {
  display: flex;
  background: $bg-card;
  padding: 0 32rpx;
  margin-top: 16rpx;
  border-bottom: 1rpx solid $border-color;
}

.period-item {
  padding: 20rpx 32rpx;
  font-size: $font-size-sm;
  color: $text-secondary;
  border-bottom: 4rpx solid transparent;
  cursor: pointer;

  &.active {
    color: $color-primary;
    border-bottom-color: $color-primary;
    font-weight: 600;
  }
}

// ---- 图表 ----
.chart-area {
  background: $bg-card;
  padding: 16rpx 0;
}

// ---- 全屏按钮 ----
.fullscreen-toggle {
  margin-left: auto;
  padding: 20rpx 24rpx;
  font-size: $font-size-sm;
  color: $color-primary;
  font-weight: 500;
  cursor: pointer;
  flex-shrink: 0;
  border-left: 1rpx solid $border-color;
}

// ---- 全屏横屏 K线 ----
.fullscreen-chart {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 999;
  background: $bg-card;
  display: flex;
  flex-direction: column;
}

.fullscreen-topbar {
  display: flex;
  align-items: center;
  padding: 12rpx 24rpx;
  background: $bg-primary;
  color: $text-inverse;
  flex-shrink: 0;
  gap: 16rpx;
  min-height: 88rpx;
}

.fs-stock-name {
  font-size: $font-size-base;
  font-weight: 600;
  flex-shrink: 0;
}

.fs-price-info {
  display: flex;
  align-items: baseline;
  gap: 8rpx;
}

.fs-price {
  font-size: $font-size-lg;
  font-weight: 700;
}

.fs-change {
  font-size: $font-size-sm;
  &.up { color: var(--color-up, #E25C5C); }
  &.down { color: var(--color-down, #34C759); }
}

.fs-periods {
  display: flex;
  gap: 8rpx;
  margin-left: auto;
}

.fs-period {
  padding: 8rpx 20rpx;
  font-size: $font-size-sm;
  color: rgba(255,255,255,0.6);
  border-radius: 6rpx;
  cursor: pointer;

  &.active {
    color: #fff;
    background: rgba(255,255,255,0.15);
    font-weight: 600;
  }
}

.fs-close {
  padding: 8rpx 16rpx;
  font-size: $font-size-sm;
  color: $text-inverse;
  background: rgba(255,255,255,0.15);
  border-radius: 6rpx;
  cursor: pointer;
  flex-shrink: 0;
}

.fullscreen-chart-body {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

// ---- 操作栏 ----
.action-bar {
  padding: 24rpx 32rpx;
  display: flex;
  gap: 16rpx;

  .btn-secondary {
    flex: 1;
    padding: 24rpx;
    font-size: $font-size-base;
    color: $color-primary;
    background: var(--bg-card, #fff);
    border: 2rpx solid $color-primary;
    border-radius: 12rpx;
    text-align: center;

    &::after { border: none; }
  }

  .btn-primary {
    flex: 1;
    padding: 24rpx;
    font-size: $font-size-base;
    color: #fff;
    background: $color-primary;
    border-radius: 12rpx;
    border: none;
    text-align: center;

    &::after { border: none; }
  }
}

// ---- 交易弹窗（增强版） ----
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  z-index: 1000;
  display: flex;
  align-items: flex-end;
  justify-content: center;
}

.trade-modal {
  width: 100%;
  max-width: 500px;
  background: var(--bg-card, #fff);
  border-radius: 24rpx 24rpx 0 0;
  padding-bottom: env(safe-area-inset-bottom);
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 32rpx 32rpx 16rpx;
  border-bottom: 1rpx solid var(--border-color, #eee);
}

.modal-title {
  font-size: 32rpx;
  font-weight: 600;
  color: var(--text-primary, #333);
}

.modal-close {
  font-size: 40rpx;
  color: var(--text-hint, #999);
  padding: 8rpx;
}

.modal-body {
  padding: 20rpx 32rpx 32rpx;
}

// ---- 方向切换 ----
.side-tabs {
  display: flex;
  gap: 16rpx;
  margin-bottom: 20rpx;
}

.side-tab {
  padding: 14rpx 36rpx;
  font-size: 28rpx;
  border-radius: 12rpx;
  border: 2rpx solid var(--border-color, #ddd);
  color: var(--text-secondary, #666);
  text-align: center;
  flex: 1;

  &.active {
    background: $color-primary;
    color: #fff;
    border-color: $color-primary;
  }
}

// ---- 分段 ----
.trade-section {
  margin-bottom: 24rpx;
}

.section-label {
  display: block;
  font-size: 26rpx;
  color: var(--text-hint, #999);
  margin-bottom: 12rpx;
}

// ---- 步进输入行 ----
.stepper-row {
  display: flex;
  align-items: center;
  gap: 12rpx;
}

.stepper-btn {
  width: 72rpx;
  height: 72rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 40rpx;
  font-weight: 500;
  color: #fff;
  background: $color-primary;
  border-radius: 16rpx;
  flex-shrink: 0;
}

.stepper-input {
  flex: 1;
  text-align: center;
  font-size: 36rpx;
  font-weight: 600;
  padding: 16rpx 12rpx;
  border: 2rpx solid var(--border-color, #ddd);
  border-radius: 12rpx;
  background: var(--bg-page, #f5f5f7);
  color: var(--text-primary, #333);
}

// ---- 价格提示 ----
.price-hint {
  display: flex;
  justify-content: space-between;
  margin-top: 10rpx;
}

.hint-text {
  font-size: 22rpx;
  color: #EF5350;

  &.down {
    color: #26A69A;
  }
}

// ---- 数量快捷操作 ----
.qty-actions {
  margin-top: 12rpx;
}

.qty-info {
  display: flex;
  justify-content: space-between;
  margin-bottom: 12rpx;
}

.qty-info-text {
  font-size: 24rpx;
  color: $color-primary;
  font-weight: 500;

  &.dim {
    color: var(--text-hint, #999);
  }

  &.cash {
    color: #EF5350;
  }
}

.qty-shortcuts {
  display: flex;
  gap: 12rpx;
}

.shortcut-btn {
  flex: 1;
  padding: 14rpx 0;
  text-align: center;
  font-size: 24rpx;
  font-weight: 600;
  color: $color-primary;
  background: rgba(74, 144, 226, 0.08);
  border: 1rpx solid rgba(74, 144, 226, 0.2);
  border-radius: 10rpx;

  &.primary {
    color: #fff;
    background: $color-primary;
    border-color: $color-primary;
  }
}

// ---- 预估金额 ----
.estimate-row {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  padding: 20rpx 0;
  border-top: 1rpx solid var(--border-color, #eee);
  border-bottom: 1rpx solid var(--border-color, #eee);
  margin-bottom: 24rpx;
}

.estimate-label {
  font-size: 28rpx;
  color: var(--text-secondary, #666);
}

.estimate-value {
  font-size: 36rpx;
  font-weight: 700;
  color: $color-primary;
}

// ---- 错误 & 按钮 ----
.trade-error {
  color: $color-danger;
  font-size: 24rpx;
  margin-bottom: 16rpx;
  text-align: center;
}

.btn-confirm {
  width: 100%;
  padding: 24rpx;
  font-size: 32rpx;
  color: #fff;
  background: $color-primary;
  border-radius: 12rpx;
  border: none;
  text-align: center;

  &[disabled] {
    opacity: 0.5;
  }

  &::after { border: none; }
}

/* 免责声明 */
.disclaimer-wrapper {
  margin-top: auto;
}
</style>
