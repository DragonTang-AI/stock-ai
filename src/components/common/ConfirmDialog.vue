<template>
  <view v-if="visible" class="confirm-overlay" @click.self="handleCancel">
    <view class="confirm-dialog slide-up">
      <!-- 标题 -->
      <view class="dialog-header">
        <text class="dialog-title">{{ title }}</text>
        <text class="dialog-close" @click="handleCancel">✕</text>
      </view>

      <!-- 内容区域 -->
      <view class="dialog-body">
        <!-- 危险操作警告 -->
        <view v-if="danger" class="danger-banner">
          <text class="danger-icon">⚠️</text>
          <text class="danger-text">{{ dangerMessage }}</text>
        </view>

        <!-- 自定义内容 -->
        <slot>
          <text class="dialog-message">{{ message }}</text>
        </slot>

        <!-- 影响描述 -->
        <view v-if="impact" class="impact-box">
          <text class="impact-label">操作影响：</text>
          <text class="impact-text">{{ impact }}</text>
        </view>
      </view>

      <!-- 操作按钮 -->
      <view class="dialog-actions" :class="{ reversed: danger }">
        <button class="btn-cancel" @click="handleCancel">{{ cancelText }}</button>
        <button
          class="btn-confirm"
          :class="{ danger: danger }"
          @click="handleConfirm"
        >{{ confirmText }}</button>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  visible: boolean
  title?: string
  message?: string
  /** 是否为危险操作（删除、清仓等） */
  danger?: boolean
  /** 操作影响描述 */
  impact?: string
  confirmText?: string
  cancelText?: string
}>()

const emit = defineEmits<{
  (e: 'confirm'): void
  (e: 'cancel'): void
}>()

const dangerMessage = computed(() => {
  return props.title ? `此操作将${props.title}，请谨慎确认。` : '此操作不可撤销，请谨慎确认。'
})

function handleConfirm() {
  emit('confirm')
}

function handleCancel() {
  emit('cancel')
}
</script>

<style lang="scss" scoped>
.confirm-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 48rpx;
}

.confirm-dialog {
  width: 100%;
  max-width: 600rpx;
  background: $bg-card;
  border-radius: 24rpx;
  padding: 36rpx 32rpx 24rpx;
  max-height: 80vh;
  overflow-y: auto;
}

.slide-up {
  animation: scaleIn 0.2s ease-out both;
}

@keyframes scaleIn {
  from {
    opacity: 0;
    transform: scale(0.9);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

// ─── 标题 ───
.dialog-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24rpx;
}

.dialog-title {
  font-size: $font-size-lg;
  font-weight: 700;
  color: $text-primary;
}

.dialog-close {
  font-size: 36rpx;
  color: $text-hint;
  padding: 8rpx 16rpx;
}

// ─── 内容 ───
.dialog-body {
  margin-bottom: 28rpx;
}

.dialog-message {
  font-size: $font-size-base;
  color: $text-secondary;
  line-height: 1.6;
}

.danger-banner {
  display: flex;
  align-items: flex-start;
  gap: 12rpx;
  background: rgba(244, 67, 54, 0.08);
  border-radius: 8rpx;
  padding: 16rpx 20rpx;
  margin-bottom: 20rpx;
}

.danger-icon {
  font-size: 32rpx;
  flex-shrink: 0;
}

.danger-text {
  font-size: $font-size-sm;
  color: $color-danger;
  line-height: 1.6;
}

.impact-box {
  background: rgba(0, 0, 0, 0.02);
  border-radius: 8rpx;
  padding: 16rpx 20rpx;
  margin-top: 16rpx;
}

.impact-label {
  font-size: $font-size-xs;
  font-weight: 600;
  color: $text-hint;
  display: block;
  margin-bottom: 8rpx;
}

.impact-text {
  font-size: $font-size-sm;
  color: $text-secondary;
  line-height: 1.5;
}

// ─── 按钮 ───
.dialog-actions {
  display: flex;
  gap: 20rpx;

  &.reversed {
    flex-direction: row-reverse;
  }
}

.btn-cancel {
  flex: 1;
  padding: 22rpx 0;
  font-size: $font-size-base;
  color: $text-secondary;
  background: rgba(0, 0, 0, 0.04);
  border-radius: 12rpx;
  border: none;
  text-align: center;

  &::after {
    border: none;
  }
}

.btn-confirm {
  flex: 1.5;
  padding: 22rpx 0;
  font-size: $font-size-base;
  font-weight: 700;
  color: #fff;
  border-radius: 12rpx;
  border: none;
  text-align: center;
  background: var(--color-primary, #4A90E2);

  &.danger {
    background: linear-gradient(135deg, #EF5350, #E53935);
  }

  &::after {
    border: none;
  }
}
</style>
