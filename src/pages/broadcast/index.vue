<template>
  <view class="broadcast-page">
    <!-- 顶部标题 -->
    <view class="page-header">
      <text class="page-title">每日播报</text>
      <text class="page-subtitle">AI 智能选股语音播报</text>
    </view>

    <!-- 加载状态 -->
    <view class="loading-state" v-if="isLoading">
      <text class="loading-text">加载中...</text>
    </view>

    <!-- 无数据状态 -->
    <view class="empty-state" v-else-if="!broadcast">
      <EmptyState icon="📻" title="暂无播报" description="今日播报尚未生成，请稍后再试" />
      <button class="btn-retry" @click="loadToday">重新加载</button>
    </view>

    <!-- 播报内容 -->
    <view v-else class="broadcast-content">
      <!-- 1. 播报头部 -->
      <view class="broadcast-header">
        <view class="header-left">
          <text class="broadcast-date">{{ formatDate(broadcast.date) }}</text>
          <text class="broadcast-time">生成于 {{ formatTime(broadcast.created_at) }}</text>
        </view>
        <view class="header-right">
          <view class="play-toggle" :class="{ active: playerPlaying }" @click="togglePlayer">
            <text class="toggle-icon">{{ playerPlaying ? '⏸' : '▶' }}</text>
          </view>
        </view>
      </view>

      <!-- 2. 语音播放器 -->
      <BroadcastPlayer
        ref="playerRef"
        :audioUrl="broadcast.audio_url"
        :broadcastText="currentText"
        :duration="broadcast.duration"
        @play="onPlay"
        @pause="onPause"
        @ended="onEnded"
        @error="onAudioError"
      />

      <!-- 3. 播报内容分模块 -->
      <!-- 大盘综述 -->
      <view class="section-card">
        <view class="card-header">
          <view class="section-icon overview-icon">📊</view>
          <text class="card-title">大盘综述</text>
        </view>
        <view class="card-body">
          <text class="content-text">{{ broadcast.content.overview || '暂无数据' }}</text>
        </view>
      </view>

      <!-- 精选推荐 -->
      <view class="section-card">
        <view class="card-header">
          <view class="section-icon pick-icon">⭐</view>
          <text class="card-title">精选推荐</text>
        </view>
        <view class="card-body">
          <view v-if="broadcast.content.recommendations && broadcast.content.recommendations.length">
            <view
              class="recommend-item"
              v-for="(rec, idx) in broadcast.content.recommendations"
              :key="rec.symbol + idx"
            >
              <view class="rec-header">
                <text class="rec-symbol">{{ formatSymbol(rec.symbol) }}</text>
                <text class="rec-name">{{ rec.name }}</text>
                <view class="confidence-badge" :class="confidenceClass(rec.confidence)">
                  <text class="confidence-text">{{ rec.confidence }}%</text>
                </view>
              </view>
              <text class="rec-reason">{{ rec.reason || '暂无理由说明' }}</text>
            </view>
          </view>
          <EmptyState v-else icon="📋" title="暂无推荐" description="今日无精选推荐" />
        </view>
      </view>

      <!-- 风险提示 -->
      <view class="section-card risk-card">
        <view class="card-header">
          <view class="section-icon risk-icon">⚠️</view>
          <text class="card-title">风险提示</text>
        </view>
        <view class="card-body">
          <text class="content-text risk-text">{{ broadcast.content.risk_warnings || '市场有风险，投资需谨慎。' }}</text>
        </view>
      </view>

      <!-- 4. 历史播报切换 -->
      <view class="history-nav" v-if="historyList.length > 1">
        <text class="nav-title">历史播报</text>
        <view class="nav-buttons">
          <view
            class="nav-btn"
            :class="{ disabled: !hasPrev }"
            @click="goPrev"
          >
            <text class="nav-arrow">‹</text>
            <text class="nav-label">上一条</text>
          </view>
          <text class="nav-indicator">{{ currentIndex + 1 }} / {{ historyList.length }}</text>
          <view
            class="nav-btn"
            :class="{ disabled: !hasNext }"
            @click="goNext"
          >
            <text class="nav-label">下一条</text>
            <text class="nav-arrow">›</text>
          </view>
        </view>
      </view>

      <!-- 免责声明 -->
      <Disclaimer />
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import BroadcastPlayer from '@/components/selection/BroadcastPlayer.vue'
import Disclaimer from '@/components/compliance/Disclaimer.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import { trackPageView, trackAction } from '@/utils/tracker'
import {
  fetchTodayBroadcast,
  fetchBroadcastList,
  type Broadcast,
} from '@/api/broadcast'

// ─── 状态 ───
const isLoading = ref(false)
const broadcast = ref<Broadcast | null>(null)
const historyList = ref<Broadcast[]>([])
const currentIndex = ref(0)
const playerPlaying = ref(false)
const playerRef = ref<InstanceType<typeof BroadcastPlayer> | null>(null)

// ─── 计算属性 ───
const hasPrev = computed(() => currentIndex.value > 0)
const hasNext = computed(() => currentIndex.value < historyList.value.length - 1)

const currentText = computed(() => {
  if (!broadcast.value) return ''
  const c = broadcast.value.content
  return [c.overview, ...(c.recommendations || []).map(r => `${r.name}：${r.reason}`), c.risk_warnings].filter(Boolean).join('。')
})

// ─── 方法 ───
function formatDate(dateStr: string): string {
  if (!dateStr) return '-'
  const d = new Date(dateStr)
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  const weekdays = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
  const wd = weekdays[d.getDay()]
  return `${d.getFullYear()}年${mm}月${dd}日 ${wd}`
}

function formatTime(iso: string): string {
  if (!iso) return '-'
  const d = new Date(iso)
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

function formatSymbol(symbol: string): string {
  return symbol.replace(/\.[A-Z]{2,4}$/, '')
}

function confidenceClass(confidence: number): string {
  if (confidence >= 80) return 'confidence-high'
  if (confidence >= 60) return 'confidence-mid'
  return 'confidence-low'
}

async function loadToday() {
  isLoading.value = true
  try {
    const data = await fetchTodayBroadcast()
    broadcast.value = data
    // 同时加载历史列表
    await loadHistory()
  } catch (err: any) {
    console.warn('[Broadcast] 加载今日播报失败', err)
    broadcast.value = null
    // 尝试加载历史
    await loadHistory()
    if (historyList.value.length > 0) {
      broadcast.value = historyList.value[0]
      currentIndex.value = 0
    }
  } finally {
    isLoading.value = false
  }
}

async function loadHistory() {
  try {
    const res = await fetchBroadcastList({ limit: 30, offset: 0 })
    historyList.value = res.items || []
    // 定位当前播报在历史列表中的位置
    if (broadcast.value) {
      const idx = historyList.value.findIndex(b => b.id === broadcast.value!.id)
      if (idx >= 0) currentIndex.value = idx
    }
  } catch (err) {
    console.warn('[Broadcast] 加载历史列表失败', err)
  }
}

function goPrev() {
  if (!hasPrev.value) return
  currentIndex.value--
  broadcast.value = historyList.value[currentIndex.value]
}

function goNext() {
  if (!hasNext.value) return
  currentIndex.value++
  broadcast.value = historyList.value[currentIndex.value]
}

function togglePlayer() {
  if (!playerRef.value) return
  // 通过 BroadcastPlayer 暴露的方法控制
  // 这里通过 audio 上下文控制
  playerPlaying.value = !playerPlaying.value
  trackAction(playerPlaying.value ? 'broadcast_play' : 'broadcast_pause', {
    broadcast_id: broadcast.value?.id,
    date: broadcast.value?.date,
  })
}

function onPlay() {
  playerPlaying.value = true
}

function onPause() {
  playerPlaying.value = false
}

function onEnded() {
  playerPlaying.value = false
}

function onAudioError(err: any) {
  uni.showToast({ title: '音频播放失败', icon: 'none' })
  playerPlaying.value = false
}

// ─── 生命周期 ───
onMounted(loadToday)
onShow(() => {
  if (!broadcast.value) loadToday()
  trackPageView('broadcast')
})
</script>

<style scoped lang="scss">
.broadcast-page {
  padding: 24rpx 24rpx calc(env(safe-area-inset-bottom) + 48rpx);
  background: var(--bg-page, #F5F5F7);
  min-height: 100vh;
}

/* 页面标题 */
.page-header {
  padding: 16rpx 0 24rpx;
  display: flex;
  flex-direction: column;
  gap: 4rpx;
}

.page-title {
  font-size: 40rpx;
  font-weight: 700;
  color: var(--text-primary, #1A1A2E);
}

.page-subtitle {
  font-size: 24rpx;
  color: var(--text-hint, #999);
}

/* 加载/空状态 */
.loading-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 120rpx 0;
}

.loading-text {
  font-size: 28rpx;
  color: var(--text-hint, #999);
}

.btn-retry {
  margin-top: 24rpx;
  background: var(--color-primary, #4A90E2);
  color: #fff;
  border-radius: 12rpx;
  font-size: 26rpx;
  padding: 12rpx 48rpx;
}

/* 播报头部 */
.broadcast-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: linear-gradient(135deg, #1A1A2E 0%, #16213E 100%);
  border-radius: 20rpx;
  padding: 28rpx 24rpx;
  margin-bottom: 24rpx;
  color: #fff;
}

.header-left {
  display: flex;
  flex-direction: column;
  gap: 6rpx;
}

.broadcast-date {
  font-size: 32rpx;
  font-weight: 700;
}

.broadcast-time {
  font-size: 22rpx;
  color: rgba(255, 255, 255, 0.6);
}

.play-toggle {
  width: 72rpx;
  height: 72rpx;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.15);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s;

  &.active {
    background: var(--color-primary, #4A90E2);
  }
}

.toggle-icon {
  font-size: 32rpx;
  color: #fff;
}

/* 内容卡片 */
.broadcast-content {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.section-card {
  background: var(--bg-card, #fff);
  border-radius: 20rpx;
  padding: 24rpx;
  margin-bottom: 24rpx;
  box-shadow: 0 2rpx 12rpx rgba(0, 0, 0, 0.04);
}

.risk-card {
  border-left: 6rpx solid #FF9500;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 12rpx;
  margin-bottom: 16rpx;
}

.section-icon {
  font-size: 32rpx;
}

.card-title {
  font-size: 30rpx;
  font-weight: 600;
  color: var(--text-primary, #1A1A2E);
}

.card-body {
  padding: 0;
}

.content-text {
  font-size: 26rpx;
  color: var(--text-primary, #333);
  line-height: 1.8;
}

.risk-text {
  color: #FF9500;
  font-weight: 500;
}

/* 推荐条目 */
.recommend-item {
  padding: 20rpx 0;
  border-bottom: 1rpx solid var(--border-color, #f0f0f0);

  &:last-child {
    border-bottom: none;
  }
}

.rec-header {
  display: flex;
  align-items: center;
  gap: 12rpx;
  margin-bottom: 8rpx;
}

.rec-symbol {
  font-size: 28rpx;
  font-weight: 700;
  color: var(--text-primary, #1A1A2E);
}

.rec-name {
  font-size: 24rpx;
  color: var(--text-secondary, #666);
}

.confidence-badge {
  margin-left: auto;
  padding: 4rpx 12rpx;
  border-radius: 16rpx;
  font-size: 20rpx;

  &.confidence-high {
    background: rgba(52, 199, 89, 0.12);
    .confidence-text { color: var(--color-success, #34C759); }
  }
  &.confidence-mid {
    background: rgba(255, 149, 0, 0.12);
    .confidence-text { color: #FF9500; }
  }
  &.confidence-low {
    background: rgba(255, 59, 48, 0.12);
    .confidence-text { color: var(--color-danger, #FF3B30); }
  }
}

.confidence-text {
  font-weight: 600;
}

.rec-reason {
  font-size: 24rpx;
  color: var(--text-secondary, #666);
  line-height: 1.6;
}

/* 历史导航 */
.history-nav {
  background: var(--bg-card, #fff);
  border-radius: 20rpx;
  padding: 24rpx;
  margin-bottom: 24rpx;
  box-shadow: 0 2rpx 12rpx rgba(0, 0, 0, 0.04);
}

.nav-title {
  font-size: 28rpx;
  font-weight: 600;
  color: var(--text-primary, #1A1A2E);
  display: block;
  margin-bottom: 16rpx;
}

.nav-buttons {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.nav-btn {
  display: flex;
  align-items: center;
  gap: 8rpx;
  padding: 12rpx 24rpx;
  background: var(--bg-input, #f5f6fa);
  border-radius: 12rpx;
  transition: opacity 0.15s;

  &.disabled {
    opacity: 0.4;
    pointer-events: none;
  }
}

.nav-arrow {
  font-size: 32rpx;
  color: var(--color-primary, #4A90E2);
  font-weight: 700;
}

.nav-label {
  font-size: 24rpx;
  color: var(--color-primary, #4A90E2);
  font-weight: 500;
}

.nav-indicator {
  font-size: 24rpx;
  color: var(--text-hint, #999);
}
</style>
