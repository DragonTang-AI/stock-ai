<template>
  <view class="notification-center">
    <view class="header">
      <text class="title">消息中心</text>
      <view class="header-actions">
        <view class="action-btn" @click="handleMarkAllRead">
          <text class="action-text">全部已读</text>
        </view>
        <view class="action-btn" @click="handleClearAll">
          <text class="action-text">清空</text>
        </view>
      </view>
    </view>

    <!-- 加载中 -->
    <view v-if="initialLoading" class="state-view">
      <text class="state-text">加载中...</text>
    </view>

    <!-- 空状态 -->
    <view v-else-if="notifications.length === 0" class="state-view">
      <text class="state-text">暂无新消息</text>
    </view>

    <!-- 通知列表 -->
    <scroll-view
      v-else
      class="notification-list"
      scroll-y
      :show-scrollbar="false"
      @scrolltolower="loadMore"
    >
      <view
        v-for="item in notifications"
        :key="item.id"
        class="notification-item"
        :class="{ unread: !item.read }"
        @click="handleClick(item)"
      >
        <view class="item-left">
          <view class="icon-wrapper" :class="item.type">
            <text class="icon-text">{{ getIcon(item.type) }}</text>
          </view>
        </view>
        <view class="item-main">
          <view class="item-header">
            <text class="item-title">{{ item.title }}</text>
            <text class="item-time">{{ formatTime(item.created_at) }}</text>
          </view>
          <text class="item-content">{{ item.content }}</text>
        </view>
        <view v-if="!item.read" class="unread-dot"></view>
      </view>
      <view v-if="loadingMore" class="loading-more">
        <text>加载中...</text>
      </view>
      <view v-else-if="!hasMore && notifications.length > 0" class="loading-more">
        <text class="no-more">没有更多了</text>
      </view>
    </scroll-view>
  </view>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import {
  fetchNotifications,
  markAsRead,
  markAllAsRead,
  clearAllNotifications,
  type NotificationItem,
} from '@/api/notifications'

const notifications = ref<NotificationItem[]>([])
const initialLoading = ref(true)
const loadingMore = ref(false)
const hasMore = ref(true)
const offset = ref(0)
const PAGE_SIZE = 20

function getIcon(type: NotificationItem['type']): string {
  const map: Record<string, string> = {
    system: 'SY',
    price: 'PL',
    selection: 'SC',
    advisor: 'AI',
    trade: 'TR',
  }
  return map[type] || 'NT'
}

function formatTime(createdAt: string): string {
  const date = new Date(createdAt)
  const now = Date.now()
  const diff = now - date.getTime()
  const minute = 60000
  const hour = minute * 60
  const day = hour * 24

  if (Number.isNaN(diff)) return ''
  if (diff < minute) return '刚刚'
  if (diff < hour) return Math.floor(diff / minute) + '分钟前'
  if (diff < day) return Math.floor(diff / hour) + '小时前'
  if (diff < day * 7) return Math.floor(diff / day) + '天前'
  return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}

async function loadNotifications(isLoadMore = false) {
  try {
    const res = await fetchNotifications({ limit: PAGE_SIZE, offset: offset.value })
    if (isLoadMore) {
      notifications.value.push(...res.items)
    } else {
      notifications.value = res.items
    }
    offset.value = isLoadMore ? offset.value + PAGE_SIZE : PAGE_SIZE
    hasMore.value = res.items.length >= PAGE_SIZE
  } catch {
    uni.showToast({ title: '加载失败', icon: 'none' })
  } finally {
    initialLoading.value = false
    loadingMore.value = false
  }
}

async function handleClick(item: NotificationItem) {
  if (!item.read) {
    try {
      await markAsRead(item.id)
      item.read = true
    } catch { /* 静默失败 */ }
  }
  // 跳转逻辑
  if (item.data?.url) {
    uni.navigateTo({ url: item.data.url })
  }
}

async function handleMarkAllRead() {
  try {
    await markAllAsRead()
    notifications.value.forEach(item => { item.read = true })
    uni.showToast({ title: '全部标记为已读', icon: 'success' })
  } catch {
    uni.showToast({ title: '操作失败', icon: 'none' })
  }
}

async function handleClearAll() {
  uni.showModal({
    title: '清空消息',
    content: '确定清空所有消息？',
    success: async (res: { confirm: boolean }) => {
      if (res.confirm) {
        try {
          await clearAllNotifications()
          notifications.value = []
          uni.showToast({ title: '已清空', icon: 'success' })
        } catch {
          uni.showToast({ title: '操作失败', icon: 'none' })
        }
      }
    },
  })
}

async function loadMore() {
  if (loadingMore.value || !hasMore.value) return
  loadingMore.value = true
  await loadNotifications(true)
}

onMounted(() => {
  loadNotifications()
})
</script>

<style lang="scss" scoped>
.notification-center {
  min-height: 100vh;
  background: $bg-page;
  padding-bottom: env(safe-area-inset-bottom);
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 32rpx 32rpx 24rpx;
  background: $bg-card;
  border-bottom: 1rpx solid $border-color;
}

.title {
  font-size: $font-size-xl;
  font-weight: 600;
  color: $text-primary;
}

.header-actions {
  display: flex;
  gap: 24rpx;
}

.action-btn {
  padding: 8rpx 16rpx;
  border-radius: 6rpx;
  background: rgba(74, 144, 226, 0.1);
  cursor: pointer;

  &:active {
    background: rgba(74, 144, 226, 0.2);
  }
}

.action-text {
  font-size: $font-size-sm;
  color: $color-primary;
}

.state-view {
  padding: 120rpx 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.state-text {
  font-size: $font-size-base;
  color: $text-hint;
}

.notification-list {
  height: calc(100vh - 120rpx);
  padding: 0 24rpx;
}

.notification-item {
  display: flex;
  padding: 28rpx 0;
  border-bottom: 1rpx solid $border-color;
  position: relative;
  cursor: pointer;

  &:last-child {
    border-bottom: none;
  }

  &.unread {
    background: rgba(74, 144, 226, 0.03);
  }
}

.item-left {
  margin-right: 20rpx;
  flex-shrink: 0;
}

.icon-wrapper {
  width: 60rpx;
  height: 60rpx;
  border-radius: 12rpx;
  display: flex;
  align-items: center;
  justify-content: center;

  &.system { background: rgba(74, 144, 226, 0.15); }
  &.price { background: rgba(82, 196, 26, 0.15); }
  &.selection { background: rgba(250, 173, 20, 0.15); }
  &.advisor { background: rgba(255, 77, 79, 0.15); }
  &.trade { background: rgba(153, 153, 153, 0.15); }
}

.icon-text {
  font-size: 22rpx;
  font-weight: 700;
  color: $text-primary;
}

.item-main {
  flex: 1;
  min-width: 0;
}

.item-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 8rpx;
}

.item-title {
  font-size: $font-size-base;
  font-weight: 600;
  color: $text-primary;
  flex: 1;
  margin-right: 16rpx;
}

.item-time {
  font-size: $font-size-xs;
  color: $text-hint;
  flex-shrink: 0;
}

.item-content {
  font-size: $font-size-sm;
  color: $text-secondary;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  word-break: break-all;
}

.unread-dot {
  position: absolute;
  top: 28rpx;
  right: 0;
  width: 12rpx;
  height: 12rpx;
  border-radius: 50%;
  background: $color-primary;
}

.loading-more {
  padding: 32rpx 0;
  text-align: center;
  font-size: $font-size-sm;
  color: $text-hint;
}

.no-more {
  color: $text-hint;
  opacity: 0.5;
}
</style>
