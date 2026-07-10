<template>
  <view class="selection-page">
    <!-- 骨架屏 -->
    <LoadingSkeleton v-if="loading" scene="selection" :rows="3" />

    <!-- 委员会分析结果 -->
    <view v-else-if="results.length > 0">
      <view class="section-title">AI 委员会选股</view>

      <view
        v-for="(item, idx) in results"
        :key="item.symbol"
        class="result-card"
      >
        <!-- 结果头部：可点击展开 -->
        <view class="card-header" @click="toggleExpand(idx)">
          <view class="header-left">
            <view class="name-row">
              <text class="stock-name">{{ item.name }}</text>
              <text class="stock-symbol">{{ item.symbol }}</text>
            </view>
            <view class="action-badge" :class="actionClass(item.final_action)">
              {{ actionLabel(item.final_action) }}
            </view>
          </view>
          <view class="header-right">
            <view class="confidence-ring">
              <text class="confidence-text">{{ formatPct(item.final_confidence) }}</text>
              <text class="confidence-label">置信度</text>
            </view>
            <text class="expand-icon">{{ expandedSet.has(idx) ? '收起' : '展开' }}</text>
          </view>
        </view>

        <!-- 详细信号：展开后显示 -->
        <view v-if="expandedSet.has(idx)" class="card-detail">
          <view class="summary-box">
            <text class="summary-text">{{ item.summary }}</text>
          </view>

          <view class="signals-title">分 Agent 信号</view>
          <view
            v-for="signal in item.signals"
            :key="signal.agent"
            class="signal-row"
          >
            <view class="signal-head">
              <text class="signal-agent">{{ agentLabel(signal.agent) }}</text>
              <view class="signal-action" :class="actionClass(signal.action)">
                {{ actionLabel(signal.action) }}
              </view>
              <text class="signal-score">{{ signal.score }}分</text>
            </view>
            <text class="signal-reason">{{ signal.reasoning }}</text>
          </view>

          <!-- 操作按钮 -->
          <view class="card-actions">
            <button
              class="btn-star"
              :class="{ starred: watchlistSet.has(item.symbol) }"
              @click="handleToggleWatch(item.symbol)"
            >
              {{ watchlistSet.has(item.symbol) ? '已关注' : '加入自选' }}
            </button>
            <button
              class="btn-detail"
              @click="handleViewDetail(item.symbol)"
            >
              查看详情
            </button>
          </view>
        </view>
      </view>
    </view>

    <!-- 空状态 -->
    <view v-else class="state-view">
      <text class="state-text">暂无选股结果</text>
      <text class="state-hint">每日收盘后 AI 委员会将自动生成分析</text>
    </view>

    <!-- 错误 -->
    <view v-if="error" class="state-view">
      <text class="state-text error">{{ error }}</text>
      <button class="btn-retry" @click="loadResults">重试</button>
    </view>
  </view>
  <Disclaimer />
</template>

<script setup lang="ts">
import Disclaimer from '@/components/compliance/Disclaimer.vue'
import { ref, reactive, onMounted } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import LoadingSkeleton from '@/components/common/LoadingSkeleton.vue'
import { trackPageView, trackAction } from '@/utils/tracker'
import {
  fetchCommitteeResults,
  addToWatchlist,
  removeFromWatchlist,
  type CommitteeResult,
} from '@/api/selection'

const results = ref<CommitteeResult[]>([])
const loading = ref(true)
const error = ref('')
const expandedSet = reactive(new Set<number>())
const watchlistSet = reactive(new Set<string>())

function actionLabel(action: string): string {
  const map: Record<string, string> = {
    BUY: '买入',
    SELL: '卖出',
    HOLD: '观望',
  }
  return map[action] || action
}

function actionClass(action: string): string {
  return action === 'BUY' ? 'buy' : action === 'SELL' ? 'sell' : 'hold'
}

function agentLabel(agent: string): string {
  const map: Record<string, string> = {
    technical: '技术面 Agent',
    fundamental: '基本面 Agent',
    sentiment: '舆情 Agent',
    emotion: '情绪 Agent',
  }
  return map[agent] || agent
}

function formatPct(v: number): string {
  return v.toFixed(0) + '%'
}

function toggleExpand(idx: number) {
  if (expandedSet.has(idx)) {
    expandedSet.delete(idx)
  } else {
    expandedSet.add(idx)
  }
}

async function handleToggleWatch(symbol: string) {
  try {
    if (watchlistSet.has(symbol)) {
      await removeFromWatchlist(symbol)
      watchlistSet.delete(symbol)
      uni.showToast({ title: '已取消关注', icon: 'success' })
    } else {
      await addToWatchlist(symbol)
      watchlistSet.add(symbol)
      uni.showToast({ title: '已加入自选', icon: 'success' })
      trackAction('add_watchlist', { symbol })
    }
  } catch {
    uni.showToast({ title: '操作失败', icon: 'none' })
  }
}

function handleViewDetail(symbol: string) {
  uni.navigateTo({ url: `/pages/selection/detail?symbol=${encodeURIComponent(symbol)}` })
}

async function loadResults() {
  loading.value = true
  error.value = ''
  try {
    results.value = await fetchCommitteeResults()
  } catch (e: any) {
    error.value = e?.message || '加载失败'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadResults()
})

onShow(() => {
  trackPageView('selection')
})
</script>

<style lang="scss" scoped>
.selection-page {
  min-height: 100vh;
  background: $bg-page;
  padding-bottom: env(safe-area-inset-bottom);
}

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

.state-hint {
  font-size: $font-size-sm;
  color: $text-hint;
  opacity: 0.6;
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

// ---- 标题 ----
.section-title {
  padding: 24rpx 32rpx 16rpx;
  font-size: $font-size-lg;
  font-weight: 700;
  color: $text-primary;
}

// ---- 结果卡片 ----
.result-card {
  margin: 0 24rpx 24rpx;
  background: $bg-card;
  border-radius: $border-radius;
  overflow: hidden;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 24rpx 28rpx;
  cursor: pointer;

  &:active {
    background: rgba(0, 0, 0, 0.02);
  }
}

.header-left {
  display: flex;
  flex-direction: column;
  gap: 8rpx;
}

.name-row {
  display: flex;
  align-items: baseline;
  gap: 12rpx;
}

.stock-name {
  font-size: $font-size-base;
  font-weight: 700;
  color: $text-primary;
}

.stock-symbol {
  font-size: $font-size-xs;
  color: $text-hint;
}

.action-badge {
  display: inline-block;
  padding: 4rpx 16rpx;
  border-radius: 6rpx;
  font-size: $font-size-xs;
  font-weight: 700;
  width: fit-content;

  &.buy {
    background: rgba(239, 83, 80, 0.1);
    color: var(--color-up, #EF5350);
  }
  &.sell {
    background: rgba(38, 166, 154, 0.1);
    color: var(--color-down, #26A69A);
  }
  &.hold {
    background: rgba(153, 153, 153, 0.1);
    color: var(--text-hint, #999);
  }
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16rpx;
  flex-shrink: 0;
}

.confidence-ring {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.confidence-text {
  font-size: $font-size-lg;
  font-weight: 700;
  color: $color-primary;
}

.confidence-label {
  font-size: 18rpx;
  color: $text-hint;
}

.expand-icon {
  font-size: $font-size-xs;
  color: $text-hint;
}

// ---- 展开详情 ----
.card-detail {
  border-top: 1rpx solid $border-color;
  padding: 24rpx 28rpx;
}

.summary-box {
  background: rgba(74, 144, 226, 0.06);
  border-radius: 8rpx;
  padding: 16rpx 20rpx;
  margin-bottom: 20rpx;
}

.summary-text {
  font-size: $font-size-sm;
  color: $text-secondary;
  line-height: 1.6;
}

.signals-title {
  font-size: $font-size-sm;
  font-weight: 600;
  color: $text-primary;
  margin-bottom: 16rpx;
}

.signal-row {
  margin-bottom: 20rpx;

  &:last-child {
    margin-bottom: 0;
  }
}

.signal-head {
  display: flex;
  align-items: center;
  gap: 12rpx;
  margin-bottom: 6rpx;
}

.signal-agent {
  font-size: $font-size-sm;
  font-weight: 600;
  color: $text-primary;
}

.signal-action {
  font-size: 20rpx;
  padding: 2rpx 10rpx;
  border-radius: 4rpx;
  font-weight: 600;

  &.buy {
    background: rgba(239, 83, 80, 0.1);
    color: var(--color-up, #EF5350);
  }
  &.sell {
    background: rgba(38, 166, 154, 0.1);
    color: var(--color-down, #26A69A);
  }
  &.hold {
    background: rgba(153, 153, 153, 0.1);
    color: var(--text-hint, #999);
  }
}

.signal-score {
  font-size: 20rpx;
  color: $text-hint;
  margin-left: auto;
}

.signal-reason {
  font-size: $font-size-sm;
  color: $text-secondary;
  line-height: 1.5;
  display: block;
}

// ---- 卡片操作 ----
.card-actions {
  display: flex;
  gap: 16rpx;
  margin-top: 24rpx;
}

.btn-star {
  flex: 1;
  padding: 18rpx;
  font-size: $font-size-sm;
  color: $color-primary;
  background: rgba(74, 144, 226, 0.08);
  border-radius: 8rpx;
  border: 1rpx solid rgba(74, 144, 226, 0.2);
  text-align: center;

  &::after { border: none; }

  &.starred {
    color: $text-hint;
    background: rgba(0, 0, 0, 0.04);
    border-color: $border-color;
  }
}

.btn-detail {
  flex: 1;
  padding: 18rpx;
  font-size: $font-size-sm;
  color: #fff;
  background: $color-primary;
  border-radius: 8rpx;
  border: none;
  text-align: center;

  &::after { border: none; }
}
</style>
