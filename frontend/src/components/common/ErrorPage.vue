<template>
  <view class="error-page">
    <view class="error-container">
      <!-- 错误图标 -->
      <view class="error-icon">
        <text class="icon-text" v-if="type === 'offline'">&#x1F4F6;</text>
        <text class="icon-text" v-else-if="type === '500'">&#x1F6A7;</text>
        <text class="icon-text" v-else-if="type === '404'">&#x1F50D;</text>
        <text class="icon-text" v-else-if="type === '403'">&#x1F512;</text>
        <text class="icon-text" v-else-if="type === 'empty'">&#x1F4ED;</text>
        <text class="icon-text" v-else>&#x26A0;&#xFE0F;</text>
      </view>

      <!-- 错误标题 -->
      <text class="error-title">{{ errorTitle }}</text>

      <!-- 错误描述 -->
      <text v-if="description" class="error-desc">{{ description }}</text>

      <!-- 错误详情（折叠） -->
      <view v-if="showDetail && detail" class="error-detail" @click="detailExpanded = !detailExpanded">
        <text class="detail-toggle">{{ detailExpanded ? '收起详情 ▲' : '展开详情 ▼' }}</text>
        <text v-if="detailExpanded" class="detail-text">{{ detail }}</text>
      </view>

      <!-- 操作按钮 -->
      <view class="error-actions">
        <!-- 离线模式 -->
        <button
          v-if="type === 'offline'"
          class="action-btn primary"
          @click="handleRetry"
        >重试连接</button>

        <!-- 服务器错误 -->
        <button
          v-if="type === '500'"
          class="action-btn primary"
          @click="handleRetry"
        >重试</button>
        <button
          v-if="type === '500'"
          class="action-btn secondary"
          @click="handleGoHome"
        >返回首页</button>

        <!-- 404 -->
        <button
          v-if="type === '404'"
          class="action-btn primary"
          @click="handleGoHome"
        >返回首页</button>

        <!-- 403 -->
        <button
          v-if="type === '403'"
          class="action-btn primary"
          @click="handleGoHome"
        >返回首页</button>

        <!-- 空数据 -->
        <button
          v-if="type === 'empty'"
          class="action-btn primary"
          @click="handleRetry"
        >重新加载</button>

        <!-- 通用 -->
        <button
          v-if="!['offline', '500', '404', '403', 'empty'].includes(type)"
          class="action-btn primary"
          @click="handleRetry"
        >重试</button>
        <button
          v-if="!['offline', '500', '404', '403', 'empty'].includes(type)"
          class="action-btn secondary"
          @click="handleGoHome"
        >返回首页</button>
      </view>

      <!-- 错误码 -->
      <text v-if="errorCode" class="error-code">错误码: {{ errorCode }}</text>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

const props = defineProps<{
  /** 错误类型 */
  type?: 'offline' | '500' | '404' | '403' | 'empty' | 'network' | 'general'
  /** 自定义标题 */
  title?: string
  /** 自定义描述 */
  description?: string
  /** 错误详情（技术信息） */
  detail?: string
  /** 错误码 */
  errorCode?: string
  /** 是否显示详情折叠 */
  showDetail?: boolean
}>()

const emit = defineEmits<{
  (e: 'retry'): void
  (e: 'go-home'): void
}>()

const detailExpanded = ref(false)

const errorTitleMap: Record<string, string> = {
  offline: '网络连接不可用',
  '500': '服务器开小差了',
  '404': '页面走丢了',
  '403': '暂无访问权限',
  empty: '暂无数据',
  network: '网络请求失败',
  general: '出了点问题',
}

const errorTitle = computed(() => {
  return props.title || errorTitleMap[props.type || 'general'] || '出了点问题'
})

function handleRetry() {
  emit('retry')
}

function handleGoHome() {
  emit('go-home')
  // 默认跳转到首页
  const pages = getCurrentPages()
  if (pages.length > 1) {
    uni.navigateBack()
  } else {
    uni.switchTab({ url: '/pages/index/index' })
  }
}
</script>

<style lang="scss" scoped>
.error-page {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  padding: 64rpx 48rpx;
  background: $bg-page;
}

.error-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  max-width: 560rpx;
  width: 100%;
}

.error-icon {
  width: 140rpx;
  height: 140rpx;
  background: rgba(0, 0, 0, 0.03);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 36rpx;
}

.icon-text {
  font-size: 64rpx;
}

.error-title {
  font-size: $font-size-lg;
  font-weight: 700;
  color: $text-primary;
  margin-bottom: 16rpx;
  text-align: center;
}

.error-desc {
  font-size: $font-size-sm;
  color: $text-secondary;
  text-align: center;
  line-height: 1.6;
  margin-bottom: 24rpx;
}

.error-detail {
  width: 100%;
  margin-bottom: 24rpx;
  padding: 16rpx 20rpx;
  background: rgba(0, 0, 0, 0.02);
  border-radius: 8rpx;
}

.detail-toggle {
  font-size: $font-size-xs;
  color: $color-primary;
}

.detail-text {
  display: block;
  margin-top: 12rpx;
  font-size: $font-size-xs;
  color: $text-hint;
  font-family: monospace;
  line-height: 1.5;
  word-break: break-all;
  white-space: pre-wrap;
}

.error-actions {
  display: flex;
  flex-direction: column;
  gap: 16rpx;
  width: 100%;
  max-width: 400rpx;
  margin-bottom: 24rpx;
}

.action-btn {
  width: 100%;
  padding: 22rpx 0;
  border-radius: 12rpx;
  font-size: $font-size-base;
  font-weight: 600;
  border: none;
  text-align: center;

  &.primary {
    background: var(--color-primary, #4A90E2);
    color: #fff;
  }

  &.secondary {
    background: rgba(0, 0, 0, 0.04);
    color: $text-secondary;
  }

  &::after {
    border: none;
  }
}

.error-code {
  font-size: 22rpx;
  color: $text-hint;
}
</style>
