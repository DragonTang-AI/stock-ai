<template>
  <view class="feedback-page">
    <view class="page-header">
      <text class="page-title">用户反馈</text>
      <text class="page-subtitle">您的反馈是我们改进的动力</text>
    </view>

    <!-- 反馈类型 -->
    <view class="section">
      <view class="section-title">反馈类型</view>
      <view class="type-grid">
        <view
          v-for="item in feedbackTypes"
          :key="item.value"
          class="type-item"
          :class="{ active: formData.type === item.value }"
          @click="formData.type = item.value"
        >
          <text class="type-icon">{{ item.icon }}</text>
          <text class="type-label">{{ item.label }}</text>
        </view>
      </view>
    </view>

    <!-- 问题描述 -->
    <view class="section">
      <view class="section-title">问题描述</view>
      <textarea
        class="desc-input"
        v-model="formData.description"
        placeholder="请详细描述您遇到的问题或建议..."
        :maxlength="500"
        :auto-height="true"
        :adjust-position="true"
        :cursor-spacing="20"
      />
      <view class="char-count">{{ formData.description.length }}/500</view>
    </view>

    <!-- 联系方式（可选） -->
    <view class="section">
      <view class="section-title">联系方式（选填）</view>
      <input
        class="contact-input"
        v-model="formData.contact"
        placeholder="手机号或邮箱，方便我们联系您"
        :adjust-position="true"
        :cursor-spacing="20"
      />
    </view>

    <!-- 提交按钮 -->
    <button
      class="btn-submit"
      :class="{ disabled: !canSubmit || submitting }"
      :disabled="!canSubmit || submitting"
      @click="handleSubmit"
    >
      {{ submitting ? '提交中...' : '提交反馈' }}
    </button>

    <!-- 提交成功 -->
    <view v-if="submitSuccess" class="success-card">
      <text class="success-icon">&#10003;</text>
      <text class="success-text">感谢您的反馈，我们会尽快处理！</text>
    </view>
  </view>
  <Disclaimer />
</template>

<script setup lang="ts">
import Disclaimer from '@/components/compliance/Disclaimer.vue'
import { ref, reactive, computed } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { trackPageView, trackAction } from '@/utils/tracker'

const feedbackTypes = [
  { value: 'bug', label: 'Bug 反馈', icon: '🐛' },
  { value: 'feature', label: '功能建议', icon: '💡' },
  { value: 'experience', label: '体验问题', icon: '🎨' },
  { value: 'data', label: '数据问题', icon: '📊' },
  { value: 'other', label: '其他', icon: '💬' },
]

const formData = reactive({
  type: 'bug',
  description: '',
  contact: '',
})

const submitting = ref(false)
const submitSuccess = ref(false)

const canSubmit = computed(() => {
  return formData.type && formData.description.trim().length >= 10
})

async function handleSubmit() {
  if (!canSubmit.value || submitting.value) return

  submitting.value = true
  try {
    await uni.request({
      url: '/api/v1/feedback',
      method: 'POST',
      header: { 'Content-Type': 'application/json' },
      data: {
        type: formData.type,
        description: formData.description.trim(),
        contact: formData.contact.trim() || undefined,
      },
    })

    trackAction('submit_feedback', {
      type: formData.type,
      description_length: formData.description.trim().length,
    })

    submitSuccess.value = true
    formData.description = ''
    formData.contact = ''

    uni.showToast({ title: '提交成功', icon: 'success' })
  } catch (err: any) {
    uni.showToast({
      title: err?.message || '提交失败，请稍后重试',
      icon: 'none',
    })
  } finally {
    submitting.value = false
  }
}

onShow(() => {
  trackPageView('feedback')
})
</script>

<style lang="scss" scoped>
.feedback-page {
  min-height: 100vh;
  background: var(--bg-page, #F5F5F7);
  padding: 24rpx 24rpx calc(env(safe-area-inset-bottom) + 48rpx);
}

.page-header {
  padding: 16rpx 0 32rpx;
  display: flex;
  flex-direction: column;
  gap: 8rpx;
}

.page-title {
  font-size: 40rpx;
  font-weight: 700;
  color: var(--text-primary, #1A1A2E);
}

.page-subtitle {
  font-size: 26rpx;
  color: var(--text-hint, #999);
}

.section {
  margin-bottom: 32rpx;
}

.section-title {
  font-size: 28rpx;
  font-weight: 600;
  color: var(--text-primary, #1A1A2E);
  margin-bottom: 16rpx;
}

.type-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 16rpx;
}

.type-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 180rpx;
  height: 140rpx;
  background: var(--bg-card, #fff);
  border-radius: 16rpx;
  border: 2rpx solid transparent;
  gap: 12rpx;
  transition: all 0.2s;

  &.active {
    border-color: #4A90E2;
    background: rgba(74, 144, 226, 0.06);
  }
}

.type-icon {
  font-size: 40rpx;
}

.type-label {
  font-size: 24rpx;
  color: var(--text-secondary, #666);
}

.desc-input {
  width: 100%;
  min-height: 240rpx;
  padding: 24rpx;
  background: var(--bg-card, #fff);
  border-radius: 16rpx;
  font-size: 28rpx;
  color: var(--text-primary, #1A1A2E);
  box-sizing: border-box;
}

.char-count {
  text-align: right;
  font-size: 22rpx;
  color: var(--text-hint, #999);
  margin-top: 8rpx;
  padding-right: 8rpx;
}

.contact-input {
  width: 100%;
  height: 88rpx;
  padding: 0 24rpx;
  background: var(--bg-card, #fff);
  border-radius: 16rpx;
  font-size: 28rpx;
  color: var(--text-primary, #1A1A2E);
  box-sizing: border-box;
}

.btn-submit {
  width: 100%;
  height: 96rpx;
  line-height: 96rpx;
  background: linear-gradient(135deg, #4A90E2, #357ABD);
  color: #fff;
  font-size: 32rpx;
  font-weight: 600;
  border-radius: 48rpx;
  border: none;
  margin-top: 32rpx;
  transition: opacity 0.2s;

  &::after { border: none; }

  &.disabled {
    opacity: 0.5;
  }

  &:active {
    opacity: 0.8;
  }
}

.success-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48rpx;
  background: var(--bg-card, #fff);
  border-radius: 16rpx;
  margin-top: 32rpx;
  gap: 16rpx;
}

.success-icon {
  width: 80rpx;
  height: 80rpx;
  line-height: 80rpx;
  text-align: center;
  background: #52c41a;
  color: #fff;
  font-size: 40rpx;
  border-radius: 50%;
}

.success-text {
  font-size: 28rpx;
  color: var(--text-secondary, #666);
}
</style>
