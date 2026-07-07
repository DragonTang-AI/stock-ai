<template>
  <view class="broadcast-player">
    <!-- 无音频提示 -->
    <view v-if="!audioUrl" class="player-empty">
      <text class="empty-icon">🔇</text>
      <text class="empty-text">{{ emptyText }}</text>
    </view>

    <!-- 播放器主体 -->
    <view v-else class="player-body">
      <!-- 进度条 -->
      <view class="progress-bar" @click="handleSeek">
        <view class="progress-track">
          <view class="progress-fill" :style="{ width: progressPercent + '%' }"></view>
          <view
            class="progress-thumb"
            :style="{ left: progressPercent + '%' }"
            @touchstart.stop="handleThumbStart"
            @touchmove.stop="handleThumbMove"
            @touchend.stop="handleThumbEnd"
          ></view>
        </view>
      </view>

      <!-- 时间显示 -->
      <view class="time-row">
        <text class="time-text">{{ formatTime(currentTime) }}</text>
        <text class="time-text">{{ formatTime(duration) }}</text>
      </view>

      <!-- 控制按钮 -->
      <view class="controls">
        <!-- 文本预览：显示当前播报片段 -->
        <view class="text-preview" v-if="broadcastText">
          <text class="preview-text" :class="{ scrolling: isPlaying }">{{ broadcastText }}</text>
        </view>

        <!-- 播放/暂停 -->
        <view class="play-btn" @click="togglePlay">
          <text class="play-icon">{{ isPlaying ? '⏸' : '▶' }}</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, computed, watch, onBeforeUnmount } from 'vue'

const props = withDefaults(
  defineProps<{
    audioUrl?: string | null
    broadcastText?: string
    duration?: number | null
    emptyText?: string
  }>(),
  {
    audioUrl: null,
    broadcastText: '',
    duration: null,
    emptyText: '暂无语音播报',
  }
)

const emit = defineEmits<{
  (e: 'play'): void
  (e: 'pause'): void
  (e: 'ended'): void
  (e: 'timeupdate', currentTime: number): void
  (e: 'error', err: any): void
}>()

// ─── 状态 ───
const isPlaying = ref(false)
const currentTime = ref(0)
const totalDuration = ref(props.duration || 0)
const audioCtx = ref<any>(null)
const isDragging = ref(false)
const dragStartX = ref(0)
const dragStartLeft = ref(0)
const pendingSeek = ref(-1)

// ─── 计算属性 ───
const progressPercent = computed(() => {
  if (totalDuration.value <= 0) return 0
  return Math.min(100, (currentTime.value / totalDuration.value) * 100)
})

// ─── 初始化音频 ───
function initAudio() {
  destroyAudio()
  if (!props.audioUrl) return

  try {
    // uni-app 环境使用 uni.createInnerAudioContext
    const innerAudio = uni.createInnerAudioContext()
    innerAudio.src = props.audioUrl
    innerAudio.autoplay = false

    innerAudio.onCanplay(() => {
      if (innerAudio.duration && innerAudio.duration > 0) {
        totalDuration.value = innerAudio.duration
      }
    })

    innerAudio.onPlay(() => {
      isPlaying.value = true
      emit('play')
    })

    innerAudio.onPause(() => {
      isPlaying.value = false
      emit('pause')
    })

    innerAudio.onStop(() => {
      isPlaying.value = false
      currentTime.value = 0
    })

    innerAudio.onEnded(() => {
      isPlaying.value = false
      currentTime.value = 0
      emit('ended')
    })

    innerAudio.onTimeUpdate(() => {
      if (!isDragging.value) {
        currentTime.value = innerAudio.currentTime || 0
        emit('timeupdate', currentTime.value)
      }
    })

    innerAudio.onError((err: any) => {
      isPlaying.value = false
      console.error('[BroadcastPlayer] 音频播放错误:', err)
      emit('error', err)
    })

    audioCtx.value = innerAudio
  } catch (err) {
    console.error('[BroadcastPlayer] 音频初始化失败:', err)
    emit('error', err)
  }
}

function destroyAudio() {
  if (audioCtx.value) {
    try {
      audioCtx.value.destroy()
    } catch {
      /* 忽略销毁异常 */
    }
    audioCtx.value = null
  }
}

// ─── 播放控制 ───
function togglePlay() {
  if (!audioCtx.value) {
    initAudio()
    // 短暂延迟等 onCanplay
    setTimeout(() => {
      if (audioCtx.value) audioCtx.value.play()
    }, 100)
    return
  }

  if (isPlaying.value) {
    audioCtx.value.pause()
  } else {
    audioCtx.value.play()
  }
}

function handleSeek(e: any) {
  if (!audioCtx.value || totalDuration.value <= 0) return
  const rect = (e.currentTarget as any).getBoundingClientRect?.()
  if (!rect) return
  const x = e.detail?.x ?? e.touches?.[0]?.clientX ?? 0
  const ratio = Math.max(0, Math.min(1, (x - rect.left) / rect.width))
  const seekTime = ratio * totalDuration.value
  audioCtx.value.seek(seekTime)
  currentTime.value = seekTime
}

function handleThumbStart(e: any) {
  isDragging.value = true
  const touch = e.touches?.[0] || e.changedTouches?.[0]
  if (touch) {
    dragStartX.value = touch.clientX
  }
}

function handleThumbMove(e: any) {
  if (!isDragging.value) return
  const touch = e.touches?.[0] || e.changedTouches?.[0]
  if (!touch) return

  // 获取进度条元素尺寸
  const progressBar = (e.currentTarget as any)?.parentElement?.parentElement
  if (!progressBar) return

  const rect = progressBar.getBoundingClientRect?.()
  if (!rect) return

  const ratio = Math.max(0, Math.min(1, (touch.clientX - rect.left) / rect.width))
  currentTime.value = ratio * totalDuration.value
  pendingSeek.value = currentTime.value
}

function handleThumbEnd() {
  if (!isDragging.value) return
  isDragging.value = false

  if (pendingSeek.value >= 0 && audioCtx.value) {
    audioCtx.value.seek(pendingSeek.value)
    currentTime.value = pendingSeek.value
    pendingSeek.value = -1
  }
}

// ─── 工具函数 ───
function formatTime(seconds: number): string {
  if (!isFinite(seconds) || seconds < 0) return '00:00'
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}

// ─── 监听 ───
watch(
  () => props.audioUrl,
  (newUrl) => {
    destroyAudio()
    currentTime.value = 0
    isPlaying.value = false
    totalDuration.value = props.duration || 0
    if (newUrl) {
      // 延迟初始化，等 DOM 更新
      setTimeout(initAudio, 50)
    }
  }
)

watch(
  () => props.duration,
  (newDuration) => {
    if (newDuration != null && newDuration > 0 && !audioCtx.value) {
      totalDuration.value = newDuration
    }
  }
)

// ─── 清理 ───
onBeforeUnmount(() => {
  destroyAudio()
})
</script>

<style scoped lang="scss">
.broadcast-player {
  background: var(--bg-card, #fff);
  border-radius: 16rpx;
  padding: 24rpx;
}

/* 无音频状态 */
.player-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 32rpx 0;
  gap: 12rpx;
}

.empty-icon {
  font-size: 48rpx;
  opacity: 0.6;
}

.empty-text {
  font-size: 26rpx;
  color: var(--text-hint, #999);
}

/* 播放器主体 */
.player-body {
  display: flex;
  flex-direction: column;
  gap: 16rpx;
}

/* 进度条 */
.progress-bar {
  padding: 12rpx 0;
  cursor: pointer;
}

.progress-track {
  position: relative;
  height: 8rpx;
  background: var(--bg-input, #e8e8ed);
  border-radius: 4rpx;
  overflow: visible;
}

.progress-fill {
  position: absolute;
  top: 0;
  left: 0;
  height: 100%;
  background: linear-gradient(90deg, #4A90E2, #6BB5FF);
  border-radius: 4rpx;
  transition: width 0.15s linear;
}

.progress-thumb {
  position: absolute;
  top: 50%;
  transform: translate(-50%, -50%);
  width: 24rpx;
  height: 24rpx;
  background: #4A90E2;
  border-radius: 50%;
  border: 4rpx solid #fff;
  box-shadow: 0 2rpx 8rpx rgba(0, 0, 0, 0.2);
  z-index: 2;
}

/* 时间行 */
.time-row {
  display: flex;
  justify-content: space-between;
}

.time-text {
  font-size: 22rpx;
  color: var(--text-hint, #999);
  font-variant-numeric: tabular-nums;
}

/* 控制区 */
.controls {
  display: flex;
  align-items: center;
  gap: 20rpx;
}

.text-preview {
  flex: 1;
  overflow: hidden;
  padding: 12rpx 16rpx;
  background: var(--bg-input, #f5f6fa);
  border-radius: 12rpx;
}

.preview-text {
  font-size: 24rpx;
  color: var(--text-secondary, #666);
  display: block;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;

  &.scrolling {
    animation: marquee 8s linear infinite;
  }
}

@keyframes marquee {
  0% { transform: translateX(60%); }
  100% { transform: translateX(-100%); }
}

.play-btn {
  width: 72rpx;
  height: 72rpx;
  border-radius: 50%;
  background: linear-gradient(135deg, #4A90E2, #357ABD);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  box-shadow: 0 4rpx 16rpx rgba(74, 144, 226, 0.35);
  transition: transform 0.15s;

  &:active {
    transform: scale(0.92);
  }
}

.play-icon {
  font-size: 32rpx;
  color: #fff;
}
</style>
