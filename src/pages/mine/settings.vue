<template>
  <view class="settings-page">
    <!-- 偏好设置 -->
    <view class="section">
      <view class="section-title">偏好设置</view>
      <view class="menu-list">
        <!-- 主题模式 -->
        <view class="menu-item" @click="showThemePicker = true">
          <text class="menu-label">深色模式</text>
          <view class="menu-right">
            <text class="menu-value">{{ themeLabel }}</text>
            <text class="menu-arrow">›</text>
          </view>
        </view>
        <view class="menu-item" @click="showLangPicker = true">
          <text class="menu-label">语言</text>
          <view class="menu-right">
            <text class="menu-value">{{ langLabel }}</text>
            <text class="menu-arrow">›</text>
          </view>
        </view>
        <view class="menu-item">
          <text class="menu-label">行情自动刷新</text>
          <switch :checked="autoRefresh" color="#4A90E2" @change="toggleAutoRefresh" />
        </view>
      </view>
    </view>

    <!-- 通知设置 -->
    <view class="section">
      <view class="section-title">通知设置</view>
      <view class="menu-list">
        <view class="menu-item">
          <text class="menu-label">价格提醒</text>
          <switch :checked="notifyPrice" color="#4A90E2" @change="toggleNotifyPrice" />
        </view>
        <view class="menu-item">
          <text class="menu-label">选股结果通知</text>
          <switch :checked="notifySelection" color="#4A90E2" @change="toggleNotifySelection" />
        </view>
        <view class="menu-item">
          <text class="menu-label">AI 分析推送</text>
          <switch :checked="notifyAI" color="#4A90E2" @change="toggleNotifyAI" />
        </view>
      </view>
    </view>

    <!-- 数据源 -->
    <view class="section">
      <view class="section-title">数据管理</view>
      <view class="menu-list">
        <view class="menu-item" @click="showDataSourcePicker = true">
          <text class="menu-label">行情数据源</text>
          <view class="menu-right">
            <text class="menu-value">{{ dataSourceLabel }}</text>
            <text class="menu-arrow">›</text>
          </view>
        </view>
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

    <!-- 主题选择弹层 -->
    <view v-if="showThemePicker" class="picker-mask" @click="showThemePicker = false">
      <view class="picker-panel" @click.stop>
        <view class="picker-title">选择主题模式</view>
        <view
          v-for="opt in themeOptions"
          :key="opt.value"
          class="picker-option"
          :class="{ active: darkMode === opt.value }"
          @click="selectTheme(opt.value)"
        >
          <text class="option-label">{{ opt.label }}</text>
          <text v-if="darkMode === opt.value" class="option-check">✓</text>
        </view>
        <view class="picker-cancel" @click="showThemePicker = false">取消</view>
      </view>
    </view>

    <!-- 语言选择弹层 -->
    <view v-if="showLangPicker" class="picker-mask" @click="showLangPicker = false">
      <view class="picker-panel" @click.stop>
        <view class="picker-title">选择语言</view>
        <view
          v-for="opt in langOptions"
          :key="opt.value"
          class="picker-option"
          :class="{ active: language === opt.value }"
          @click="selectLang(opt.value)"
        >
          <text class="option-label">{{ opt.label }}</text>
          <text v-if="language === opt.value" class="option-check">✓</text>
        </view>
        <view class="picker-cancel" @click="showLangPicker = false">取消</view>
      </view>
    </view>

    <!-- 数据源选择弹层 -->
    <view v-if="showDataSourcePicker" class="picker-mask" @click="showDataSourcePicker = false">
      <view class="picker-panel" @click.stop>
        <view class="picker-title">选择行情数据源</view>
        <view
          v-for="opt in dataSourceOptions"
          :key="opt.value"
          class="picker-option"
          :class="{ active: dataSource === opt.value }"
          @click="selectDataSource(opt.value)"
        >
          <text class="option-label">{{ opt.label }}</text>
          <text v-if="dataSource === opt.value" class="option-check">✓</text>
        </view>
        <view class="picker-cancel" @click="showDataSourcePicker = false">取消</view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { getThemeState, setThemeMode, type ThemeMode } from '@/utils/theme'

// ---- 弹层开关 ----
const showThemePicker = ref(false)
const showLangPicker = ref(false)
const showDataSourcePicker = ref(false)

// ---- 设置项 ----
const darkMode = ref<ThemeMode>('light')
const autoRefresh = ref(true)
const notifyPrice = ref(false)
const notifySelection = ref(false)
const notifyAI = ref(false)
const cacheSize = ref('0 KB')
const language = ref<'zh-CN' | 'en'>('zh-CN')
const dataSource = ref<'sina' | 'akshare' | 'eastmoney'>('sina')

const SETTINGS_KEY = 'ai-stock:settings'

interface AppSettings {
  darkMode: ThemeMode
  autoRefresh: boolean
  notifyPrice: boolean
  notifySelection: boolean
  notifyAI: boolean
  language: string
  dataSource: string
}

// ---- 选项列表 ----
const themeOptions = [
  { label: '浅色模式', value: 'light' as ThemeMode },
  { label: '深色模式', value: 'dark' as ThemeMode },
  { label: '跟随系统', value: 'system' as ThemeMode },
]

const langOptions = [
  { label: '简体中文', value: 'zh-CN' },
  { label: 'English', value: 'en' },
]

const dataSourceOptions = [
  { label: '新浪财经（推荐）', value: 'sina' },
  { label: 'AKShare（开源数据）', value: 'akshare' },
  { label: '东方财富', value: 'eastmoney' },
]

// ---- 显示标签 ----
const themeLabel = computed(() => {
  const found = themeOptions.find(o => o.value === darkMode.value)
  return found?.label ?? '浅色模式'
})

const langLabel = computed(() => {
  const found = langOptions.find(o => o.value === language.value)
  return found?.label ?? '简体中文'
})

const dataSourceLabel = computed(() => {
  const found = dataSourceOptions.find(o => o.value === dataSource.value)
  return found?.label ?? '新浪财经'
})

// ---- 持久化 ----
function loadSettings() {
  const theme = getThemeState()
  darkMode.value = theme.mode

  try {
    const raw = uni.getStorageSync(SETTINGS_KEY)
    if (raw) {
      const s: AppSettings = JSON.parse(raw)
      autoRefresh.value = s.autoRefresh ?? true
      notifyPrice.value = s.notifyPrice ?? false
      notifySelection.value = s.notifySelection ?? false
      notifyAI.value = s.notifyAI ?? false
      language.value = (s.language as 'zh-CN' | 'en') || 'zh-CN'
      dataSource.value = (s.dataSource as 'sina' | 'akshare' | 'eastmoney') || 'sina'
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
    language: language.value,
    dataSource: dataSource.value,
  }
  uni.setStorageSync(SETTINGS_KEY, JSON.stringify(s))
}

// ---- 选择器操作 ----
function selectTheme(mode: ThemeMode) {
  darkMode.value = mode
  setThemeMode(mode)
  showThemePicker.value = false
  saveSettings()
}

function selectLang(lang: 'zh-CN' | 'en') {
  language.value = lang
  showLangPicker.value = false
  saveSettings()
  uni.showToast({ title: lang === 'en' ? 'Language changed to English' : '已切换为中文', icon: 'none' })
}

function selectDataSource(src: 'sina' | 'akshare' | 'eastmoney') {
  dataSource.value = src
  showDataSourcePicker.value = false
  saveSettings()
  uni.showToast({ title: '数据源已切换', icon: 'success' })
}

// ---- 开关操作 ----
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

// ---- 缓存 ----
function getCacheSize() {
  try {
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

// ---- 弹层 ----
.picker-mask {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.45);
  z-index: 9999;
  display: flex;
  align-items: flex-end;
}

.picker-panel {
  width: 100%;
  background: $bg-card;
  border-radius: 24rpx 24rpx 0 0;
  padding-bottom: env(safe-area-inset-bottom);
}

.picker-title {
  padding: 32rpx 32rpx 16rpx;
  font-size: $font-size-base;
  font-weight: 600;
  color: $text-primary;
  text-align: center;
  border-bottom: 1rpx solid $border-color;
}

.picker-option {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 32rpx;
  border-bottom: 1rpx solid $border-color;

  &:active {
    background: rgba(0, 0, 0, 0.03);
  }

  &.active .option-label {
    color: $color-primary;
    font-weight: 600;
  }
}

.option-label {
  font-size: $font-size-base;
  color: $text-primary;
}

.option-check {
  font-size: $font-size-lg;
  color: $color-primary;
  font-weight: 700;
}

.picker-cancel {
  padding: 32rpx;
  text-align: center;
  font-size: $font-size-base;
  color: $text-secondary;
  border-top: 8rpx solid $bg-page;
}
</style>
