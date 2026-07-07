<template>
  <view class="hosted-page">
    <!-- 状态卡片 -->
    <view class="status-card" v-if="status">
      <view class="status-header">
        <view class="status-left">
          <text class="status-title">AI托管</text>
          <view class="status-badge" :class="{ active: status.is_active }">
            <text>{{ status.is_active ? '运行中' : '已关闭' }}</text>
          </view>
        </view>
        <switch
          :checked="status.is_active"
          @change="handleToggle"
          color="#4A90E2"
        />
      </view>
      <view class="status-body" v-if="status.is_active">
        <view class="status-row">
          <text class="s-label">当前模式</text>
          <text class="s-value">{{ status.mode || '-' }}</text>
        </view>
        <view class="status-row">
          <text class="s-label">今日成交</text>
          <text class="s-value">{{ status.total_trades }} 笔</text>
        </view>
        <view class="status-row">
          <text class="s-label">今日盈亏</text>
          <text class="s-value" :class="(status.daily_loss_pct ?? 0) >= 0 ? 'up' : 'down'">
            {{ (status.daily_loss_pct ?? 0) >= 0 ? '+' : '' }}{{ ((status.daily_loss_pct ?? 0) * 100).toFixed(2) }}%
          </text>
        </view>
        <view class="status-row">
          <text class="s-label">最后更新</text>
          <text class="s-value muted">{{ formatTime(status.is_active ? status.enabled_at : status.disabled_at) }}</text>
        </view>
      </view>
    </view>

    <!-- 风控参数 -->
    <view class="section" v-if="status && status.is_active">
      <view class="section-header">
        <text class="section-title">风控参数</text>
        <text class="section-action" @click="showConfig = !showConfig">
          {{ showConfig ? '收起' : '修改' }}
        </text>
      </view>

      <view class="config-readonly" v-if="!showConfig">
        <view class="cfg-row">
          <text class="cfg-label">最低置信度</text>
          <text class="cfg-value">{{ status.min_confidence != null ? status.min_confidence + '%' : '-' }}</text>
        </view>
        <view class="cfg-row">
          <text class="cfg-label">最大仓位比例</text>
          <text class="cfg-value">{{ status.max_position_ratio != null ? (status.max_position_ratio * 100).toFixed(0) + '%' : '-' }}</text>
        </view>
      </view>

      <view class="config-edit" v-else>
        <view class="cfg-edit-row">
          <text class="cfg-label">最低置信度 (%)</text>
          <view class="cfg-input-wrap">
            <input class="cfg-input" v-model="configForm.min_confidence" type="number" placeholder="60-100" />
            <text class="cfg-unit">%</text>
          </view>
        </view>
        <view class="cfg-hint">建议范围 60-90，越高越保守</view>

        <view class="cfg-edit-row">
          <text class="cfg-label">最大仓位比例 (%)</text>
          <view class="cfg-input-wrap">
            <input class="cfg-input" v-model="configForm.max_position_ratio" type="number" placeholder="5-30" />
            <text class="cfg-unit">%</text>
          </view>
        </view>
        <view class="cfg-hint">单策略最大持仓占总资产比例，建议 ≤20</view>

        <button class="btn-save" :disabled="savingConfig" @click="handleSaveConfig">
          {{ savingConfig ? '保存中...' : '保存修改' }}
        </button>
      </view>
    </view>

    <!-- 执行日志 -->
    <view class="section" v-if="status && status.is_active && logs.length">
      <view class="section-header">
        <text class="section-title">执行日志</text>
        <text class="section-action" @click="loadLogs">刷新</text>
      </view>

      <view class="log-list">
        <view class="log-item" v-for="log in logs" :key="log.id">
          <view class="log-header">
            <text class="log-action" :class="log.action === 'BUY' ? 'up' : 'down'">
              {{ log.action === 'BUY' ? '买入' : log.action === 'SELL' ? '卖出' : log.action }}
            </text>
            <text class="log-symbol">{{ log.symbol }}</text>
            <text class="log-confidence" v-if="log.signal_id">置信度 {{ log.signal_id.slice(0, 8) }}</text>
          </view>
          <view class="log-body">
            <text class="log-msg">{{ log.reason || '-' }}</text>
          </view>
          <view class="log-footer">
            <text class="log-result" :class="log.status === 'TRIGGERED' ? 'up' : 'down'">
              {{ log.status === 'TRIGGERED' ? '触发' : log.status === 'BLOCKED' ? '阻止' : log.status === 'SKIPPED' ? '跳过' : log.status }}
            </text>
            <text class="log-time">{{ formatTime(log.created_at) }}</text>
          </view>
        </view>
      </view>

      <view class="log-more" v-if="logTotal > logs.length" @click="loadMoreLogs">
        <text>加载更多 ({{ logTotal - logs.length }}条)</text>
      </view>
    </view>

    <!-- 加载状态 -->
    <view class="loading-state" v-if="isLoading">
      <text class="loading-text">加载中...</text>
    </view>

    <!-- 空状态 -->
    <view class="empty-state" v-if="!isLoading && !status">
      <text class="empty-text">AI托管服务未就绪</text>
      <button class="btn-retry" @click="loadStatus">重试</button>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import {
  getHostedStatus, switchHosted, updateHostedConfig, getHostedLogs,
  type HostedStatus, type HostedLog, type HostedMode,
} from '@/api/hosted'

const isLoading = ref(false)
const savingConfig = ref(false)
const status = ref<HostedStatus | null>(null)
const logs = ref<HostedLog[]>([])
const logTotal = ref(0)
const logOffset = ref(0)
const showConfig = ref(false)
const configForm = ref({ min_confidence: '', max_position_ratio: '' })

function formatTime(iso: string): string {
  if (!iso) return '-'
  const d = new Date(iso)
  return d.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

async function loadStatus() {
  isLoading.value = true
  try {
    status.value = await getHostedStatus()
    configForm.value = {
      min_confidence: status.value.min_confidence != null ? String(status.value.min_confidence) : '',
      max_position_ratio: status.value.max_position_ratio != null ? String((status.value.max_position_ratio * 100).toFixed(0)) : '',
    }
    if (status.value.is_active) await loadLogs()
  } catch {
    status.value = null
  } finally {
    isLoading.value = false
  }
}

async function handleToggle(e: { detail: { value: boolean } }) {
  const wantActive = e.detail.value
  const targetMode: HostedMode = wantActive ? 'AI_HOSTED' : 'MANUAL'
  try {
    uni.showLoading({ title: '切换中...' })
    status.value = await switchHosted(targetMode)
    configForm.value = {
      min_confidence: status.value.min_confidence != null ? String(status.value.min_confidence) : '',
      max_position_ratio: status.value.max_position_ratio != null ? String((status.value.max_position_ratio * 100).toFixed(0)) : '',
    }
    if (wantActive) await loadLogs()
  } catch (err: any) {
    uni.showToast({ title: err?.message || '操作失败', icon: 'none' })
  } finally {
    uni.hideLoading()
  }
}

async function handleSaveConfig() {
  const minConf = parseFloat(configForm.value.min_confidence)
  const maxPos = parseFloat(configForm.value.max_position_ratio)
  if (isNaN(minConf) || isNaN(maxPos)) {
    uni.showToast({ title: '请输入有效数值', icon: 'none' })
    return
  }
  savingConfig.value = true
  try {
    status.value = await updateHostedConfig({
      min_confidence: minConf,
      max_position_ratio: maxPos / 100,  // % 转 0-1
    })
    showConfig.value = false
    uni.showToast({ title: '已保存', icon: 'success' })
  } catch (err: any) {
    uni.showToast({ title: err?.message || '保存失败', icon: 'none' })
  } finally {
    savingConfig.value = false
  }
}

async function loadLogs() {
  try {
    const res = await getHostedLogs({ limit: 20, offset: 0 })
    logs.value = res.logs || []
    logTotal.value = res.total || 0
    logOffset.value = logs.value.length
  } catch { /* ignore */ }
}

async function loadMoreLogs() {
  try {
    const res = await getHostedLogs({ limit: 20, offset: logOffset.value })
    logs.value.push(...(res.logs || []))
    logTotal.value = res.total || 0
    logOffset.value = logs.value.length
  } catch { /* ignore */ }
}

onMounted(loadStatus)
onShow(() => { if (!status.value) loadStatus() })
</script>

<style scoped lang="scss">
.hosted-page {
  min-height: 100vh;
  background: #f5f6fa;
  padding-bottom: 32rpx;
}

.status-card {
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
  margin: 16rpx 24rpx;
  border-radius: 16rpx;
  padding: 28rpx;
  color: #fff;
}

.status-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24rpx;
}

.status-left {
  display: flex;
  align-items: center;
  gap: 16rpx;
}

.status-title {
  font-size: 32rpx;
  font-weight: 700;
}

.status-badge {
  padding: 4rpx 16rpx;
  border-radius: 20rpx;
  font-size: 22rpx;
  background: rgba(255,255,255,0.15);
  &.active { background: rgba(74,144,226,0.6); }
}

.status-body {
  display: flex;
  flex-direction: column;
  gap: 16rpx;
}

.status-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.s-label { font-size: 26rpx; color: rgba(255,255,255,0.6); }
.s-value { font-size: 26rpx; font-weight: 600; }
.muted { opacity: 0.6; }

/* Section */
.section {
  background: #fff;
  margin: 16rpx 24rpx;
  border-radius: 16rpx;
  padding: 24rpx;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20rpx;
}

.section-title {
  font-size: 28rpx;
  font-weight: 600;
  color: #1a1a2e;
}

.section-action {
  font-size: 24rpx;
  color: #4A90E2;
}

/* Config */
.cfg-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16rpx 0;
  border-bottom: 1rpx solid #f0f0f0;
  &:last-child { border-bottom: none; }
}

.cfg-label { font-size: 26rpx; color: #666; }
.cfg-value { font-size: 26rpx; font-weight: 600; color: #1a1a2e; }

.cfg-edit-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8rpx;
}

.cfg-input-wrap {
  display: flex;
  align-items: center;
  background: #f5f6fa;
  border-radius: 8rpx;
  padding: 8rpx 16rpx;
}

.cfg-input {
  width: 100rpx;
  text-align: right;
  font-size: 26rpx;
  font-weight: 600;
  color: #1a1a2e;
}

.cfg-unit { font-size: 22rpx; color: #999; margin-left: 4rpx; }

.cfg-hint {
  font-size: 22rpx;
  color: #ccc;
  margin-bottom: 16rpx;
  padding-left: 0;
}

.btn-save {
  margin-top: 24rpx;
  background: #4A90E2;
  color: #fff;
  border-radius: 12rpx;
  font-size: 28rpx;
  height: 80rpx;
  line-height: 80rpx;
  &[disabled] { opacity: 0.5; }
}

/* Logs */
.log-list { display: flex; flex-direction: column; gap: 4rpx; }

.log-item {
  padding: 20rpx;
  background: #f8f9fc;
  border-radius: 12rpx;
  margin-bottom: 12rpx;
  &:last-child { margin-bottom: 0; }
}

.log-header {
  display: flex;
  align-items: center;
  gap: 12rpx;
  margin-bottom: 8rpx;
}

.log-action {
  font-size: 24rpx;
  font-weight: 600;
}

.log-symbol {
  font-size: 24rpx;
  font-weight: 600;
  color: #1a1a2e;
}

.log-confidence {
  font-size: 22rpx;
  color: #999;
  margin-left: auto;
}

.log-body {
  margin-bottom: 6rpx;
}

.log-msg {
  font-size: 24rpx;
  color: #666;
}

.log-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.log-result {
  font-size: 22rpx;
}

.log-time {
  font-size: 22rpx;
  color: #ccc;
}

.log-more {
  text-align: center;
  padding: 20rpx 0 0;
  font-size: 24rpx;
  color: #4A90E2;
}

/* Colors */
.up { color: #E25C5C; }
.down { color: #34C759; }
.neutral { color: #1a1a2e; }

/* States */
.loading-state, .empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 120rpx 0;
}

.loading-text { font-size: 28rpx; color: #999; }
.empty-text { font-size: 28rpx; color: #999; margin-bottom: 16rpx; }

.btn-retry {
  margin-top: 16rpx;
  background: #4A90E2;
  color: #fff;
  border-radius: 12rpx;
  font-size: 26rpx;
  padding: 12rpx 48rpx;
}
</style>
