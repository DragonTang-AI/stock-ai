<template>
  <view class="candidates-page">
    <!-- 加载中 -->
    <view v-if="loading && items.length === 0" class="state-view">
      <text class="state-text">加载中...</text>
    </view>

    <!-- 错误 -->
    <view v-else-if="error && items.length === 0" class="state-view">
      <text class="state-text error">{{ error }}</text>
      <button class="btn-retry" @click="loadCandidates(true)">重试</button>
    </view>

    <!-- 主内容 -->
    <template v-else>
      <!-- 统计信息 -->
      <view class="stats-bar">
        <text class="stats-text">共 {{ total }} 只候选股票</text>
      </view>

      <!-- 筛选工具栏 -->
      <view class="filter-bar">
        <!-- 评分区间 -->
        <view class="filter-group">
          <text class="filter-label">评分</text>
          <scroll-view scroll-x class="filter-scroll">
            <view class="filter-tags">
              <view
                v-for="range in scoreRanges"
                :key="range.label"
                class="filter-tag"
                :class="{ active: activeScoreRange === range.label }"
                @click="handleScoreRange(range.label)"
              >
                {{ range.label }}
              </view>
            </view>
          </scroll-view>
        </view>

        <!-- 行业 + 排序 -->
        <view class="filter-row">
          <view class="filter-select" @click="handleShowIndustryPicker">
            <text class="filter-select-label">{{ selectedIndustry || '全部行业' }}</text>
            <text class="filter-arrow">&#9662;</text>
          </view>
          <view class="filter-select" @click="handleToggleSort">
            <text class="filter-select-label">{{ sortLabel }}</text>
            <text class="filter-arrow">&#9662;</text>
          </view>
        </view>
      </view>

      <!-- 列表 -->
      <view v-if="items.length > 0" class="candidate-list">
        <view
          v-for="(item, idx) in items"
          :key="item.symbol"
          class="candidate-card"
          @click="handleViewDetail(item.symbol)"
        >
          <!-- 排名 -->
          <view class="rank-cell">
            <text
              class="rank-num"
              :class="{
                'rank-top1': item.rank === 1,
                'rank-top2': item.rank === 2,
                'rank-top3': item.rank === 3,
              }"
            >{{ item.rank }}</text>
          </view>

          <!-- 股票基本信息 -->
          <view class="stock-cell">
            <view class="stock-name-row">
              <text class="stock-name">{{ item.name }}</text>
              <text class="market-tag">{{ marketLabel(item.market) }}</text>
            </view>
            <text class="stock-symbol">{{ item.symbol }}</text>
            <text v-if="item.industry" class="stock-industry">{{ item.industry }}</text>
          </view>

          <!-- 粗筛分 -->
          <view class="score-cell">
            <text class="score-value" :class="scoreColorClass(item.coarse_score)">
              {{ item.coarse_score }}
            </text>
            <text class="score-label">粗筛分</text>
          </view>

          <!-- 分析师气 -->
          <view class="score-cell">
            <text class="score-value" :class="scoreColorClass(item.analyst_score)">
              {{ item.analyst_score }}
            </text>
            <text class="score-label">分析师气</text>
          </view>

          <!-- 价格 -->
          <view class="price-cell">
            <text class="price-value" v-if="item.current_price != null">
              {{ formatPrice(item.current_price) }}
            </text>
            <text v-else class="price-na">--</text>
            <text
              v-if="item.change_pct != null"
              class="price-change"
              :class="item.change_pct >= 0 ? 'up' : 'down'"
            >{{ formatChangePct(item.change_pct) }}</text>
          </view>
        </view>

        <!-- 加载更多 -->
        <view v-if="loadingMore" class="load-more">
          <text class="load-more-text">加载中...</text>
        </view>

        <view v-else-if="!hasMore && items.length > 0" class="load-more">
          <text class="load-more-text dim">已加载全部</text>
        </view>
      </view>

      <!-- 空状态 -->
      <EmptyState
        v-else
        icon="&#128269;"
        title="暂无符合条件的候选股票"
        description="尝试调整筛选条件或清空筛选"
      >
        <button v-if="hasActiveFilter" class="btn-clear-filter" @click="handleClearFilters">
          清空筛选
        </button>
      </EmptyState>
      <Disclaimer />
</template>

    <!-- 行业选择弹层 -->
    <view v-if="showIndustryPicker" class="picker-overlay" @click="showIndustryPicker = false">
      <view class="picker-panel" @click.stop>
        <view class="picker-header">
          <text class="picker-title">选择行业</text>
          <text class="picker-close" @click="showIndustryPicker = false">完成</text>
        </view>
        <scroll-view scroll-y class="picker-body">
          <view
            class="picker-item"
            :class="{ active: selectedIndustry === '' }"
            @click="handleSelectIndustry('')"
          >全部行业</view>
          <view
            v-for="ind in industryList"
            :key="ind"
            class="picker-item"
            :class="{ active: selectedIndustry === ind }"
            @click="handleSelectIndustry(ind)"
          >{{ ind }}</view>
        </scroll-view>
      </view>
    </view>

    <!-- 排序选择弹层 -->
    <view v-if="showSortPicker" class="picker-overlay" @click="showSortPicker = false">
      <view class="picker-panel" @click.stop>
        <view class="picker-header">
          <text class="picker-title">排序方式</text>
          <text class="picker-close" @click="showSortPicker = false">完成</text>
        </view>
        <scroll-view scroll-y class="picker-body">
          <view
            v-for="s in sortOptions"
            :key="s.value"
            class="picker-item"
            :class="{ active: sortBy === s.value }"
            @click="handleSelectSort(s.value)"
          >{{ s.label }}</view>
        </scroll-view>
      </view>
    </view>
  </view>
  <Disclaimer />
</template>

<script setup lang="ts">
import Disclaimer from '@/components/compliance/Disclaimer.vue'
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import {
  fetchCandidates,
  fetchIndustries,
  type CandidateStock,
} from '@/api/selection'
import EmptyState from '@/components/common/EmptyState.vue'

// ---- 状态 ----
const items = ref<CandidateStock[]>([])
const total = ref(0)
const page = ref(1)
const hasMore = ref(false)
const loading = ref(false)
const loadingMore = ref(false)
const error = ref('')

// 筛选
const scoreRanges = [
  { label: '全部', min: 0, max: 100 },
  { label: '80-100', min: 80, max: 100 },
  { label: '60-79', min: 60, max: 79 },
  { label: '40-59', min: 40, max: 59 },
]
const activeScoreRange = ref('全部')
const selectedIndustry = ref('')
const sortBy = ref<'rank' | 'coarse_score' | 'analyst_score'>('rank')

// 行业列表
const industryList = ref<string[]>([])

// 弹层
const showIndustryPicker = ref(false)
const showSortPicker = ref(false)

// 排序选项
const sortOptions = [
  { label: '综合排名', value: 'rank' },
  { label: '粗筛分 高→低', value: 'coarse_score' },
  { label: '分析师气 高→低', value: 'analyst_score' },
]
const sortLabel = computed(() => {
  const found = sortOptions.find(s => s.value === sortBy.value)
  return found ? found.label : '综合排名'
})

// 当前是否激活了筛选
const hasActiveFilter = computed(() => {
  return activeScoreRange.value !== '全部' || selectedIndustry.value !== '' || sortBy.value !== 'rank'
})

// 当前评分区间
const currentScoreRange = computed(() => {
  const found = scoreRanges.find(r => r.label === activeScoreRange.value)
  return found || scoreRanges[0]
})

// ---- 工具函数 ----
function marketLabel(market: string): string {
  const map: Record<string, string> = { A: 'A股', HK: '港股', US: '美股' }
  return map[market] || market
}

function scoreColorClass(score: number): string {
  if (score >= 80) return 'score-high'
  if (score >= 60) return 'score-mid'
  return 'score-low'
}

function formatPrice(v: number): string {
  return v.toFixed(2)
}

function formatChangePct(v: number): string {
  const sign = v >= 0 ? '+' : ''
  return sign + v.toFixed(2) + '%'
}

// ---- 筛选处理 ----
function handleScoreRange(label: string) {
  activeScoreRange.value = label
  loadCandidates(true)
}

function handleShowIndustryPicker() {
  if (industryList.value.length === 0) {
    loadIndustries()
  }
  showIndustryPicker.value = true
}

function handleSelectIndustry(ind: string) {
  selectedIndustry.value = ind
  showIndustryPicker.value = false
  loadCandidates(true)
}

function handleToggleSort() {
  showSortPicker.value = true
}

function handleSelectSort(value: string) {
  sortBy.value = value as typeof sortBy.value
  showSortPicker.value = false
  loadCandidates(true)
}

function handleClearFilters() {
  activeScoreRange.value = '全部'
  selectedIndustry.value = ''
  sortBy.value = 'rank'
  loadCandidates(true)
}

// ---- 跳转详情 ----
function handleViewDetail(symbol: string) {
  uni.navigateTo({ url: `/pages/selection/detail?symbol=${encodeURIComponent(symbol)}` })
}

// ---- 数据加载 ----
async function loadCandidates(reset: boolean = false) {
  if (reset) {
    page.value = 1
    items.value = []
    hasMore.value = false
    loading.value = true
  } else {
    loadingMore.value = true
  }
  error.value = ''

  try {
    const res = await fetchCandidates({
      page: page.value,
      page_size: 20,
      score_min: currentScoreRange.value.min,
      score_max: currentScoreRange.value.max,
      industry: selectedIndustry.value || undefined,
      sort_by: sortBy.value,
    })

    if (reset) {
      items.value = res
    } else {
      items.value = [...items.value, ...res]
    }
    total.value = items.value.length
    hasMore.value = res.length >= 20
  } catch (e: any) {
    error.value = e?.message || '加载失败'
  } finally {
    loading.value = false
    loadingMore.value = false
  }
}

async function loadIndustries() {
  try {
    industryList.value = await fetchIndustries()
  } catch {
    industryList.value = []
  }
}

// ---- 滚动加载更多 ----
function onScroll(e: any) {
  // uni-app scroll-view 不支持 onScrolltolower 事件参数
}

function onScrollToLower() {
  if (hasMore.value && !loadingMore.value) {
    page.value++
    loadCandidates(false)
  }
}

onMounted(() => {
  loadCandidates(true)
})
</script>

<style lang="scss" scoped>
.candidates-page {
  min-height: 100vh;
  background: $bg-page;
  padding-bottom: env(safe-area-inset-bottom);
}

// ---- 状态视图 ----
.state-view {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 200rpx 0;
  gap: 16rpx;
}

.state-text {
  font-size: $font-size-base;
  color: $text-hint;

  &.error { color: $color-danger; }
}

.btn-retry {
  margin-top: 24rpx;
  padding: 12rpx 48rpx;
  font-size: $font-size-sm;
  color: $color-primary;
  background: rgba(74, 144, 226, 0.1);
  border-radius: 8rpx;
  border: none;
  &::after { border: none; }
}

// ---- 统计条 ----
.stats-bar {
  padding: 16rpx 32rpx;
}

.stats-text {
  font-size: $font-size-xs;
  color: $text-hint;
}

// ---- 筛选栏 ----
.filter-bar {
  background: $bg-card;
  padding: 0 24rpx 20rpx;
  margin: 0 24rpx;
  border-radius: $border-radius;
}

.filter-group {
  padding-top: 16rpx;
}

.filter-label {
  font-size: $font-size-xs;
  color: $text-hint;
  margin-bottom: 12rpx;
  display: block;
}

.filter-scroll {
  white-space: nowrap;
}

.filter-tags {
  display: flex;
  gap: 12rpx;
}

.filter-tag {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 10rpx 24rpx;
  border-radius: 8rpx;
  font-size: $font-size-sm;
  color: $text-secondary;
  background: rgba(0, 0, 0, 0.04);
  transition: all 0.2s;
  flex-shrink: 0;

  &.active {
    color: $color-primary;
    background: rgba(74, 144, 226, 0.1);
    font-weight: 600;
  }
}

.filter-row {
  display: flex;
  gap: 16rpx;
  margin-top: 16rpx;
}

.filter-select {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14rpx 20rpx;
  background: rgba(0, 0, 0, 0.04);
  border-radius: 8rpx;
}

.filter-select-label {
  font-size: $font-size-sm;
  color: $text-secondary;
}

.filter-arrow {
  font-size: 16rpx;
  color: $text-hint;
}

// ---- 候选列表 ----
.candidate-list {
  margin-top: 16rpx;
  padding: 0 24rpx;
}

.candidate-card {
  display: flex;
  align-items: center;
  gap: 16rpx;
  padding: 24rpx 20rpx;
  background: $bg-card;
  border-radius: $border-radius;
  margin-bottom: 12rpx;

  &:active {
    background: rgba(0, 0, 0, 0.02);
  }
}

// 排名
.rank-cell {
  width: 56rpx;
  min-width: 56rpx;
  display: flex;
  justify-content: center;
}

.rank-num {
  font-size: $font-size-base;
  font-weight: 700;
  color: $text-hint;

  &.rank-top1 { color: #FFD700; font-size: 36rpx; }
  &.rank-top2 { color: #C0C0C0; font-size: 32rpx; }
  &.rank-top3 { color: #CD7F32; }
}

// 股票信息
.stock-cell {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4rpx;
}

.stock-name-row {
  display: flex;
  align-items: center;
  gap: 8rpx;
}

.stock-name {
  font-size: $font-size-base;
  font-weight: 600;
  color: $text-primary;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.market-tag {
  font-size: 18rpx;
  padding: 2rpx 8rpx;
  border-radius: 4rpx;
  background: rgba(74, 144, 226, 0.08);
  color: $color-primary;
  flex-shrink: 0;
}

.stock-symbol {
  font-size: 20rpx;
  color: $text-hint;
}

.stock-industry {
  font-size: 18rpx;
  color: $text-hint;
  opacity: 0.7;
}

// 评分
.score-cell {
  display: flex;
  flex-direction: column;
  align-items: center;
  min-width: 72rpx;
  gap: 2rpx;
}

.score-value {
  font-size: 28rpx;
  font-weight: 700;

  &.score-high { color: #EF5350; }
  &.score-mid  { color: #FF9800; }
  &.score-low  { color: $text-hint; }
}

.score-label {
  font-size: 18rpx;
  color: $text-hint;
}

// 价格
.price-cell {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  min-width: 100rpx;
  gap: 2rpx;
}

.price-value {
  font-size: $font-size-sm;
  font-weight: 600;
  color: $text-primary;
}

.price-na {
  font-size: $font-size-sm;
  color: $text-hint;
}

.price-change {
  font-size: 20rpx;
  font-weight: 500;

  &.up   { color: #EF5350; }
  &.down { color: #26A69A; }
}

// ---- 加载更多 ----
.load-more {
  display: flex;
  justify-content: center;
  padding: 32rpx 0 16rpx;
}

.load-more-text {
  font-size: $font-size-xs;
  color: $text-hint;

  &.dim { opacity: 0.4; }
}

// ---- 清空筛选按钮 ----
.btn-clear-filter {
  margin-top: 24rpx;
  padding: 16rpx 48rpx;
  font-size: $font-size-sm;
  color: $color-primary;
  background: rgba(74, 144, 226, 0.08);
  border: 1rpx solid rgba(74, 144, 226, 0.2);
  border-radius: 8rpx;

  &::after { border: none; }
}

// ---- 弹层 ----
.picker-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.4);
  z-index: 1000;
  display: flex;
  align-items: flex-end;
  justify-content: center;
}

.picker-panel {
  width: 100%;
  max-height: 60vh;
  background: $bg-card;
  border-radius: 24rpx 24rpx 0 0;
  overflow: hidden;
}

.picker-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 28rpx 32rpx 20rpx;
  border-bottom: 1rpx solid $border-color;
}

.picker-title {
  font-size: $font-size-base;
  font-weight: 700;
  color: $text-primary;
}

.picker-close {
  font-size: $font-size-sm;
  color: $color-primary;
  font-weight: 600;
}

.picker-body {
  max-height: 50vh;
  padding: 8rpx 0 env(safe-area-inset-bottom);
}

.picker-item {
  padding: 28rpx 32rpx;
  font-size: $font-size-base;
  color: $text-primary;
  border-bottom: 1rpx solid rgba(0, 0, 0, 0.04);

  &.active {
    color: $color-primary;
    font-weight: 600;
  }

  &:active {
    background: rgba(0, 0, 0, 0.02);
  }
}
</style>
