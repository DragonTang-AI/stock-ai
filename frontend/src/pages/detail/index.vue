<template>
  <view class="detail-page">
    <!-- 加载中 -->
    <view v-if="loading" class="loading-view">
      <text>加载中...</text>
    </view>

    <!-- 行情头部 -->
    <view v-else-if="quote" class="quote-header">
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

    <!-- 周期切换 -->
    <view v-if="quote" class="period-bar">
      <view
        v-for="p in periods"
        :key="p.value"
        class="period-item"
        :class="{ active: period === p.value }"
        @click="switchPeriod(p.value)"
      >
        <text>{{ p.label }}</text>
      </view>
    </view>

    <!-- K线图 -->
    <view v-if="quote" class="chart-area">
      <KlineChart :points="klinePoints" :loading="klineLoading" :period="period" />
    </view>

    <!-- 操作按钮 -->
    <view v-if="quote" class="action-bar">
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
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import KlineChart from '@/components/market/KlineChart.vue'
import { fetchQuote, fetchKline, type QuoteSnapshot, type KlinePoint } from '@/api/market'

const code = ref('')
const quote = ref<QuoteSnapshot | null>(null)
const klinePoints = ref<KlinePoint[]>([])
const period = ref<'day' | 'week' | 'month'>('day')
const loading = ref(true)
const klineLoading = ref(false)
const error = ref('')
const isInWatchlist = ref(false)

const periods = [
  { label: '日K', value: 'day' as const },
  { label: '周K', value: 'week' as const },
  { label: '月K', value: 'month' as const },
]

const changeClass = computed(() => {
  if (!quote.value) return ''
  return quote.value.change >= 0 ? 'up' : 'down'
})

onMounted(() => {
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
    color: #EF5350;
  }

  &.down {
    background: rgba(38, 166, 154, 0.1);
    color: #26A69A;
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

  &.up { color: #EF5350; }
  &.down { color: #26A69A; }
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

// ---- 操作栏 ----
.action-bar {
  padding: 24rpx 32rpx;

  .btn-primary {
    width: 100%;
    padding: 24rpx;
    font-size: $font-size-base;
    color: #FFFFFF;
    background: $color-primary;
    border-radius: 12rpx;
    border: none;
    text-align: center;

    &::after { border: none; }
  }
}
</style>
