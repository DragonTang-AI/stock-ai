<template>
  <view class="ctb-wrap">
    <view class="ctb-bar">
      <!-- 滑块 -->
      <view
        class="ctb-slider"
        :style="{
          width: sliderWidth,
          transform: `translateX(${activeIndex * 100}%)`,
        }"
      />
      <!-- Tab 项 -->
      <view
        v-for="(item, idx) in TABS"
        :key="item.path"
        class="ctb-item"
        :class="{ 'is-active': idx === activeIndex }"
        @click="onTap(idx)"
      >
        <view class="ctb-icon-wrap">
          <view class="ctb-icon" :class="{ 'is-hide': idx === activeIndex }" :style="{ backgroundImage: `url(${item.icon})` }"></view>
          <view class="ctb-icon ctb-icon-active" :class="{ 'is-show': idx === activeIndex }" :style="{ backgroundImage: `url(${item.activeIcon})` }"></view>
        </view>
        <text class="ctb-text">{{ item.text }}</text>
      </view>
    </view>
    <!-- 底部安全区占位 -->
    <view class="ctb-safe" />
  </view>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface TabItem {
  path: string
  text: string
  icon: string
  activeIcon: string
}

const props = defineProps<{
  /** 当前页面路径，如 /pages/market/index */
  current: string
}>()

const TABS: TabItem[] = [
  { path: '/pages/market/index', text: '行情', icon: '/static/tabbar/market.v3.png', activeIcon: '/static/tabbar/market-active.v3.png' },
  { path: '/pages/agent-market/index', text: '交易员', icon: '/static/tabbar/agent-market.v3.png', activeIcon: '/static/tabbar/agent-market-active.v3.png' },
  { path: '/pages/selection/index', text: '选股', icon: '/static/tabbar/selection.v3.png', activeIcon: '/static/tabbar/selection-active.v3.png' },
  { path: '/pages/portfolio/index', text: '持仓', icon: '/static/tabbar/portfolio.v3.png', activeIcon: '/static/tabbar/portfolio-active.v3.png' },
  { path: '/pages/advisor/index', text: 'AI助手', icon: '/static/tabbar/advisor.v3.png', activeIcon: '/static/tabbar/advisor-active.v3.png' },
  { path: '/pages/mine/index', text: '我的', icon: '/static/tabbar/mine.v3.png', activeIcon: '/static/tabbar/mine-active.v3.png' },
]

const activeIndex = computed(() => {
  const idx = TABS.findIndex((t) => t.path === props.current)
  return idx === -1 ? 0 : idx
})

const sliderWidth = computed(() => `calc(100% / ${TABS.length})`)

function onTap(idx: number) {
  if (idx === activeIndex.value) return
  uni.switchTab({ url: TABS[idx].path })
}
</script>

<style lang="scss" scoped>
.ctb-wrap {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 999;
  background: var(--bg-card, #ffffff);
  box-shadow: 0 -2rpx 16rpx rgba(0, 0, 0, 0.06);
}

.ctb-bar {
  position: relative;
  display: flex;
  align-items: stretch;
  height: 112rpx;
  padding: 10rpx 16rpx 8rpx;
}

/* 滑块：圆角胶囊，丝滑过渡 */
.ctb-slider {
  position: absolute;
  left: 16rpx;
  top: 10rpx;
  bottom: 8rpx;
  border-radius: 40rpx;
  background: rgba(74, 144, 226, 0.16);
  box-shadow: inset 0 0 0 1.5rpx rgba(74, 144, 226, 0.18);
  transition: transform 0.38s cubic-bezier(0.22, 1, 0.36, 1);
  will-change: transform;
  pointer-events: none;
}

.ctb-item {
  position: relative;
  z-index: 1;
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2rpx;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}

.ctb-icon-wrap {
  position: relative;
  width: 52rpx;
  height: 52rpx;
}

.ctb-icon {
  position: absolute;
  left: 0;
  top: 0;
  width: 100%;
  height: 100%;
  background-repeat: no-repeat;
  background-position: center;
  background-size: contain;
  opacity: 1;
  transition: opacity 0.22s ease, transform 0.28s cubic-bezier(0.22, 1, 0.36, 1);
}

.ctb-icon-active {
  opacity: 0;
}

.ctb-icon.is-hide {
  opacity: 0;
}

.ctb-icon-active.is-show {
  opacity: 1;
}

.ctb-item.is-active .ctb-icon-wrap .ctb-icon {
  transform: scale(1.08);
}

.ctb-text {
  font-size: 20rpx;
  line-height: 1.2;
  color: var(--text-hint, #6E7681);
  transition: color 0.25s ease;
  font-weight: 500;
}

.ctb-item.is-active .ctb-text {
  color: var(--color-primary, #4A90E2);
  font-weight: 700;
}

.ctb-safe {
  height: env(safe-area-inset-bottom);
  background: var(--bg-card, #ffffff);
}
</style>
