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
      <button class="btn-primary" @click="handleAddWatchlist">
        <text>{{ isInWatchlist ? '已加入自选' : '加入自选' }}</text>
      </button>
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
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import KlineChart from '@/components/market/KlineChart.vue'
import { fetchQuote, fetchKline, type QuoteSnapshot, type KlinePoint } from '@/api/market'
import { trackPageView } from '@/utils/tracker'

const code = ref('')
const quote = ref<QuoteSnapshot | null>(null)
const klinePoints = ref<KlinePoint[]>([])
const period = ref<'day' | 'week' | 'month'>('day')
const loading = ref(true)
const klineLoading = ref(false)
const error = ref('')
const isInWatchlist = ref(false)

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
  code.value = query.code || ''
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
    const data = await fetchKline({ code: code.value, period: period.value, count: 200 })
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

  .btn-primary {
    width: 100%;
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

/* 免责声明 */
.disclaimer-wrapper {
  margin-top: auto;
}
</style>
