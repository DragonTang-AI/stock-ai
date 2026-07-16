<template>
  <view class="mine-page">
    <!-- 用户信息卡片 -->
    <view class="user-card">
      <view class="user-info">
        <view class="avatar-wrapper">
          <text class="avatar-text">{{ avatarText }}</text>
        </view>
        <view class="user-meta">
          <text class="username">{{ userInfo?.username || '未登录' }}</text>
          <text v-if="userInfo?.email" class="user-email">{{ userInfo.email }}</text>
          <text class="account-badge">{{ userInfo?.account_type || 'PAPER' }}</text>
        </view>
      </view>
    </view>

    <!-- 账户功能 -->
    <view class="section">
      <view class="menu-list">
        <view class="menu-item" @click="navigateTo('/pages/mine/notifications')">
          <text class="menu-icon">🔔</text>
          <text class="menu-label">消息中心</text>
          <view class="menu-badge" v-if="unreadCount > 0">{{ unreadCount > 99 ? '99+' : unreadCount }}</view>
          <text class="menu-arrow">›</text>
        </view>
        <view class="menu-item" @click="navigateTo('/pages/watchlist/index')">
          <text class="menu-icon">⭐</text>
          <text class="menu-label">自选股</text>
          <text class="menu-arrow">›</text>
        </view>
      </view>
    </view>

    <!-- 看板 -->
    <view class="section">
      <view class="menu-list">
        <view class="menu-item" @click="navigateTo('/pages/hosted/index')">
          <text class="menu-icon">🤖</text>
          <text class="menu-label">AI托管</text>
          <text class="menu-arrow">›</text>
        </view>
        <view class="menu-item" @click="navigateTo('/pages/portfolio/analytics')">
          <text class="menu-icon">📊</text>
          <text class="menu-label">持仓分析</text>
          <text class="menu-arrow">›</text>
        </view>
        <view class="menu-item" @click="navigateTo('/pages/mine/settings')">
          <text class="menu-icon">⚙️</text>
          <text class="menu-label">设置</text>
          <text class="menu-arrow">›</text>
        </view>
      </view>
    </view>

    <!-- 退出登录 -->
    <view class="section">
      <button
        class="btn-logout"
        :disabled="!authStore.isLoggedIn"
        @click="handleLogout"
      >
        退出登录
      </button>
    </view>

    <!-- 版本信息 -->
    <view class="version-info">
      <text>AI-Stock v0.1.0</text>
      <text class="disclaimer-mini">模拟收益仅供参考，不构成投资建议</text>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { useAuthStore } from '@/stores/auth'
import { getCurrentUser } from '@/api/auth'
import { fetchNotifications } from '@/api/notifications'

const authStore = useAuthStore()

const unreadCount = ref(0)

const userInfo = computed(() => authStore.userInfo)
const avatarText = computed(() => {
  const name = userInfo.value?.username || '游'
  return name.slice(0, 1).toUpperCase()
})

/** 页面加载时 / 每次可见时拉取最新用户信息 */
async function fetchUserInfo() {
  if (!authStore.isLoggedIn) return
  try {
    const me = await getCurrentUser()
    authStore.userInfo = me
    uni.setStorageSync('userInfo', JSON.stringify(me))
  } catch {
    // 忽略网络错误，显示缓存数据
  }
}

onMounted(() => {
  fetchUserInfo()
  fetchUnreadCount()
})

// uni-app 页面生命周期
onShow(() => {
  fetchUserInfo()
  fetchUnreadCount()
})

async function fetchUnreadCount() {
  try {
    const res = await fetchNotifications({ limit: 1, offset: 0 })
    unreadCount.value = res.unread_count
  } catch {
    // 静默失败
  }
}

function navigateTo(url: string) {
  uni.navigateTo({ url })
}

function showToast(msg: string) {
  uni.showToast({ title: msg, icon: 'none' })
}

async function handleLogout() {
  await authStore.logout()
  uni.reLaunch({ url: '/pages/login/index' })
}
</script>

<style lang="scss" scoped>
.mine-page {
  min-height: 100vh;
  background: $bg-page;
  padding-bottom: env(safe-area-inset-bottom);
}

.user-card {
  background: linear-gradient(135deg, $bg-primary 0%, $bg-secondary 100%);
  padding: 48rpx 32rpx 40rpx;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 24rpx;
}

.avatar-wrapper {
  width: 100rpx;
  height: 100rpx;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
}

.avatar-text {
  font-size: 44rpx;
  font-weight: 700;
  color: $text-inverse;
}

.user-meta {
  display: flex;
  flex-direction: column;
  gap: 8rpx;
}

.username {
  font-size: $font-size-xl;
  font-weight: 600;
  color: $text-inverse;
}

.user-email {
  font-size: $font-size-xs;
  color: rgba(255, 255, 255, 0.6);
  margin-top: 4rpx;
}

.account-badge {
  display: inline-block;
  font-size: 22rpx;
  padding: 4rpx 12rpx;
  border-radius: 8rpx;
  background: rgba(74, 144, 226, 0.4);
  color: $text-inverse;
  width: fit-content;
}

.section {
  margin: 24rpx;
}

.menu-list {
  background: $bg-card;
  border-radius: $border-radius;
  overflow: hidden;
}

.menu-item {
  display: flex;
  align-items: center;
  padding: 28rpx 28rpx;
  border-bottom: 1rpx solid $border-color;
  cursor: pointer;

  &:last-child {
    border-bottom: none;
  }

  &:active {
    background: rgba(0, 0, 0, 0.03);
  }
}

.menu-icon {
  font-size: 40rpx;
  margin-right: 20rpx;
}

.menu-label {
  flex: 1;
  font-size: $font-size-base;
  color: $text-primary;
}

.menu-arrow {
  font-size: $font-size-xl;
  color: $text-hint;
}

.menu-badge {
  background: $color-danger;
  color: $text-inverse;
  font-size: 20rpx;
  padding: 2rpx 10rpx;
  border-radius: 20rpx;
  margin-right: 12rpx;
  line-height: 1.4;
  min-width: 32rpx;
  text-align: center;
}

.btn-logout {
  width: 100%;
  background: $bg-card;
  color: $color-danger;
  font-size: $font-size-base;
  padding: 28rpx;
  border-radius: $border-radius;
  border: none;

  &::after { border: none; }

  &[disabled] {
    color: $text-hint;
  }
}

.version-info {
  text-align: center;
  padding: 32rpx 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8rpx;
}

.disclaimer-mini {
  font-size: $font-size-xs;
  color: $text-hint;
}
</style>
