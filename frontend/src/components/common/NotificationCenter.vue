<template>
  <view class="notification-center">
    <!-- 标题栏 -->
    <view class="header">
      <text class="title">消息中心</text>
      <view class="header-actions">
        <view class="action-btn" @click="markAllAsRead">
          <text class="action-text">全部已读</text>
        </view>
        <view class="action-btn" @click="clearAll">
          <text class="action-text">清空</text>
        </view>
      </view>
    </view>

    <!-- 空状态 -->
    <view v-if="notifications.length === 0" class="empty-state">
      <text class="empty-icon">📭</text>
      <text class="empty-text">暂无新消息</text>
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
            <text class="item-time">{{ formatTime(item.time) }}</text>
          </view>
          <text class="item-content">{{ item.content }}</text>
          <view v-if="item.action" class="item-actions">
            <button
              v-for="(action, idx) in item.action"
              :key="idx"
              class="action-btn-small"
              @click.stop="handleAction(item, action)"
            >
              {{ action.label }}
            </button>
          </view>
        </view>
        <view v-if="!item.read" class="unread-dot"></view>
      </view>
      <view v-if="loading" class="loading-more">
        <text>加载中...</text>
      </view>
    </scroll-view>
  </view>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'

interface NotificationAction {
  label: string
  value: string
  url?: string
  callback?: () => void
}

interface NotificationItem {
  id: string
  type: 'system' | 'price' | 'selection' | 'advisor' | 'trade'
  title: string
  content: string
  time: number // timestamp
  read: boolean
  action?: NotificationAction[]
  data?: Record<string, any>
}

const notifications = ref<NotificationItem[]>([
  {
    id: '1',
    type: 'system',
    title: '系统更新',
    content: 'AI-Stock v0.1.0 已发布，新增设置页面和通知中心。',
    time: Date.now() - 3600000 * 2,
    read: true,
  },
  {
    id: '2',
    type: 'price',
    title: '价格提醒',
    content: '贵州茅台(600519) 已跌破 1600 元，当前 1589.50 元。',
    time: Date.now() - 1800000,
    read: false,
    action: [
      { label: '查看', value: 'view', url: '/pages/detail/index?code=600519' },
    ],
  },
  {
    id: '3',
    type: 'selection',
    title: '选股结果',
    content: '今日选股策略「高成长低估值」已生成 5 只推荐股票。',
    time: Date.now() - 600000,
    read: false,
    action: [
      { label: '查看', value: 'view', url: '/pages/selection/index' },
    ],
  },
  {
    id: '4',
    type: 'advisor',
    title: 'AI 分析',
    content: 'AI 助手已为您分析持仓组合，建议关注新能源板块。',
    time: Date.now() - 300000,
    read: false,
    action: [
      { label: '查看', value: 'view', url: '/pages/advisor/index' },
    ],
  },
])

const loading = ref(false)
const hasMore = ref(true)

function formatTime(timestamp: number): string {
  const now = Date.now()
  const diff = now - timestamp
  const minute = 60000
  const hour = minute * 60
  const day = hour * 24

  if (diff < minute) return '刚刚'
  if (diff < hour) return Math.floor(diff / minute) + '分钟前'
  if (diff < day) return Math.floor(diff / hour) + '小时前'
  if (diff < day * 7) return Math.floor(diff / day) + '天前'
  return new Date(timestamp).toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}

function getIcon(type: NotificationItem['type']): string {
  const map = {
    system: '📢',
    price: '💰',
    selection: '📈',
    advisor: '🤖',
    trade: '📊',
  }
  return map[type] || '📨'
}

function handleClick(item: NotificationItem) {
  if (!item.read) {
    item.read = true
    // 实际场景可调用 API 标记已读
  }
  // 默认跳转逻辑
  if (item.type === 'price' && item.data?.code) {
    uni.navigateTo({ url: `/pages/detail/index?code=${item.data.code}` })
  } else if (item.type === 'selection') {
    uni.navigateTo({ url: '/pages/selection/index' })
  } else if (item.type === 'advisor') {
    uni.navigateTo({ url: '/pages/advisor/index' })
  }
}

function handleAction(item: NotificationItem, action: NotificationAction) {
  if (action.callback) {
    action.callback()
  } else if (action.url) {
    uni.navigateTo({ url: action.url })
  }
  if (!item.read) item.read = true
}

function markAllAsRead() {
  notifications.value.forEach(item => { item.read = true })
  uni.showToast({ title: '全部标记为已读', icon: 'success' })
}

function clearAll() {
  uni.showModal({
    title: '清空消息',
    content: '确定清空所有消息？',
    success: (res: { confirm: boolean }) => {
      if (res.confirm) {
        notifications.value = []
        uni.showToast({ title: '已清空', icon: 'success' })
      }
    },
  })
}

function loadMore() {
  if (loading.value || !hasMore.value) return
  // 模拟加载更多
  loading.value = true
  setTimeout(() => {
    const newItems: NotificationItem[] = [
      {
        id: '5',
        type: 'trade',
        title: '交易提醒',
        content: '您的限价单 600036 招商银行 已成交，成交价 32.15 元。',
        time: Date.now() - 86400000 * 2,
        read: true,
      },
      {
        id: '6',
        type: 'system',
        title: '系统维护',
        content: '本周六凌晨 2:00-4:00 进行系统维护，期间可能无法访问。',
        time: Date.now() - 86400000 * 3,
        read: true,
      },
    ]
    notifications.value.push(...newItems)
    hasMore.value = false
    loading.value = false
  }, 800)
}

onMounted(() => {
  // 可在此处从 API 拉取真实通知
})
</script>

<style lang="scss" scoped>
.notification-center {
  min-height: 100vh;
  background: $bg-page;
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

.empty-state {
  padding: 120rpx 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.empty-icon {
  font-size: 80rpx;
  margin-bottom: 24rpx;
  opacity: 0.4;
}

.empty-text {
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

  &.system { background: rgba(74, 144, 226, 0.1); }
  &.price { background: rgba(82, 196, 26, 0.1); }
  &.selection { background: rgba(250, 173, 20, 0.1); }
  &.advisor { background: rgba(255, 77, 79, 0.1); }
  &.trade { background: rgba(153, 153, 153, 0.1); }
}

.icon-text {
  font-size: 32rpx;
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

.item-actions {
  margin-top: 16rpx;
  display: flex;
  gap: 12rpx;
}

.action-btn-small {
  padding: 8rpx 20rpx;
  font-size: $font-size-xs;
  color: $color-primary;
  background: rgba(74, 144, 226, 0.1);
  border-radius: 6rpx;
  border: none;
  line-height: 1;

  &::after { border: none; }
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
</style>
