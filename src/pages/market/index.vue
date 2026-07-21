<template>
  <view class="market-page">
    <LoadingSkeleton v-if="loading" scene="list" :rows="5" />
    <ErrorPage v-else-if="error" :message="error" @retry="fetchMarketData" />

    <view v-else class="market-content">
      <!-- ========== 大盘指数 Hero ========== -->
      <view class="index-hero">
        <scroll-view scroll-x class="index-scroll" :show-scrollbar="false">
          <view class="index-row">
            <view
              v-for="item in indices"
              :key="item.code"
              class="index-card"
              @click="goDetail(item.code)"
            >
              <text class="index-name">{{ item.name }}</text>
              <text class="index-price">{{ item.price }}</text>
              <view class="index-change-row">
                <text class="index-change-amount" :class="item.change >= 0 ? 'up' : 'down'">
                  {{ item.change >= 0 ? '+' : '' }}{{ item.changePct }}%
                </text>
              </view>
            </view>
          </view>
        </scroll-view>
      </view>

      <!-- ========== 市场脉动 ========== -->
      <view class="pulse-bar">
        <view class="pulse-chip">
          <text class="pulse-label">上涨</text>
          <text class="pulse-value up">{{ pulse.up }}</text>
        </view>
        <view class="pulse-chip">
          <text class="pulse-label">下跌</text>
          <text class="pulse-value down">{{ pulse.down }}</text>
        </view>
        <view class="pulse-chip">
          <text class="pulse-label">持平</text>
          <text class="pulse-value flat">{{ pulse.flat }}</text>
        </view>
        <view class="pulse-chip">
          <text class="pulse-label">总成交</text>
          <text class="pulse-value vol">{{ pulse.volume }}</text>
        </view>
      </view>

      <!-- ========== 热门股票（按成交额） ========== -->
      <view class="section">
        <view class="section-head">
          <text class="section-title">热门股票</text>
          <text class="section-count">按成交额</text>
        </view>
        <view class="stock-list">
          <view
            v-for="(stock, idx) in hotStocks"
            :key="stock.code"
            class="stock-row"
            hover-class="stock-row--hover"
            @click="goDetail(stock.code)"
          >
            <text class="stock-rank" :class="idx < 3 ? 'rank-hot' : ''">{{ idx + 1 }}</text>
            <view class="stock-info">
              <text class="stock-name">{{ stock.name }}</text>
              <text class="stock-code">{{ stock.code }}</text>
            </view>
            <view class="stock-data">
              <text class="stock-price">{{ stock.price }}</text>
              <view class="change-bar-wrap">
                <view
                  class="change-bar-fill"
                  :class="stock.change >= 0 ? 'up' : 'down'"
                  :style="{ width: Math.min(Math.abs(stock.change) * 12, 100) + '%' }"
                />
                <text class="stock-change" :class="stock.change >= 0 ? 'up' : 'down'">
                  {{ stock.change >= 0 ? '+' : '' }}{{ stock.change }}%
                </text>
              </view>
            </view>
          </view>
        </view>
      </view>

      <!-- ========== 涨跌榜 Tab（按真实涨幅排序） ========== -->
      <view class="section">
        <view class="section-head">
          <text class="section-title">涨跌榜</text>
          <text class="section-count">全市场</text>
        </view>
        <view class="tab-bar">
          <view
            class="tab-item"
            :class="{ active: rankTab === 'gainers' }"
            @click="switchTab('gainers')"
          >
            <text>涨幅榜</text>
          </view>
          <view
            class="tab-item"
            :class="{ active: rankTab === 'losers' }"
            @click="switchTab('losers')"
          >
            <text>跌幅榜</text>
          </view>
        </view>
        <view v-if="rankLoading" class="rank-loading">
          <text>加载中...</text>
        </view>
        <view v-else class="rank-list">
          <view
            v-for="(item, idx) in rankList"
            :key="item.code"
            class="rank-row"
            hover-class="rank-row--hover"
            @click="goDetail(item.code)"
          >
            <text class="rank-idx" :class="rankTab === 'gainers' ? 'up' : 'down'">{{ idx + 1 }}</text>
            <view class="rank-info">
              <text class="rank-name">{{ item.name }}</text>
              <text class="rank-code">{{ item.code }}</text>
            </view>
            <text class="rank-price">{{ formatPrice(item.price) }}</text>
            <text class="rank-change" :class="item.change_pct >= 0 ? 'up' : 'down'">
              {{ item.change_pct >= 0 ? '+' : '' }}{{ item.change_pct.toFixed(2) }}%
            </text>
          </view>
        </view>
      </view>

      <EmptyState v-if="!loading && hotStocks.length === 0" message="暂无行情数据" />
    </view>

    <Disclaimer />
  </view>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import LoadingSkeleton from '@/components/common/LoadingSkeleton.vue'
import ErrorPage from '@/components/common/ErrorPage.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import Disclaimer from '@/components/compliance/Disclaimer.vue'
import { fetchQuotes, fetchIndices, fetchRanking, type RankItem } from '@/api/market'

interface StockItem {
  code: string
  name: string
  price: string
  change: number
  changePct?: string
}

const loading = ref(true)
const error = ref('')
const indices = ref<StockItem[]>([])
const hotStocks = ref<StockItem[]>([])

const rankTab = ref<'gainers' | 'losers'>('gainers')
const rankLoading = ref(false)
const gainers = ref<RankItem[]>([])
const losers = ref<RankItem[]>([])

// 涨跌榜展示数据
const rankList = computed(() => (rankTab.value === 'gainers' ? gainers.value : losers.value))

// 市场脉动（基于全市场排行数据）
const pulse = computed(() => {
  const all = [...gainers.value, ...losers.value]
  // 从两个榜各取10只，得到20只（涨跌两端）
  // 实际市场脉动需要全市场数据，这里用涨跌榜的统计作为参考
  const up = gainers.value.length
  const down = losers.value.length
  // 总成交 = hot榜前 10 的成交额合计
  const totalAmount = hotStocks.value.reduce((sum, s) => sum + (s.amount || 0), 0)
  return {
    up,
    down,
    flat: 0,
    volume: formatAmount(totalAmount),
  }
})

// 缓存上一次拉取时间，避免重复请求
let gainersFetchedAt = 0
let losersFetchedAt = 0
const CACHE_TTL = 30_000  // 30s 缓存

// ─────────── 数据拉取 ───────────
async function fetchMarketData() {
  loading.value = true
  error.value = ''
  try {
    // 大盘指数
    try {
      const indexData = await fetchIndices()
      if (indexData.length) {
        indices.value = indexData.map((d: any) => ({
          code: d.symbol,
          name: d.name,
          price: typeof d.price === 'number' ? d.price.toFixed(2) : '--',
          change: d.change_pct != null ? Number(d.change_pct.toFixed(2)) : 0,
          changePct: d.change_pct != null ? d.change_pct.toFixed(2) : '0.00',
        }))
      } else {
        indices.value = fallbackIndices()
      }
    } catch {
      indices.value = fallbackIndices()
    }

    // 热门股票（按成交额） + 涨跌榜（按真实涨幅排序）
    // 三路并发
    const [quotes, gainerList, loserList] = await Promise.all([
      fetchQuotes().catch(() => []),
      fetchRanking('gainers', 20).catch(() => []),
      fetchRanking('losers', 20).catch(() => []),
    ])

    // 热门股票：优先用 hot 榜，无则回退到 quotes
    let hotData: RankItem[] = []
    try {
      hotData = await fetchRanking('hot', 20)
    } catch {
      hotData = []
    }

    hotStocks.value = (hotData.length > 0 ? hotData : (quotes as any[]).slice(0, 20)).map((s: any) => ({
      code: s.code || s.symbol,
      name: s.name,
      price: typeof s.price === 'number' ? s.price.toFixed(2) : '--',
      change: Number((s.change_pct ?? s.change ?? 0).toFixed(2)),
      amount: s.amount || 0,
    }))

    gainers.value = gainerList
    losers.value = loserList
    gainersFetchedAt = losersFetchedAt = Date.now()
  } catch (e: any) {
    error.value = e?.message || '加载失败'
  } finally {
    loading.value = false
  }
}

async function switchTab(tab: 'gainers' | 'losers') {
  rankTab.value = tab
  // 简单缓存策略：30s 内复用
  const now = Date.now()
  if (tab === 'gainers' && now - gainersFetchedAt > CACHE_TTL) {
    await refreshRanking('gainers')
  } else if (tab === 'losers' && now - losersFetchedAt > CACHE_TTL) {
    await refreshRanking('losers')
  }
}

async function refreshRanking(type: 'gainers' | 'losers') {
  rankLoading.value = true
  try {
    const data = await fetchRanking(type, 20)
    if (type === 'gainers') {
      gainers.value = data
      gainersFetchedAt = Date.now()
    } else {
      losers.value = data
      losersFetchedAt = Date.now()
    }
  } catch {
    // 静默失败，保留旧数据
  } finally {
    rankLoading.value = false
  }
}

// ─────────── 工具函数 ───────────
function formatPrice(p: number): string {
  if (typeof p !== 'number') return '--'
  return p.toFixed(2)
}

function formatAmount(amount: number): string {
  if (amount >= 1e8) return (amount / 1e8).toFixed(0) + '亿'
  if (amount >= 1e4) return (amount / 1e4).toFixed(0) + '万'
  return amount.toFixed(0)
}

function fallbackIndices(): StockItem[] {
  return [
    { code: '000001', name: '上证指数', price: '--', change: 0, changePct: '0.00' },
    { code: '399001', name: '深证成指', price: '--', change: 0, changePct: '0.00' },
    { code: '399006', name: '创业板指', price: '--', change: 0, changePct: '0.00' },
  ]
}

function goDetail(code: string) {
  uni.navigateTo({ url: `/pages/detail/index?code=${code}` })
}

onMounted(() => {
  fetchMarketData()
})
</script>

<style scoped lang="scss">
.market-page {
  min-height: 100vh;
  background: var(--bg-page, #f5f5f7);
}

.market-content {
  padding-bottom: 24rpx;
}

/* ========== 大盘指数 Hero ========== */
.index-hero {
  margin: 24rpx;
}

.index-scroll {
  white-space: nowrap;
}

.index-row {
  display: inline-flex;
  gap: 20rpx;
  padding-right: 24rpx;
}

.index-card {
  display: inline-flex;
  flex-direction: column;
  align-items: flex-start;
  min-width: 200rpx;
  padding: 28rpx 28rpx 24rpx;
  background: #fff;
  border-radius: 20rpx;
  box-shadow: 0 4rpx 16rpx rgba(0, 0, 0, 0.04);
  transition: transform 0.15s ease;
}

.index-card:active {
  transform: scale(0.97);
}

.index-name {
  font-size: 24rpx;
  color: var(--text-hint, #999);
  margin-bottom: 12rpx;
}

.index-price {
  font-size: 44rpx;
  font-weight: 800;
  color: var(--text-primary, #1f1f1f);
  letter-spacing: -1rpx;
  margin-bottom: 8rpx;
}

.index-change-row {
  display: flex;
  align-items: center;
}

.index-change-amount {
  font-size: 26rpx;
  font-weight: 600;
  padding: 4rpx 16rpx;
  border-radius: 8rpx;

  &.up {
    color: var(--color-up, #e25c5c);
    background: rgba(226, 92, 92, 0.08);
  }
  &.down {
    color: var(--color-down, #34c759);
    background: rgba(52, 199, 89, 0.08);
  }
}

/* ========== 市场脉动 ========== */
.pulse-bar {
  display: flex;
  margin: 0 24rpx 24rpx;
  gap: 16rpx;
}

.pulse-chip {
  flex: 1;
  text-align: center;
  background: #fff;
  border-radius: 16rpx;
  padding: 20rpx 0;
  box-shadow: 0 2rpx 8rpx rgba(0, 0, 0, 0.03);
}

.pulse-label {
  display: block;
  font-size: 22rpx;
  color: var(--text-hint, #999);
  margin-bottom: 6rpx;
}

.pulse-value {
  display: block;
  font-size: 36rpx;
  font-weight: 800;

  &.up   { color: var(--color-up, #e25c5c); }
  &.down { color: var(--color-down, #34c759); }
  &.flat { color: var(--text-hint, #999); }
  &.vol  { color: var(--color-primary, #4a90e2); }
}

/* ========== 通用 Section ========== */
.section {
  background: #fff;
  margin: 0 24rpx 24rpx;
  border-radius: 20rpx;
  padding: 28rpx;
  box-shadow: 0 2rpx 12rpx rgba(0, 0, 0, 0.03);
}

.section-head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 20rpx;
}

.section-title {
  font-size: 32rpx;
  font-weight: 700;
  color: var(--text-primary, #1f1f1f);
}

.section-count {
  font-size: 24rpx;
  color: var(--text-hint, #999);
}

/* ========== 热门股票列表 ========== */
.stock-list {
  display: flex;
  flex-direction: column;
}

.stock-row {
  display: flex;
  align-items: center;
  padding: 22rpx 0;
  border-bottom: 1rpx solid var(--border-color, #f0f0f0);
  transition: background 0.12s ease;

  &:last-child { border-bottom: none; }
}

.stock-row--hover {
  background: var(--bg-hover, rgba(0, 0, 0, 0.03));
}

.stock-rank {
  width: 44rpx;
  font-size: 26rpx;
  font-weight: 600;
  color: var(--text-hint, #999);
  text-align: center;

  &.rank-hot {
    color: var(--color-primary, #4a90e2);
    font-weight: 700;
  }
}

.stock-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  margin-left: 12rpx;
}

.stock-name {
  font-size: 30rpx;
  font-weight: 600;
  color: var(--text-primary, #1f1f1f);
}

.stock-code {
  font-size: 22rpx;
  color: var(--text-hint, #999);
  margin-top: 4rpx;
}

.stock-data {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  min-width: 160rpx;
}

.stock-price {
  font-size: 30rpx;
  font-weight: 700;
  color: var(--text-primary, #1f1f1f);
}

.change-bar-wrap {
  position: relative;
  height: 36rpx;
  min-width: 120rpx;
  margin-top: 6rpx;
  border-radius: 6rpx;
  overflow: hidden;
  background: var(--bg-page, #f5f5f7);
}

.change-bar-fill {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  border-radius: 6rpx;
  opacity: 0.18;
  transition: width 0.4s ease;

  &.up   { background: var(--color-up, #e25c5c); }
  &.down { background: var(--color-down, #34c759); }
}

.stock-change {
  position: absolute;
  right: 10rpx;
  top: 50%;
  transform: translateY(-50%);
  font-size: 24rpx;
  font-weight: 700;
  z-index: 1;

  &.up   { color: var(--color-up, #e25c5c); }
  &.down { color: var(--color-down, #34c759); }
}

/* ========== 涨跌榜 Tab ========== */
.tab-bar {
  display: flex;
  gap: 12rpx;
  margin-bottom: 16rpx;
}

.tab-item {
  flex: 1;
  text-align: center;
  padding: 14rpx 0;
  font-size: 26rpx;
  font-weight: 500;
  color: var(--text-secondary, #666);
  background: var(--bg-page, #f5f5f7);
  border-radius: 12rpx;
  transition: all 0.2s ease;

  &.active {
    color: #fff;
    background: var(--color-primary, #4a90e2);
    font-weight: 600;
  }
}

.rank-loading {
  text-align: center;
  padding: 40rpx 0;
  color: var(--text-hint, #999);
  font-size: 26rpx;
}

.rank-list {
  display: flex;
  flex-direction: column;
  gap: 8rpx;
}

.rank-row {
  display: flex;
  align-items: center;
  padding: 16rpx 12rpx;
  border-radius: 12rpx;
  transition: background 0.12s ease;
}

.rank-row--hover {
  background: var(--bg-hover, rgba(0, 0, 0, 0.03));
}

.rank-idx {
  width: 44rpx;
  font-size: 28rpx;
  font-weight: 800;
  text-align: center;

  &.up   { color: var(--color-up, #e25c5c); }
  &.down { color: var(--color-down, #34c759); }
}

.rank-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  margin-left: 12rpx;
}

.rank-name {
  font-size: 28rpx;
  font-weight: 600;
  color: var(--text-primary, #1f1f1f);
}

.rank-code {
  font-size: 22rpx;
  color: var(--text-hint, #999);
  margin-top: 2rpx;
}

.rank-price {
  font-size: 28rpx;
  font-weight: 600;
  color: var(--text-primary, #1f1f1f);
  min-width: 130rpx;
  text-align: right;
  margin-right: 20rpx;
}

.rank-change {
  font-size: 28rpx;
  font-weight: 700;
  min-width: 120rpx;
  text-align: right;

  &.up   { color: var(--color-up, #e25c5c); }
  &.down { color: var(--color-down, #34c759); }
}
</style>
