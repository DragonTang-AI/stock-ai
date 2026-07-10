<template>
  <view class="hosted-page">
    <!-- 骨架屏 -->
    <LoadingSkeleton v-if="isLoading" scene="hosted" :rows="3" />

    <!-- 审核模式提示 -->
    <view class="audit-banner" v-if="status?.is_audit_mode">
      <view class="audit-icon">&#x26A0;</view>
      <view class="audit-content">
        <text class="audit-title">审核模式</text>
        <text class="audit-desc">系统目前处于审核模式，信号仅记录不下单。如需正式运行，请联系管理员。</text>
      </view>
    </view>

    <!-- 托管状态卡片 -->
    <view class="status-card">
      <view class="status-header">
        <view class="status-left">
          <text class="status-title">AI 托管</text>
          <view
            class="status-badge"
            :class="{ active: status?.is_active }"
          >
            {{ status?.is_active ? '已开启' : '已关闭' }}
          </view>
        </view>
        <switch
          :checked="status?.is_active ?? false"
          :disabled="isSwitching || (status?.is_audit_mode ?? false)"
          @change="handleToggle"
          color="#4A90E2"
        />
      </view>

      <view class="status-grid" v-if="status?.is_active">
        <view class="grid-item">
          <text class="grid-label">托管模式</text>
          <text class="grid-value">{{ status.mode === 'AI_HOSTED' ? 'AI 自动' : '手动' }}</text>
        </view>
        <view class="grid-item">
          <text class="grid-label">风险等级</text>
          <text class="grid-value risk-tag" :class="'risk-' + status.risk_level">
            {{ riskLabel(status.risk_level) }}
          </text>
        </view>
        <view class="grid-item">
          <text class="grid-label">今日信号</text>
          <text class="grid-value">{{ status.active_signals_today }} 条</text>
        </view>
        <view class="grid-item">
          <text class="grid-label">今日盈亏</text>
          <text class="grid-value" :class="(status.daily_loss_pct ?? 0) >= 0 ? 'up' : 'down'">
            {{ (status.daily_loss_pct ?? 0) >= 0 ? '+' : '' }}{{ ((status.daily_loss_pct ?? 0) * 100).toFixed(2) }}%
          </text>
        </view>
        <view class="grid-item">
          <text class="grid-label">今日成交</text>
          <text class="grid-value">{{ status.total_trades }} 笔</text>
        </view>
        <view class="grid-item">
          <text class="grid-label">开启时间</text>
          <text class="grid-value muted">{{ formatDate(status.enabled_at) }}</text>
        </view>
      </view>
    </view>

    <!-- 统计卡片（4格横排） -->
    <view class="stats-row" v-if="status?.is_active">
      <view class="stat-card stat-total">
        <text class="stat-num">{{ status.total_trades }}</text>
        <text class="stat-label">总信号</text>
      </view>
      <view class="stat-card stat-triggered">
        <text class="stat-num">{{ status.total_triggered }}</text>
        <text class="stat-label">执行成功</text>
      </view>
      <view class="stat-card stat-blocked">
        <text class="stat-num">{{ status.total_blocked }}</text>
        <text class="stat-label">风控拦截</text>
      </view>
      <view class="stat-card stat-today">
        <text class="stat-num">{{ status.active_signals_today }}</text>
        <text class="stat-label">今日信号</text>
      </view>
    </view>

    <!-- 托管设置 -->
    <view class="section" v-if="status?.is_active">
      <view class="section-header">
        <text class="section-title">托管设置</text>
      </view>

      <!-- 风险等级 -->
      <view class="setting-item">
        <view class="setting-label">
          <text class="s-name">风险等级</text>
          <text class="s-desc">决定 AI 交易策略的激进程度</text>
        </view>
        <view class="risk-selector">
          <view
            v-for="lvl in riskLevels"
            :key="lvl.value"
            class="risk-option"
            :class="{ selected: configForm.risk_level === lvl.value }"
            @click="configForm.risk_level = lvl.value as RiskLevel"
          >
            <text class="risk-dot" :class="'risk-' + lvl.value"></text>
            <text class="risk-name">{{ lvl.label }}</text>
          </view>
        </view>
      </view>

      <!-- 单笔限额 -->
      <view class="setting-item">
        <view class="setting-label">
          <text class="s-name">单笔限额（元）</text>
          <text class="s-desc">单次交易金额上限</text>
        </view>
        <view class="input-wrap">
          <input
            class="s-input"
            v-model="configForm.single_trade_limit"
            type="digit"
            placeholder="如 50000"
            :adjust-position="true"
            :cursor-spacing="20"
          />
        </view>
      </view>

      <!-- 日限额 -->
      <view class="setting-item">
        <view class="setting-label">
          <text class="s-name">日限额（元）</text>
          <text class="s-desc">单日总交易金额上限</text>
        </view>
        <view class="input-wrap">
          <input
            class="s-input"
            v-model="configForm.daily_trade_limit"
            type="digit"
            placeholder="如 200000"
            :adjust-position="true"
            :cursor-spacing="20"
          />
        </view>
      </view>

      <!-- 行业集中度 -->
      <view class="setting-item">
        <view class="setting-label">
          <text class="s-name">行业集中度（%）</text>
          <text class="s-desc">单一行业持仓占总资产比例上限</text>
        </view>
        <view class="input-wrap">
          <input
            class="s-input"
            v-model="configForm.industry_concentration"
            type="digit"
            placeholder="如 30"
            :adjust-position="true"
            :cursor-spacing="20"
          />
          <text class="input-suffix">%</text>
        </view>
      </view>

      <!-- 自动止损 -->
      <view class="setting-item">
        <view class="setting-label">
          <text class="s-name">自动止损</text>
          <text class="s-desc">达到止损线自动平仓</text>
        </view>
        <switch
          :checked="configForm.auto_stop_loss"
          @change="configForm.auto_stop_loss = ($event as any).detail.value"
          color="#4A90E2"
        />
      </view>

      <button
        class="btn-primary"
        :disabled="savingConfig"
        @click="handleSaveConfig"
      >
        {{ savingConfig ? '保存中...' : '保存设置' }}
      </button>
    </view>

    <!-- 交易日志 -->
    <view class="section" v-if="status?.is_active">
      <view class="section-header">
        <text class="section-title">交易日志</text>
        <text class="section-action" @click="loadLogs">刷新</text>
      </view>

      <view class="log-list">
        <view
          class="log-item"
          v-for="log in logs"
          :key="log.id"
          @click="goDetail(log.symbol)"
        >
          <view class="log-row top">
            <text class="log-time">{{ formatLogTime(log.created_at) }}</text>
          </view>
          <view class="log-row stock">
            <text class="log-name">{{ log.symbol_name || log.symbol }}</text>
            <text class="log-symbol" v-if="log.symbol_name">{{ log.symbol }}</text>
          </view>
          <view class="log-row tags">
            <text class="log-action" :class="actionTagClass(log.action)">{{ actionLabel(log.action) }}</text>
            <text class="log-status" :class="statusTagClass(log.status)">{{ statusLabel(log.status) }}</text>
          </view>
          <view class="log-row reason" v-if="log.reason">
            <text class="log-reason-text">{{ log.reason }}</text>
          </view>
        </view>
      </view>

      <view class="list-more" v-if="logTotal > logs.length" @click="loadMoreLogs">
        <text>加载更多 ({{ logTotal - logs.length }} 条)</text>
      </view>

      <view class="signal-empty" v-if="!logs.length && !loadingLogs">
        <text>暂无交易日志</text>
      </view>
    </view>

    <!-- 免责声明 -->
    <view class="disclaimer" v-if="status?.disclaimer">
      <text>{{ status.disclaimer }}</text>
    </view>

    <!-- 加载中 -->
    <view class="loading-state" v-if="isLoading">
      <text>加载中...</text>
    </view>

    <!-- 空状态 -->
    <view class="empty-state" v-if="!isLoading && !status">
      <text>AI托管服务未就绪</text>
      <button class="btn-retry" @click="loadStatus">重试</button>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import LoadingSkeleton from '@/components/common/LoadingSkeleton.vue'
import { trackPageView, trackAction } from '@/utils/tracker'
import {
  getHostedStatus,
  switchHosted,
  updateHostedConfig,
  getHostedTradeLogs,
  type HostedStatus,
  type HostedTradeLog,
  type HostedMode,
  type RiskLevel,
  type HostedConfigRequest,
  RiskLevelLabel,
} from '@/api/hosted'

const riskLevels = [
  { value: 'conservative' as RiskLevel, label: '保守' },
  { value: 'balanced' as RiskLevel, label: '平衡' },
  { value: 'aggressive' as RiskLevel, label: '激进' },
]

const isLoading = ref(false)
const savingConfig = ref(false)
const isSwitching = ref(false)
const loadingLogs = ref(false)
const status = ref<HostedStatus | null>(null)

const logs = ref<HostedTradeLog[]>([])
const logTotal = ref(0)
const logOffset = ref(0)

const configForm = reactive<HostedConfigRequest & { single_trade_limit: string; daily_trade_limit: string; industry_concentration: string }>({
  risk_level: 'balanced',
  single_trade_limit: '',
  daily_trade_limit: '',
  industry_concentration: '',
  auto_stop_loss: true,
})

function riskLabel(level: RiskLevel): string {
  return RiskLevelLabel[level] || level
}

function actionLabel(action: string): string {
  switch (action) {
    case 'BUY': return '买入'
    case 'ADD': return '加仓'
    case 'HOLD': return '持仓'
    case 'SELL': return '卖出'
    case 'REDUCE': return '减仓'
    default: return action
  }
}

function actionTagClass(action: string): string {
  switch (action) {
    case 'BUY': return 'act-buy'
    case 'ADD': return 'act-add'
    case 'SELL': return 'act-sell'
    case 'REDUCE': return 'act-reduce'
    case 'HOLD': return 'act-hold'
    default: return ''
  }
}

function statusLabel(status: string): string {
  switch (status) {
    case 'TRIGGERED': return '已触发'
    case 'BLOCKED': return '已拦截'
    case 'SKIPPED': return '已跳过'
    case 'ERROR': return '异常'
    default: return status
  }
}

function statusTagClass(status: string): string {
  switch (status) {
    case 'TRIGGERED': return 'sts-triggered'
    case 'BLOCKED': return 'sts-blocked'
    case 'SKIPPED': return 'sts-skipped'
    case 'ERROR': return 'sts-error'
    default: return ''
  }
}

function formatDate(iso: string | null): string {
  if (!iso) return '-'
  const d = new Date(iso)
  const m = (d.getMonth() + 1).toString().padStart(2, '0')
  const day = d.getDate().toString().padStart(2, '0')
  return `${m}-${day}`
}

function formatLogTime(iso: string): string {
  if (!iso) return '-'
  const d = new Date(iso)
  const m = (d.getMonth() + 1).toString().padStart(2, '0')
  const day = d.getDate().toString().padStart(2, '0')
  const h = d.getHours().toString().padStart(2, '0')
  const min = d.getMinutes().toString().padStart(2, '0')
  const s = d.getSeconds().toString().padStart(2, '0')
  return `${m}-${day} ${h}:${min}:${s}`
}

function goDetail(symbol: string) {
  if (!symbol) return
  uni.navigateTo({ url: '/pages/detail/index?symbol=' + symbol })
}

/* ---- 数据加载 ---- */
async function loadStatus() {
  isLoading.value = true
  try {
    status.value = await getHostedStatus()
    fillConfigForm(status.value)
    if (status.value.is_active) {
      await loadLogs()
    }
  } catch {
    status.value = null
  } finally {
    isLoading.value = false
  }
}

function fillConfigForm(s: HostedStatus) {
  configForm.risk_level = s.risk_level || 'balanced'
  configForm.single_trade_limit = s.single_trade_limit != null ? String(s.single_trade_limit) : ''
  configForm.daily_trade_limit = s.daily_trade_limit != null ? String(s.daily_trade_limit) : ''
  configForm.industry_concentration = s.industry_concentration != null ? String((s.industry_concentration * 100).toFixed(0)) : ''
  configForm.auto_stop_loss = s.auto_stop_loss ?? true
}

/* ---- 开关 ---- */
async function handleToggle(e: { detail: { value: boolean } }) {
  const wantActive = e.detail.value
  isSwitching.value = true
  try {
    uni.showLoading({ title: '切换中...' })
    status.value = await switchHosted(wantActive ? 'AI_HOSTED' : 'MANUAL')
    fillConfigForm(status.value)
    if (wantActive) {
      await loadLogs()
    } else {
      logs.value = []
      logTotal.value = 0
    }
    uni.showToast({ title: wantActive ? '已开启AI托管' : '已关闭AI托管', icon: 'success' })
    trackAction(wantActive ? 'hosted_enable' : 'hosted_disable', { mode: wantActive ? 'AI_HOSTED' : 'MANUAL' })
  } catch (err: any) {
    uni.showToast({ title: err?.message || '操作失败', icon: 'none' })
  } finally {
    isSwitching.value = false
    uni.hideLoading()
  }
}

/* ---- 保存设置 ---- */
async function handleSaveConfig() {
  savingConfig.value = true
  try {
    const body: HostedConfigRequest = { risk_level: configForm.risk_level }
    if (configForm.single_trade_limit) {
      body.single_trade_limit = parseFloat(configForm.single_trade_limit)
    }
    if (configForm.daily_trade_limit) {
      body.daily_trade_limit = parseFloat(configForm.daily_trade_limit)
    }
    if (configForm.industry_concentration) {
      body.industry_concentration = parseFloat(configForm.industry_concentration) / 100
    }
    body.auto_stop_loss = configForm.auto_stop_loss

    status.value = await updateHostedConfig(body)
    fillConfigForm(status.value)
    uni.showToast({ title: '设置已保存', icon: 'success' })
  } catch (err: any) {
    uni.showToast({ title: err?.message || '保存失败', icon: 'none' })
  } finally {
    savingConfig.value = false
  }
}

/* ---- 交易日志 ---- */
async function loadLogs() {
  loadingLogs.value = true
  try {
    const res = await getHostedTradeLogs(50, 0)
    logs.value = res.logs || []
    logTotal.value = res.total || 0
    logOffset.value = logs.value.length
  } catch {
    /* ignore */
  } finally {
    loadingLogs.value = false
  }
}

async function loadMoreLogs() {
  try {
    const res = await getHostedTradeLogs(50, logOffset.value)
    logs.value.push(...(res.logs || []))
    logTotal.value = res.total || 0
    logOffset.value = logs.value.length
  } catch {
    /* ignore */
  }
}

onMounted(loadStatus)
onShow(() => {
  if (!status.value) loadStatus()
  trackPageView('hosted')
})
</script>

<style scoped lang="scss">
.hosted-page {
  min-height: 100vh;
  background: var(--bg-page, #f5f6fa);
  padding-bottom: calc(env(safe-area-inset-bottom) + 48rpx);
}

/* ---- 审核模式横幅 ---- */
.audit-banner {
  margin: 16rpx 24rpx;
  padding: 20rpx 24rpx;
  background: #FFF3CD;
  border: 2rpx solid #FFC107;
  border-radius: 12rpx;
  display: flex;
  align-items: flex-start;
  gap: 16rpx;
}

.audit-icon {
  font-size: 36rpx;
  line-height: 44rpx;
  flex-shrink: 0;
}

.audit-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4rpx;
}

.audit-title {
  font-size: 28rpx;
  font-weight: 700;
  color: #856404;
}

.audit-desc {
  font-size: 24rpx;
  color: #856404;
  line-height: 1.5;
}

/* ---- 状态卡片 ---- */
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
  background: rgba(255, 255, 255, 0.15);

  &.active {
    background: rgba(74, 144, 226, 0.6);
  }
}

.status-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20rpx 16rpx;
}

.grid-item {
  display: flex;
  flex-direction: column;
  gap: 6rpx;
}

.grid-label {
  font-size: 22rpx;
  color: rgba(255, 255, 255, 0.55);
}

.grid-value {
  font-size: 26rpx;
  font-weight: 600;
}

.muted {
  font-size: 22rpx;
  font-weight: 400;
  opacity: 0.6;
}

.risk-tag {
  display: inline;

  &.risk-conservative { color: var(--color-down, #34C759); }
  &.risk-balanced { color: #FFC107; }
  &.risk-aggressive { color: var(--color-up, #E25C5C); }
}

/* ---- 统计卡片 4 格 ---- */
.stats-row {
  display: flex;
  margin: 16rpx 24rpx;
  gap: 12rpx;
}

.stat-card {
  flex: 1;
  border-radius: 12rpx;
  padding: 20rpx 12rpx;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6rpx;
}

.stat-num {
  font-size: 36rpx;
  font-weight: 700;
}

.stat-label {
  font-size: 22rpx;
}

.stat-total {
  background: #E8F0FE;
  .stat-num { color: #4A90E2; }
  .stat-label { color: #4A90E2; }
}

.stat-triggered {
  background: #E6F9ED;
  .stat-num { color: #34C759; }
  .stat-label { color: #34C759; }
}

.stat-blocked {
  background: #FFF3E0;
  .stat-num { color: #F59E0B; }
  .stat-label { color: #F59E0B; }
}

.stat-today {
  background: #EDE9FE;
  .stat-num { color: #8B5CF6; }
  .stat-label { color: #8B5CF6; }
}

/* ---- Section ---- */
.section {
  background: var(--bg-card, #fff);
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
  font-size: 30rpx;
  font-weight: 700;
  color: var(--text-primary, #1a1a2e);
}

.section-action {
  font-size: 24rpx;
  color: var(--color-primary, #4A90E2);
}

/* ---- 设置项 ---- */
.setting-item {
  padding: 20rpx 0;
  border-bottom: 1rpx solid var(--border-color, #f0f0f0);

  &:last-of-type {
    border-bottom: none;
  }
}

.setting-label {
  margin-bottom: 12rpx;
}

.s-name {
  font-size: 28rpx;
  font-weight: 500;
  color: var(--text-primary, #1a1a2e);
}

.s-desc {
  font-size: 22rpx;
  color: var(--text-hint, #999);
  margin-left: 12rpx;
}

.setting-item:has(switch) {
  display: flex;
  justify-content: space-between;
  align-items: center;

  .setting-label {
    margin-bottom: 0;
  }
}

/* ---- 风险等级选择器 ---- */
.risk-selector {
  display: flex;
  gap: 12rpx;
}

.risk-option {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8rpx;
  padding: 16rpx 0;
  border-radius: 12rpx;
  background: var(--bg-input, #f5f6fa);
  border: 2rpx solid transparent;

  &.selected {
    background: #EDF4FD;
    border-color: var(--color-primary, #4A90E2);
  }
}

.risk-dot {
  width: 16rpx;
  height: 16rpx;
  border-radius: 50%;

  &.risk-conservative { background: #34C759; }
  &.risk-balanced { background: #FFC107; }
  &.risk-aggressive { background: #E25C5C; }
}

.risk-name {
  font-size: 26rpx;
  color: var(--text-primary, #1a1a2e);
  font-weight: 500;
}

/* ---- 输入框 ---- */
.input-wrap {
  display: flex;
  align-items: center;
  background: var(--bg-input, #f5f6fa);
  border-radius: 10rpx;
  padding: 14rpx 20rpx;
}

.s-input {
  flex: 1;
  font-size: 28rpx;
  color: var(--text-primary, #1a1a2e);
}

.input-suffix {
  font-size: 24rpx;
  color: var(--text-hint, #999);
  margin-left: 8rpx;
}

/* ---- 按钮 ---- */
.btn-primary {
  margin-top: 32rpx;
  background: var(--color-primary, #4A90E2);
  color: #fff;
  border-radius: 12rpx;
  font-size: 28rpx;
  height: 88rpx;
  line-height: 88rpx;

  &[disabled] {
    opacity: 0.5;
  }
}

/* ---- 交易日志 ---- */
.log-list {
  display: flex;
  flex-direction: column;
  gap: 12rpx;
}

.log-item {
  padding: 20rpx;
  background: var(--bg-input, #f8f9fc);
  border-radius: 12rpx;
}

.log-row {
  display: flex;
  align-items: center;

  &.top {
    margin-bottom: 6rpx;
  }

  &.stock {
    margin-bottom: 8rpx;
  }

  &.tags {
    margin-bottom: 6rpx;
    gap: 10rpx;
  }

  &.reason {
    /* reason 单独行 */
  }
}

.log-time {
  font-size: 22rpx;
  color: var(--text-hint, #ccc);
}

.log-name {
  font-size: 28rpx;
  font-weight: 600;
  color: var(--text-primary, #1a1a2e);
}

.log-symbol {
  font-size: 22rpx;
  color: var(--text-hint, #999);
  margin-left: 8rpx;
}

/* 操作标签 */
.log-action {
  font-size: 22rpx;
  padding: 2rpx 12rpx;
  border-radius: 20rpx;
  font-weight: 600;

  &.act-buy {
    background: #D1ECF1;
    color: #0C5460;
  }
  &.act-add {
    background: #D4EDDA;
    color: #155724;
  }
  &.act-sell {
    background: #F8D7DA;
    color: #721C24;
  }
  &.act-reduce {
    background: #FFF3E0;
    color: #856404;
  }
  &.act-hold {
    background: #E8E8E8;
    color: #666;
  }
}

/* 状态标签 */
.log-status {
  font-size: 22rpx;
  padding: 2rpx 12rpx;
  border-radius: 20rpx;

  &.sts-triggered {
    background: #D4EDDA;
    color: #155724;
  }
  &.sts-blocked {
    background: #FFF3E0;
    color: #856404;
  }
  &.sts-skipped {
    background: #E8E8E8;
    color: #999;
  }
  &.sts-error {
    background: #F8D7DA;
    color: #721C24;
  }
}

.log-reason-text {
  font-size: 22rpx;
  color: var(--text-hint, #999);
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.signal-empty {
  text-align: center;
  padding: 60rpx 0;
  font-size: 26rpx;
  color: var(--text-hint, #ccc);
}

.list-more {
  text-align: center;
  padding: 24rpx 0 0;
  font-size: 24rpx;
  color: var(--color-primary, #4A90E2);
}

/* ---- 免责声明 ---- */
.disclaimer {
  margin: 16rpx 24rpx;
  padding: 20rpx 24rpx;
  background: var(--bg-input, #f0f0f0);
  border-radius: 12rpx;
  font-size: 22rpx;
  color: var(--text-hint, #999);
  line-height: 1.6;
}

/* ---- 颜色 ---- */
.up { color: var(--color-up, #E25C5C); }
.down { color: var(--color-down, #34C759); }
.neutral { color: #FFC107; }

/* ---- 状态页 ---- */
.loading-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 120rpx 0;
  font-size: 28rpx;
  color: var(--text-hint, #999);
}

.btn-retry {
  margin-top: 24rpx;
  background: var(--color-primary, #4A90E2);
  color: #fff;
  border-radius: 12rpx;
  font-size: 26rpx;
  padding: 12rpx 48rpx;
}
</style>
