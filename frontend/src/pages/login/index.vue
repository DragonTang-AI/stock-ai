<template>
  <view class="login-page">
    <view class="login-card">
      <view class="login-header">
        <text class="app-name">AI-Stock</text>
        <text class="app-desc">智能选股助手</text>
      </view>

      <view class="login-form">
        <view class="input-group">
          <text class="input-label">用户名</text>
          <input
            v-model="username"
            class="input-field"
            placeholder="请输入用户名"
            placeholder-style="color:#bbb"
          />
        </view>
        <view class="input-group">
          <text class="input-label">密码</text>
          <input
            v-model="password"
            class="input-field"
            type="password"
            placeholder="请输入密码"
            placeholder-style="color:#bbb"
          />
        </view>

        <button
          class="btn-login"
          :disabled="loading"
          @click="handleLogin"
        >
          {{ loading ? '登录中...' : '登录' }}
        </button>

        <view class="login-extra">
          <text class="extra-link" @click="goRegister">注册账号</text>
          <text class="extra-link" @click="goForgot">忘记密码</text>
        </view>
      </view>
    </view>

    <text class="error-msg" v-if="errorMsg">{{ errorMsg }}</text>

    <Disclaimer />
  </view>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useAuthStore } from '@/stores/auth'
import Disclaimer from '@/components/compliance/Disclaimer.vue'

const authStore = useAuthStore()
const username = ref('')
const password = ref('')
const loading = ref(false)
const errorMsg = ref('')

async function handleLogin() {
  if (!username.value || !password.value) {
    errorMsg.value = '请输入用户名和密码'
    return
  }

  loading.value = true
  errorMsg.value = ''

  try {
    // TODO: 对接后端登录 API
    uni.showToast({ title: '登录功能开发中', icon: 'none' })
  } catch (e: any) {
    errorMsg.value = e?.message || '登录失败，请重试'
  } finally {
    loading.value = false
  }
}

function goRegister() {
  uni.showToast({ title: '注册功能开发中', icon: 'none' })
}

function goForgot() {
  uni.showToast({ title: '找回密码功能开发中', icon: 'none' })
}
</script>

<style scoped lang="scss">
.login-page {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  padding: 48rpx 32rpx;
  background: linear-gradient(135deg, #1A1A2E 0%, #16213E 100%);
}

.login-card {
  width: 100%;
  max-width: 600rpx;
  background: #fff;
  border-radius: 24rpx;
  padding: 64rpx 48rpx 48rpx;
}

.login-header {
  text-align: center;
  margin-bottom: 64rpx;
}

.app-name {
  display: block;
  font-size: 48rpx;
  font-weight: 700;
  color: #1A1A2E;
  letter-spacing: 4rpx;
}

.app-desc {
  display: block;
  font-size: 24rpx;
  color: #999;
  margin-top: 12rpx;
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 32rpx;
}

.input-group {
  display: flex;
  flex-direction: column;
  gap: 12rpx;
}

.input-label {
  font-size: 26rpx;
  color: #333;
  font-weight: 500;
}

.input-field {
  height: 88rpx;
  padding: 0 24rpx;
  font-size: 30rpx;
  color: #333;
  border: 2rpx solid #e0e0e0;
  border-radius: 12rpx;
  background: #fafafa;

  &:focus {
    border-color: #4A90E2;
    background: #fff;
  }
}

.btn-login {
  width: 100%;
  height: 88rpx;
  line-height: 88rpx;
  font-size: 32rpx;
  color: #fff;
  background: linear-gradient(135deg, #4A90E2, #357ABD);
  border-radius: 12rpx;
  border: none;
  text-align: center;
  margin-top: 16rpx;

  &[disabled] {
    opacity: 0.6;
  }
}

.login-extra {
  display: flex;
  justify-content: space-between;
  padding: 0 8rpx;
}

.extra-link {
  font-size: 24rpx;
  color: #4A90E2;
}

.error-msg {
  margin-top: 32rpx;
  font-size: 24rpx;
  color: #ff4d4f;
  text-align: center;
}
</style>
