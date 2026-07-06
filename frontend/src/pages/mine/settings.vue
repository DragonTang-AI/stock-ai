<template>
  <view class="settings-page">
    <!-- 偏好设置 -->
    <view class="section">
      <view class="section-title">偏好设置</view>
      <view class="menu-list">
        <view class="menu-item">
          <text class="menu-label">深色模式</text>
          <switch
            :checked="darkMode"
            color="#4A90E2"
            @change="toggleDarkMode"
          />
        </view>
        <view class="menu-item">
          <text class="menu-label">行情自动刷新</text>
          <switch
            :checked="autoRefresh"
            color="#4A90E2"
            @change="toggleAutoRefresh"
          />
        </view>
      </view>
    </view>

    <!-- 通知设置 -->
    <view class="section">
      <view class="section-title">通知设置</view>
      <view class="menu-list">
        <view class="menu-item">
          <text class="menu-label">价格提醒</text>
          <switch
            :checked="notifyPrice"
            color="#4A90E2"
            @change="toggleNotifyPrice"
          />
        </view>
        <view class="menu-item">
          <text class="menu-label">选股结果通知</text>
          <switch
            :checked="notifySelection"
            color="#4A90E2"
            @change="toggleNotifySelection"
          />
        </view>
        <view class="menu-item">
          <text class="menu-label">AI 分析推送</text>
          <switch
            :checked="notifyAI"
            color="#4A90E2"
            @change="toggleNotifyAI"
          />
        </view>
      </view>
    </view>

    <!-- 数据管理 -->
    <view class="section">
      <view class="section-title">数据管理</view>
      <view class="menu-list">
        <view class="menu-item" @click="handleClearCache">
          <text class="menu-label">清除缓存</text>
          <view class="menu-right">
            <text class="menu-value">{{ cacheSize }}</text>
            <text class="menu-arrow">›</text>
          </view>
        </view>
        <view class="menu-item" @click="handleExportData">
          <text class="menu-label">导出数据</text>
          <text class="menu-arrow">›</text>
        </view>
      </view>
    </view>

    <!-- 关于 -->
    <view class="section">
      <view class="section-title">关于</view>
      <view class="menu-list">
        <view class="menu-item" @click="showToast('当前版本 v0.1.0')">
          <text class="menu-label">版本更新</text>
          <view class="menu-right">
            <text class="menu-value">v0.1.0</text>
            <text class="menu-arrow">›</text>
          </view>
        </view>
        <view class="menu-item" @click="showToast('使用帮助开发中')">
          <text class="menu-label">使用帮助</text>
          <text class="menu-arrow">›</text>
        </view>
        <view class="menu-item" @click="showToast('隐私政策开发中')">
          <text class="menu-label">隐私政策</text>
          <text class="menu-arrow">›</text>
        </view>
        <view class="menu-item" @click="showToast('用户协议暂无')">
          <text class="menu-label">用户协议</text>
          <text class="menu-arrow">›</text>
        </view>
      </view>
    </view>

    <!-- 风险提示 -->
    <view class="disclaimer">
      <text>AI-Stock 为模拟交易工具。所有数据仅供参考，不构成投资建议。市场有风险，投资需谨慎。</text>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getThemeState, setThemeMode, type ThemeMode } from '@/utils/theme'

const darkMode = ref(false)
const autoRefresh = ref(true)
const notifyPrice = ref(false)
const notifySelection = ref(false)
const notifyAI = ref(false)
const cacheSize = ref('0 KB')

const SETTINGS_KEY = 'ai-stock:settings'

interface AppSettings {
  darkMode: boolean
  autoRefresh: boolean
  notifyPrice: boolean
  notifySelection: boolean
  notifyAI: boolean
}

function loadSettings() {
  // 加载主题状态
  const theme = getThemeState()
  darkMode.value = theme.isDark

  try {
    const raw = uni.getStorageSync(SETTINGS_KEY)
    if (raw) {
      const s: AppSettings = JSON.parse(raw)
      autoRefresh.value = s.autoRefresh ?? true
      notifyPrice.value = s.notifyPrice ?? false
      notifySelection.value = s.notifySelection ?? false
      notifyAI.value = s.notifyAI ?? false
    }
  } catch { /* ignore */ }
}

function saveSettings() {
  const s: AppSettings = {
    darkMode: darkMode.value,
    autoRefresh: autoRefresh.value,
    notifyPrice: notifyPrice.value,
    notifySelection: notifySelection.value,
    notifyAI: notifyAI.value,
  }
  uni.setStorageSync(SETTINGS_KEY, JSON.stringify(s))
}

function toggleDarkMode(e: { detail: { value: boolean } }) {
  const newValue = e.detail.value
  darkMode.value = newValue
  setThemeMode(newValue ? 'dark' : 'light')
  saveSettings()
}

function toggleAutoRefresh(e: { detail: { value: boolean } }) {
  autoRefresh.value = e.detail.value
  saveSettings()
}

function toggleNotifyPrice(e: { detail: { value: boolean } }) {
  notifyPrice.value = e.detail.value
  saveSettings()
}

function toggleNotifySelection(e: { detail: { value: boolean } }) {
  notifySelection.value = e.detail.value
  saveSettings()
}

function toggleNotifyAI(e: { detail: { value: boolean } }) {
  notifyAI.value = e.detail.value
  saveSettings()
}

function getCacheSize() {
  try {
    const res = uni.getStorageInfoSync()
    // #ifdef H5
    // localStorage estimate
    let total = 0
    for (const key in localStorage) {
      if (key.indexOf('ai-stock') >= 0 || key.indexOf('uni') >= 0) {
        total += localStorage.getItem(key)?.length ?? 0
      }
    }
    if (total > 1024 * 1024) {
      cacheSize.value = (total / (1024 * 1024)).toFixed(1) + ' MB'
    } else if (total > 1024) {
      cacheSize.value = (total / 1024).toFixed(1) + ' KB'
    } else {
      cacheSize.value = total + ' B'
    }
    // #endif
    // #ifndef H5
    cacheSize.value = res.currentSize > 1024
      ? (res.currentSize / 1024).toFixed(1) + ' KB'
      : res.currentSize + ' KB'
    // #endif
  } catch {
    cacheSize.value = '计算中...'
  }
}

function handleClearCache() {
  uni.showModal({
    title: '清除缓存',
    content: '将清除所有本地缓存数据（不包含账号信息），确定继续？',
    success: (res: { confirm: boolean }) => {
      if (res.confirm) {
        // 保留 auth token 和 settings
        const token = uni.getStorageSync('token')
        const userInfo = uni.getStorageSync('userInfo')
        const settings = uni.getStorageSync(SETTINGS_KEY)
        uni.clearStorageSync()
        if (token) uni.setStorageSync('token', token)
        if (userInfo) uni.setStorageSync('userInfo', userInfo)
        if (settings) uni.setStorageSync(SETTINGS_KEY, settings)
        getCacheSize()
        uni.showToast({ title: '缓存已清除', icon: 'success' })
      }
    },
  })
}

function handleExportData() {
  uni.showToast({ title: '导出功能开发中', icon: 'none' })
}

function showToast(msg: string) {
  uni.showToast({ title: msg, icon: 'none' })
}

onMounted(() => {
  loadSettings()
  getCacheSize()
})
</script>

<style lang="scss" scoped>
.settings-page {
  min-height: 100vh;
  background: $bg-page;
  padding-bottom: env(safe-area-inset-bottom);
}

.section {
  margin: 24rpx 24rpx 0;
}

.section-title {
  font-size: $font-size-sm;
  color: $text-hint;
  padding: 0 8rpx 16rpx;
}

.menu-list {
  background: $bg-card;
  border-radius: $border-radius;
  overflow: hidden;
}

.menu-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 28rpx 28rpx;
  border-bottom: 1rpx solid $border-color;

  &:last-child {
    border-bottom: none;
  }

  &:active {
    background: rgba(0, 0, 0, 0.03);
  }
}

.menu-label {
  font-size: $font-size-base;
  color: $text-primary;
  flex-shrink: 0;
}

.menu-right {
  display: flex;
  align-items: center;
  gap: 12rpx;
}

.menu-value {
  font-size: $font-size-sm;
  color: $text-hint;
}

.menu-arrow {
  font-size: $font-size-xl;
  color: $text-hint;
}

.disclaimer {
  padding: 48rpx 48rpx 32rpx;
  text-align: center;

  text {
    font-size: $font-size-xs;
    color: $text-hint;
    line-height: 1.6;
  }
}
</style>
