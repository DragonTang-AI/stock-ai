<template>
  <view class="register-page">
    <view class="register-card">
      <view class="register-header">
        <text class="app-name">AI-Stock</text>
        <text class="app-desc">创建您的账号</text>
      </view>

      <view class="register-form">
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
          <text class="input-label">邮箱</text>
          <input
            v-model="email"
            class="input-field"
            placeholder="请输入邮箱"
            placeholder-style="color:#bbb"
          />
        </view>
        <view class="input-group">
          <text class="input-label">密码</text>
          <input
            v-model="password"
            class="input-field"
            type="password"
            placeholder="请输入密码（至少6位）"
            placeholder-style="color:#bbb"
          />
        </view>

        <button
          class="btn-register"
          :disabled="loading"
          @click="handleRegister"
        >
          {{ loading ? '注册中...' : '注册' }}
        </button>

        <view class="register-extra">
          <text class="extra-link" @click="goLogin">已有账号？去登录</text>
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
import { register } from '@/api/auth'
import Disclaimer from '@/components/compliance/Disclaimer.vue'

const authStore = useAuthStore()
const username = ref('')
const email = ref('')
const password = ref('')
const loading = ref(false)
const errorMsg = ref('')

async function handleRegister() {
  errorMsg.value = ''

  if (!username.value.trim()) {
    errorMsg.value = '请输入用户名'
    return
  }
  if (!email.value.trim()) {
    errorMsg.value = '请输入邮箱'
    return
  }
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.value.trim())) {
    errorMsg.value = '邮箱格式不正确'
    return
  }
  if (!password.value) {
    errorMsg.value = '请输入密码'
    return
  }
  if (password.value.length < 6) {
    errorMsg.value = '密码至少 6 位'
    return
  }

  loading.value = true

  try {
    const res = await register({
      username: username.value.trim(),
      email: email.value.trim(),
      password: password.value,
    })

    authStore.setAuth(res.access_token, res.refresh_token)
    if (res.user) {
      authStore.setUserInfo(res.user)
    }

    uni.showToast({ title: '注册成功', icon: 'success', duration: 1500 })
    setTimeout(() => {
      uni.switchTab({ url: '/pages/market/index' })
    }, 800)
  } catch (e: any) {
    const detail = e?.detail || e?.message || ''
    if (detail.includes('已被注册') || detail.includes('already')) {
      errorMsg.value = '用户名或邮箱已被注册'
    } else if (e?.statusCode === 422) {
      errorMsg.value = '输入格式不正确，请检查后重试'
    } else {
      errorMsg.value = detail || '注册失败，请检查网络连接'
    }
  } finally {
    loading.value = false
  }
}

function goLogin() {
  uni.navigateBack()
}
</script>

<style scoped lang="scss">
.register-page {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  padding: 48rpx 32rpx;
  background: linear-gradient(135deg, #1A1A2E 0%, #16213E 100%);
}

.register-card {
  width: 100%;
  max-width: 600rpx;
  background: #fff;
  border-radius: 24rpx;
  padding: 64rpx 48rpx 48rpx;
}

.register-header {
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

.register-form {
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

.btn-register {
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

.register-extra {
  display: flex;
  justify-content: center;
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
