<template>
  <view class="console-page">
    <!-- 骨架屏 -->
    <SkeletonScreen v-if="isLoading" type="table" :count="5" />

    <template v-else>
    <!-- 调度器运行状态 -->
    <view class="scheduler-bar" :class="{ active: schedulerRunning }">
      <view class="sched-dot" :class="{ pulse: schedulerRunning }"></view>
      <text class="sched-text">
        {{ schedulerRunning ? 'AI 引擎运行中' : 'AI 引擎空闲' }}
      </text>
      <text v-if="schedLastRun" class="sched-detail">上次 {{ schedLastRun }}</text>
      <text v-if="schedNextRun" class="sched-detail next">下次 {{ schedNextRun }}</text>
      <text v-if="schedulerRunning && schedInfo" class="sched-detail sched-count">
        {{ schedInfo.total_signals || 0 }} 信号
      </text>
    </view>

    <!-- 顶部：交易员信息 + 模式 -->
    <view class="header">
      <view class="trader-info">
        <view class="trader-avatar" :class="modeAvatarClass">
          <text class="avatar-text">{{ traderName[0] || 'A' }}</text>
        </view>
        <view class="trader-meta">
          <text class="trader-name">{{ traderName }}</text>
          <text class="trader-tag">{{ traderTag }}</text>
        </view>
      </view>
      <view class="mode-badge" :class="managementMode === 'full_managed' ? 'managed' : 'advisory'">
        <view class="mode-dot"></view>
        <text>{{ managementMode === 'full_managed' ? '全自动托管' : '建议推送' }}</text>
      </view>
    </view>

    <!-- 概览卡片 -->
    <view class="overview-row">
      <view class="ov-card">
        <text class="ov-value">¥{{ formatMoney(overview.total_assets) }}</text>
        <text class="ov-label">总资产</text>
      </view>
      <view class="ov-card">
        <text class="ov-value" :class="overview.unrealized_pnl >= 0 ? 'up' : 'down'">
          {{ formatPct(overview.unrealized_pnl) }}
        </text>
        <text class="ov-label">浮动盈亏</text>
      </view>
      <view class="ov-card">
        <text class="ov-value">{{ overview.position_count }}</text>
        <text class="ov-label">持仓</text>
      </view>
      <view class="ov-card highlight">
        <text class="ov-value" style="color: #f39c12">{{ overview.pending_signals }}</text>
        <text class="ov-label">待决策</text>
      </view>
    </view>

    <!-- Tab 切换 -->
    <view class="tabs">
      <view class="tab-item" :class="{ active: activeTab === 'signals' }" @click="activeTab = 'signals'">
        <text>信号流</text>
        <text v-if="pendingCount > 0" class="tab-badge">{{ pendingCount }}</text>
      </view>
      <view class="tab-item" :class="{ active: activeTab === 'portfolio' }" @click="activeTab = 'portfolio'">
        <text>持仓</text>
      </view>
      <view class="tab-item" :class="{ active: activeTab === 'trades' }" @click="activeTab = 'trades'">
        <text>交易记录</text>
      </view>
      <view class="tab-item" :class="{ active: activeTab === 'perf' }" @click="activeTab = 'perf'" @click.once="loadPerformance">
        <text>绩效</text>
      </view>
    </view>

    <!-- 信号筛选 -->
    <view v-if="activeTab === 'signals'" class="signal-filters">
      <input
        v-model="filterSymbol"
        class="filter-input"
        placeholder="股票代码..."
        @confirm="onFilterChange"
      />
      <picker mode="date" :value="filterDateFrom" @change="onDateFromChange">
        <view class="filter-picker">{{ filterDateFrom || '起始日期' }}</view>
      </picker>
      <picker mode="date" :value="filterDateTo" @change="onDateToChange">
        <view class="filter-picker">{{ filterDateTo || '结束日期' }}</view>
      </picker>
      <picker
        mode="selector"
        :range="statusOptions"
        @change="onStatusChange"
      >
        <view class="filter-picker">
          {{ filterStatusLabel }}
        </view>
      </picker>
      <view v-if="hasFilters" class="filter-clear" @click="clearFilters">
        <text class="filter-clear-text">清空</text>
      </view>
    </view>

    <!-- 信号列表 -->
    <view v-if="activeTab === 'signals'" class="signal-list">
      <view v-if="signals.length === 0" class="empty-state">
        <view class="empty-icon">&#9744;</view>
        <text class="empty-title">暂无信号</text>
        <text class="empty-desc">AI 引擎正在监控市场，一旦发现机会会立即{{ managementMode === 'full_managed' ? '自动执行' : '推送通知' }}</text>
      </view>

      <view v-for="sig in signals" :key="sig.id" class="signal-card" :class="sig.exec_status">
        <!-- 自动执行标签 -->
        <view v-if="sig.exec_status === 'auto_executed'" class="auto-tag">
          <text>AI 自动执行</text>
        </view>

        <view class="sig-head">
          <view class="sig-stock">
            <text class="sig-symbol">{{ sig.symbol }}</text>
            <text class="sig-name">{{ sig.symbol_name }}</text>
          </view>
          <view class="sig-action-row">
            <text :class="sig.action === 'buy' ? 'action-buy' : 'action-sell'">
              {{ sig.action === 'buy' ? '买入' : '卖出' }}
            </text>
            <text class="sig-time">{{ formatRelative(sig.created_at) }}</text>
          </view>
        </view>

        <view class="sig-body">
          <view class="sig-item">
            <text class="sig-label">建议价</text>
            <text class="sig-val mono">¥{{ formatMoney(sig.price, 2) }}</text>
          </view>
          <view class="sig-item">
            <text class="sig-label">数量</text>
            <text class="sig-val mono">{{ sig.quantity }} 股</text>
          </view>
          <view class="sig-item">
            <text class="sig-label">置信度</text>
            <view class="conf-bar-wrap">
              <view class="conf-bar">
                <view class="conf-fill" :style="{ width: sig.confidence + '%' }" :class="sig.confidence >= 70 ? 'high' : sig.confidence >= 50 ? 'mid' : 'low'"></view>
              </view>
              <text class="sig-val mono">{{ sig.confidence }}%</text>
            </view>
          </view>
        </view>

        <view v-if="sig.reasoning" class="sig-reason">
          <view class="reason-icon">&#9432;</view>
          <text>{{ sig.reasoning }}</text>
        </view>

        <!-- 建议模式：确认/忽略 -->
        <view v-if="sig.exec_status === 'pending' && managementMode === 'advisory'" class="sig-actions">
          <view class="btn-confirm" @click="handleConfirm(sig)">
            <text>采纳建议</text>
          </view>
          <view class="btn-ignore" @click="handleIgnore(sig)">
            <text>忽略</text>
          </view>
        </view>

        <!-- 已执行 / 已确认状态 -->
        <view v-else class="sig-exec-status">
          <view v-if="sig.exec_status === 'auto_executed'" class="exec-badge done">
            <text>AI 自动执行</text>
          </view>
          <view v-else-if="sig.exec_status === 'confirmed'" class="exec-badge done">
            <text>已采纳</text>
          </view>
          <view v-else-if="sig.exec_status === 'ignored'" class="exec-badge muted">
            <text>已忽略</text>
          </view>
        </view>
      </view>
    </view>

    <!-- 持仓列表 -->
    <view v-if="activeTab === 'portfolio'" class="portfolio-list">
      <view v-if="portfolios.length === 0" class="empty-state">
        <view class="empty-icon">&#9737;</view>
        <text class="empty-title">暂无持仓</text>
        <text class="empty-desc">AI 交易员会在合适的时机为你建立仓位</text>
      </view>
      <view v-for="pos in portfolios" :key="pos.id" class="portfolio-card">
        <view class="pos-head">
          <text class="pos-symbol">{{ pos.symbol }}</text>
          <text class="pos-name">{{ pos.symbol_name }}</text>
          <text class="pos-pnl" :class="(pos.unrealized_pnl || 0) >= 0 ? 'up' : 'down'">
            {{ formatPct(pos.unrealized_pnl || 0) }}
          </text>
        </view>
        <view class="pos-grid">
          <view class="pos-item">
            <text class="pos-label">持仓</text>
            <text class="pos-val mono">{{ pos.quantity }} 股</text>
          </view>
          <view class="pos-item">
            <text class="pos-label">成本</text>
            <text class="pos-val mono">¥{{ formatMoney(pos.avg_cost, 2) }}</text>
          </view>
          <view class="pos-item">
            <text class="pos-label">现价</text>
            <text class="pos-val mono">¥{{ formatMoney(pos.current_price, 2) }}</text>
          </view>
          <view class="pos-item">
            <text class="pos-label">市值</text>
            <text class="pos-val mono">¥{{ formatMoney(pos.market_value || 0) }}</text>
          </view>
        </view>
      </view>
    </view>

    <!-- 交易记录 -->
    <view v-if="activeTab === 'trades'" class="trade-list">
      <view v-if="trades.length === 0" class="empty-state">
        <view class="empty-icon">&#9776;</view>
        <text class="empty-title">暂无交易记录</text>
        <text class="empty-desc">交易执行后将在此展示</text>
      </view>
      <view v-for="trade in trades" :key="trade.id" class="trade-card">
        <view class="trade-left">
          <view class="trade-icon" :class="trade.action === 'buy' ? 'buy' : 'sell'">
            <text>{{ trade.action === 'buy' ? 'B' : 'S' }}</text>
          </view>
          <view class="trade-info">
            <text class="trade-symbol">{{ trade.symbol }}</text>
            <text class="trade-name">{{ trade.symbol_name }}</text>
          </view>
        </view>
        <view class="trade-right">
          <text class="trade-price mono">¥{{ formatMoney(trade.price, 2) }}</text>
          <text class="trade-qty mono">{{ trade.quantity }} 股</text>
          <text class="trade-time">{{ formatTime(trade.executed_at) }}</text>
        </view>
      </view>
    </view>

    <!-- 绩效面板 -->
    <view v-if="activeTab === 'perf'" class="perf-panel">
      <view v-if="perfLoading" class="perf-loading">
        <text>加载中...</text>
      </view>
      <view v-else-if="!perfData" class="empty-state">
        <view class="empty-icon">&#9783;</view>
        <text class="empty-title">暂无绩效数据</text>
        <text class="empty-desc">交易员开始交易后将生成绩效指标</text>
      </view>
      <template v-else>
        <!-- 指标卡片 -->
        <view class="perf-metrics">
          <view class="perf-card">
            <text class="perf-label">累计收益</text>
            <text class="perf-value" :class="perfData.return_pct >= 0 ? 'up' : 'down'">
              {{ perfData.return_pct >= 0 ? '+' : '' }}{{ formatMoney(perfData.return_pct, 2) }}%
            </text>
          </view>
          <view class="perf-card">
            <text class="perf-label">Alpha</text>
            <text class="perf-value" :class="(perfData.alpha || 0) >= 0 ? 'up' : 'down'">
              {{ (perfData.alpha || 0) >= 0 ? '+' : '' }}{{ formatMoney(perfData.alpha || 0, 2) }}%
            </text>
          </view>
          <view class="perf-card">
            <text class="perf-label">夏普比率</text>
            <text class="perf-value">{{ formatMoney(perfData.sharpe_ratio || 0, 2) }}</text>
          </view>
          <view class="perf-card">
            <text class="perf-label">最大回撤</text>
            <text class="perf-value down">{{ formatMoney(perfData.max_drawdown || 0, 2) }}%</text>
          </view>
          <view class="perf-card">
            <text class="perf-label">胜率</text>
            <text class="perf-value">{{ formatMoney(perfData.win_rate || 0, 1) }}%</text>
          </view>
        </view>
        <!-- 收益曲线 -->
        <view v-if="perfCurve.dates.length" class="perf-chart-section">
          <text class="perf-section-title">收益走势</text>
          <LineChart
            v-model="perfPeriod"
            :dates="perfCurve.dates"
            :values="perfCurve.values"
            height="200px"
            :show-legend="false"
          />
        </view>
        <!-- 历史记录 -->
        <view v-if="perfHistory.length" class="perf-history">
          <text class="perf-section-title">历史记录</text>
          <view v-for="p in perfHistory" :key="p.period + '-' + p.period_end" class="perf-history-row">
            <text class="perf-history-period">{{ p.period_end }}</text>
            <text class="perf-history-return" :class="p.return_pct >= 0 ? 'up' : 'down'">
              {{ p.return_pct >= 0 ? '+' : '' }}{{ formatMoney(p.return_pct, 2) }}%
            </text>
            <text class="perf-history-sharpe">Sharpe {{ formatMoney(p.sharpe_ratio || 0, 2) }}</text>
            <text class="perf-history-win">胜率 {{ formatMoney(p.win_rate || 0, 1) }}%</text>
          </view>
        </view>
      </template>
    </view>
    </template>
  </view>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from "vue"
import { onPullDownRefresh, onShow } from '@dcloudio/uni-app'
import SkeletonScreen from '@/components/common/SkeletonScreen.vue'
import {
  getConsoleOverview,
  getSignals,
  getAgentPortfolio,
  getAgentTrades,
  confirmSignal,
  ignoreSignal,
  type ConsoleOverview,
  type ConsoleSignal,
  type ConsolePortfolio,
  type ConsoleTrade,
} from '@/api/agent'
import { request } from '@/utils/request'
import { formatMoney } from '@/utils/format'
import { useShowRefresh, touchRefreshKey } from '@/utils/refresh-cache'
import LineChart from '@/components/charts/LineChart.vue'

const isLoading = ref(true)
const hireId = ref<number>(0)
const activeTab = ref<'signals' | 'portfolio' | 'trades' | 'perf'>('signals')

const overview = ref<ConsoleOverview>({
  hire_id: 0,
  trader_name: '',
  trader_tag: '',
  management_mode: 'advisory',
  status: 'active',
  total_assets: 0,
  unrealized_pnl: 0,
  today_signals: 0,
  pending_signals: 0,
  position_count: 0,
})

const traderName = ref('')
const traderTag = ref('')
const managementMode = ref('advisory')

const signals = ref<ConsoleSignal[]>([])
const portfolios = ref<ConsolePortfolio[]>([])
const trades = ref<ConsoleTrade[]>([])

const schedulerRunning = ref(false)
const schedInfo = ref<any>(null)
const schedLastRun = ref('')
const schedNextRun = ref('')
let pollTimer: number | null = null
let schedTimer: number | null = null

const pendingCount = computed(() =>
  signals.value.filter(s => s.exec_status === 'pending').length
)

const modeAvatarClass = computed(() => ({
  'avatar-managed': managementMode.value === 'full_managed',
  'avatar-advisory': managementMode.value === 'advisory',
}))

onMounted(() => {
  const pages = getCurrentPages()
  const page = pages[pages.length - 1] as any
  hireId.value = parseInt(page.options?.hire_id || '0')
  loadAll().finally(() => { isLoading.value = false })
  startPolling()
  checkScheduler()
})
onShow(() => {
  if (hireId.value) useShowRefresh('agent-console', () => loadAll())
})

onUnmounted(() => {
  stopPolling()
})

const startPolling = () => {
  // 每 30 秒自动刷新
  pollTimer = setInterval(() => {
    if (hireId.value) loadAll()
  }, 30000)
onPullDownRefresh(() => {
  uni.stopPullDownRefresh()
}) as unknown as number

  // 每 10 秒检查调度器状态
  schedTimer = setInterval(() => {
    checkScheduler()
  }, 10000) as unknown as number
}

const stopPolling = () => {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
  if (schedTimer) { clearInterval(schedTimer); schedTimer = null }
}

const checkScheduler = async () => {
  try {
    const status = await request<any>('/agent-console/scheduler-status')
    schedulerRunning.value = status.running
    if (status.last_run_result) {
      schedInfo.value = status.last_run_result
    }
    if (status.last_run_at) {
      schedLastRun.value = formatRelative(status.last_run_at)
    }
    if (status.next_run_at) {
      const bj = toBJTime(status.next_run_at)
      if (bj) {
        const h = String(bj.getUTCHours()).padStart(2, '0')
        const m = String(bj.getUTCMinutes()).padStart(2, '0')
        const diff = bj.getTime() - Date.now()
        if (diff > 0 && diff < 3600000) {
          schedNextRun.value = Math.ceil(diff / 60000) + '分钟后'
        } else {
          schedNextRun.value = h + ':' + m
        }
      }
    }
  } catch (e) {
    // 忽略
  }
}

const loadAll = async () => {
  if (!hireId.value) return
  try {
    const ov = await getConsoleOverview(hireId.value)
    overview.value = ov
    traderName.value = ov.trader_name
    traderTag.value = ov.trader_tag
    managementMode.value = ov.management_mode
    await Promise.all([loadSignals(), loadPortfolio(), loadTrades()])
  } catch (e: any) {
    // 静默失败 - 后台自动刷新
  }
}

const loadSignals = async () => {
  try {
    const filters: any = {}
    if (filterStatus.value) filters.status = filterStatus.value
    if (filterSymbol.value) filters.symbol = filterSymbol.value
    if (filterDateFrom.value) filters.date_from = filterDateFrom.value
    if (filterDateTo.value) filters.date_to = filterDateTo.value
    signals.value = await getSignals(hireId.value, Object.keys(filters).length ? filters : undefined)
  } catch (e) { /* ignore */ }
}

const loadPortfolio = async () => {
  try {
    portfolios.value = await getAgentPortfolio(hireId.value)
  } catch (e) { /* ignore */ }
}

const loadTrades = async () => {
  try {
    trades.value = await getAgentTrades(hireId.value)
  } catch (e) { /* ignore */ }
}

const loadPerformance = async () => {
  if (!hireId.value) return
  perfLoading.value = true
  try {
    // 先获取 hire 信息拿到 agent_id
    const hireInfo: any = await request('/agent-console/' + hireId.value)
    const agentId = hireInfo.agent_id || hireInfo.data?.agent_id
    if (!agentId) return

    const perf: any = await request('/agent/market/' + agentId + '/performance')
    const pdata = perf || {}
    if (pdata.performance_metrics) {
      perfData.value = pdata.performance_metrics
    }
    if (pdata.recent_performances) {
      perfHistory.value = pdata.recent_performances
    }
    if (pdata.salary_curve && pdata.salary_curve.length) {
      perfCurve.value = {
        dates: pdata.salary_curve.map((p: any) => p.date),
        values: pdata.salary_curve.map((p: any) => p.value),
      }
    }
  } catch (e) { /* ignore */ }
  finally { perfLoading.value = false }
}

const handleConfirm = async (sig: ConsoleSignal) => {
  try {
    uni.showLoading({ title: '处理中...' })
    await confirmSignal(sig.id)
    uni.hideLoading()
    uni.showToast({ title: '已采纳', icon: 'success' })
    uni.vibrateShort({ type: 'medium' })
    await loadAll()
  } catch (e: any) {
    uni.hideLoading()
    uni.showToast({ title: e?.message || '操作失败', icon: 'none' })
  }
}

const handleIgnore = async (sig: ConsoleSignal) => {
  try {
    await ignoreSignal(sig.id)
    uni.showToast({ title: '已忽略', icon: 'none' })
    await loadAll()
  } catch (e: any) {
    uni.showToast({ title: e?.message || '操作失败', icon: 'none' })
  }
}

const formatMoney = (v: number) => {
  if (v == null) return '--'
  if (v >= 10000) return (v / 10000).toFixed(2) + '万'
  return v.toFixed(0)
}

const formatPct = (v: number) => {
  if (v == null) return '--'
  return (v >= 0 ? '+' : '') + v.toFixed(2) + '%'
}

const toBJTime = (t: string) => {
  const d = new Date(t)
  if (isNaN(d.getTime())) return null
  return new Date(d.getTime() + 8 * 3600 * 1000)
}

const formatTime = (t: string | null) => {
  if (!t) return ''
  const bj = toBJTime(t)
  if (!bj) return t.slice(0, 16).replace('T', ' ')
  const y = bj.getUTCFullYear()
  const m = String(bj.getUTCMonth() + 1).padStart(2, '0')
  const day = String(bj.getUTCDate()).padStart(2, '0')
  const h = String(bj.getUTCHours()).padStart(2, '0')
  const min = String(bj.getUTCMinutes()).padStart(2, '0')
  return `${y}-${m}-${day} ${h}:${min}`
}

const formatRelative = (t: string | null) => {
  if (!t) return ''
  try {
    // P2-14: 直接解析 ISO 字符串（支持 +00:00 与 Z），不再手动补 Z，避免 Invalid Date
    const d = new Date(t.replace(' ', 'T'))
    if (isNaN(d.getTime())) return formatTime(t)
    const now = Date.now()
    const diff = now - d.getTime()
    if (diff < 60000) return '刚刚'
    if (diff < 3600000) return Math.floor(diff / 60000) + '分钟前'
    if (diff < 86400000) return Math.floor(diff / 3600000) + '小时前'
    return formatTime(t)
  } catch {
    return formatTime(t)
  }
}
</script>

<style scoped lang="scss">
.console-page {
  min-height: 100vh;
  background: #0a0a14;
  padding-bottom: 60rpx;
}

// ── 调度器状态条 ──
.scheduler-bar {
  display: flex;
  align-items: center;
  padding: 16rpx 24rpx;
  background: #111122;
  border-bottom: 1rpx solid rgba(255, 255, 255, 0.06);
  gap: 12rpx;

  .sched-dot {
    width: 12rpx;
    height: 12rpx;
    border-radius: 50%;
    background: #444466;

    &.pulse {
      background: #27ae60;
      animation: pulse-dot 2s infinite;
    }
  }

  .sched-text {
    font-size: 22rpx;
    color: #667788;
  }

  .sched-detail {
    font-size: 20rpx;
    color: #4A6FA5;
  }

  .sched-detail.next {
    color: #556677;
    margin-left: 16rpx;
  }

  .sched-detail.sched-count {
    margin-left: auto;
    color: #4A6FA5;
  }

  &.active {
    background: rgba(39, 174, 96, 0.06);
    .sched-text { color: #27ae60; }
  }
}

@keyframes pulse-dot {
  0%, 100% { opacity: 1; box-shadow: 0 0 0 0 rgba(39, 174, 96, 0.4); }
  50% { opacity: 0.6; box-shadow: 0 0 0 8rpx rgba(39, 174, 96, 0); }
}

// ── Header ──
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 24rpx;
  background: #0f0f1e;

  .trader-info {
    display: flex;
    align-items: center;

    .trader-avatar {
      width: 72rpx;
      height: 72rpx;
      border-radius: 20rpx;
      display: flex;
      align-items: center;
      justify-content: center;
      margin-right: 16rpx;

      .avatar-text {
        font-size: 32rpx;
        font-weight: 700;
        color: #fff;
      }
    }

    .avatar-managed {
      background: linear-gradient(135deg, #4A90E2, #7B68EE);
      box-shadow: 0 4rpx 16rpx rgba(74, 144, 226, 0.3);
    }

    .avatar-advisory {
      background: linear-gradient(135deg, #f39c12, #e67e22);
      box-shadow: 0 4rpx 16rpx rgba(243, 156, 18, 0.3);
    }

    .trader-meta {
      .trader-name {
        font-size: 30rpx;
        font-weight: 700;
        color: #fff;
        display: block;
      }
      .trader-tag {
        font-size: 22rpx;
        color: #4A90E2;
        margin-top: 4rpx;
      }
    }
  }

  .mode-badge {
    display: flex;
    align-items: center;
    gap: 8rpx;
    padding: 10rpx 20rpx;
    border-radius: 20rpx;
    font-size: 22rpx;
    font-weight: 600;

    .mode-dot {
      width: 10rpx;
      height: 10rpx;
      border-radius: 50%;
      animation: pulse-dot 2s infinite;
    }

    &.managed {
      background: rgba(74, 144, 226, 0.12);
      color: #4A90E2;
      .mode-dot { background: #4A90E2; }
    }

    &.advisory {
      background: rgba(243, 156, 18, 0.12);
      color: #f39c12;
      .mode-dot { background: #f39c12; }
    }
  }
}

// ── Overview Cards ──
.overview-row {
  display: flex;
  gap: 12rpx;
  padding: 0 24rpx 24rpx;

  .ov-card {
    flex: 1;
    background: #13132a;
    border-radius: 16rpx;
    padding: 20rpx 12rpx;
    display: flex;
    flex-direction: column;
    align-items: center;
    border: 1rpx solid rgba(255, 255, 255, 0.04);

    .ov-value {
      font-size: 26rpx;
      font-weight: 700;
      color: #fff;
      font-family: 'DIN Alternate', 'Courier New', monospace;
    }
    .ov-label {
      font-size: 20rpx;
      color: #556677;
      margin-top: 6rpx;
    }

    &.highlight {
      background: rgba(243, 156, 18, 0.06);
      border-color: rgba(243, 156, 18, 0.15);
    }
  }
}

// ── Tabs ──
.tabs {
  display: flex;
  background: #13132a;
  margin: 0 24rpx 20rpx;
  border-radius: 16rpx;
  padding: 6rpx;

  .tab-item {
    flex: 1;
    text-align: center;
    padding: 16rpx 0;
    font-size: 26rpx;
    color: #556677;
    border-radius: 12rpx;
    position: relative;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8rpx;

    &.active {
      background: rgba(74, 144, 226, 0.12);
      color: #4A90E2;
      font-weight: 700;
    }

    .tab-badge {
      font-size: 18rpx;
      background: #f39c12;
      color: #fff;
      padding: 2rpx 10rpx;
      border-radius: 20rpx;
    }
  }
}

// ── Empty State ──
.empty-state {
  text-align: center;
  padding: 100rpx 40rpx;

  .empty-icon {
    font-size: 64rpx;
    color: #2a2a40;
    margin-bottom: 20rpx;
  }

  .empty-title {
    display: block;
    font-size: 28rpx;
    color: #667788;
    font-weight: 600;
    margin-bottom: 12rpx;
  }

  .empty-desc {
    display: block;
    font-size: 22rpx;
    color: #445566;
    line-height: 1.6;
  }
}

// ── Signal Cards ──
.signal-filters {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 8px 12px;
  background: #f9fafb;
  border-bottom: 1px solid #e5e7eb;
}
.filter-input {
  flex: 1 1 100px;
  max-width: 120px;
  height: 30px;
  border: 1px solid #e5e7eb;
  border-radius: 4px;
  padding: 0 8px;
  font-size: 13px;
  background: #fff;
}
.filter-picker {
  height: 30px;
  line-height: 30px;
  padding: 0 8px;
  border: 1px solid #e5e7eb;
  border-radius: 4px;
  font-size: 13px;
  background: #fff;
  color: #6b7280;
  white-space: nowrap;
}
.filter-clear {
  height: 30px;
  line-height: 30px;
  padding: 0 8px;
  cursor: pointer;
}
.filter-clear-text {
  font-size: 13px;
  color: #ef4444;
}

.signal-list {
  padding: 0 24rpx;
}

.signal-card {
  background: #13132a;
  border-radius: 16rpx;
  padding: 24rpx;
  margin-bottom: 16rpx;
  border: 1rpx solid rgba(255, 255, 255, 0.05);
  position: relative;
  overflow: hidden;

  &.auto_executed {
    border-color: rgba(74, 144, 226, 0.15);
    &::before {
      content: '';
      position: absolute;
      top: 0; left: 0; right: 0;
      height: 1rpx;
      background: linear-gradient(90deg, transparent, rgba(74, 144, 226, 0.4), transparent);
    }
  }

  .auto-tag {
    position: absolute;
    top: 12rpx;
    right: 12rpx;
    background: rgba(74, 144, 226, 0.15);
    padding: 4rpx 14rpx;
    border-radius: 8rpx;

    text {
      font-size: 18rpx;
      color: #4A90E2;
      font-weight: 600;
    }
  }

  .sig-head {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 16rpx;

    .sig-stock {
      .sig-symbol {
        font-size: 30rpx;
        font-weight: 700;
        color: #fff;
        margin-right: 12rpx;
      }
      .sig-name {
        font-size: 22rpx;
        color: #667788;
      }
    }

    .sig-action-row {
      display: flex;
      flex-direction: column;
      align-items: flex-end;
      gap: 6rpx;

      .action-buy {
        font-size: 22rpx;
        color: #e74c3c;
        background: rgba(231, 76, 60, 0.1);
        padding: 4rpx 14rpx;
        border-radius: 8rpx;
        font-weight: 600;
      }
      .action-sell {
        font-size: 22rpx;
        color: #27ae60;
        background: rgba(39, 174, 96, 0.1);
        padding: 4rpx 14rpx;
        border-radius: 8rpx;
        font-weight: 600;
      }

      .sig-time {
        font-size: 18rpx;
        color: #445566;
      }
    }
  }

  .sig-body {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 16rpx;
    margin-bottom: 16rpx;

    .sig-item {
      display: flex;
      flex-direction: column;
      gap: 6rpx;

      .sig-label {
        font-size: 20rpx;
        color: #556677;
      }
      .sig-val {
        font-size: 22rpx;
        color: #ddd;
        font-weight: 600;
      }
      .mono {
        font-family: 'DIN Alternate', 'Courier New', monospace;
      }

      .conf-bar-wrap {
        display: flex;
        align-items: center;
        gap: 8rpx;

        .conf-bar {
          flex: 1;
          height: 8rpx;
          background: rgba(255, 255, 255, 0.06);
          border-radius: 4rpx;
          overflow: hidden;

          .conf-fill {
            height: 100%;
            border-radius: 4rpx;
            transition: width 0.8s ease;

            &.high { background: linear-gradient(90deg, #27ae60, #2ecc71); }
            &.mid { background: linear-gradient(90deg, #f39c12, #e67e22); }
            &.low { background: linear-gradient(90deg, #e74c3c, #c0392b); }
          }
        }
      }
    }
  }

  .sig-reason {
    display: flex;
    gap: 10rpx;
    font-size: 22rpx;
    color: #8899aa;
    line-height: 1.5;
    margin-bottom: 16rpx;
    padding: 14rpx;
    background: rgba(255, 255, 255, 0.03);
    border-radius: 10rpx;
    border-left: 4rpx solid rgba(74, 144, 226, 0.3);

    .reason-icon {
      font-size: 22rpx;
      color: #4A90E2;
      flex-shrink: 0;
      margin-top: 2rpx;
    }
  }

  .sig-actions {
    display: flex;
    gap: 16rpx;

    .btn-confirm {
      flex: 1;
      text-align: center;
      padding: 16rpx 0;
      background: linear-gradient(135deg, #4A90E2, #5B9FE8);
      border-radius: 12rpx;
      color: #fff;
      font-size: 26rpx;
      font-weight: 600;
    }
    .btn-ignore {
      flex: 1;
      text-align: center;
      padding: 16rpx 0;
      background: rgba(255, 255, 255, 0.06);
      border-radius: 12rpx;
      color: #8899aa;
      font-size: 26rpx;
    }
  }

  .sig-exec-status {
    text-align: center;
    padding: 8rpx 0;

    .exec-badge {
      display: inline-flex;
      padding: 6rpx 20rpx;
      border-radius: 8rpx;
      font-size: 22rpx;
      font-weight: 600;

      &.done {
        background: rgba(39, 174, 96, 0.1);
        color: #27ae60;
      }
      &.muted {
        background: rgba(255, 255, 255, 0.04);
        color: #667788;
      }
    }
  }
}

// ── Portfolio ──
.portfolio-list {
  padding: 0 24rpx;
}

.portfolio-card {
  background: #13132a;
  border-radius: 16rpx;
  padding: 24rpx;
  margin-bottom: 16rpx;
  border: 1rpx solid rgba(255, 255, 255, 0.05);

  .pos-head {
    display: flex;
    align-items: center;
    gap: 12rpx;
    margin-bottom: 16rpx;

    .pos-symbol {
      font-size: 28rpx;
      font-weight: 700;
      color: #fff;
    }
    .pos-name {
      font-size: 22rpx;
      color: #667788;
    }
    .pos-pnl {
      font-size: 24rpx;
      font-weight: 700;
      margin-left: auto;
    }
  }

  .pos-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16rpx;

    .pos-item {
      display: flex;
      flex-direction: column;
      gap: 4rpx;

      .pos-label {
        font-size: 20rpx;
        color: #556677;
      }
      .pos-val {
        font-size: 24rpx;
        color: #ddd;
        font-weight: 600;
      }
    }
  }
}

// ── Trade List ──
.trade-list {
  padding: 0 24rpx;
}

.trade-card {
  background: #13132a;
  border-radius: 16rpx;
  padding: 20rpx 24rpx;
  margin-bottom: 12rpx;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border: 1rpx solid rgba(255, 255, 255, 0.05);

  .trade-left {
    display: flex;
    align-items: center;
    gap: 16rpx;

    .trade-icon {
      width: 52rpx;
      height: 52rpx;
      border-radius: 14rpx;
      display: flex;
      align-items: center;
      justify-content: center;

      text {
        font-size: 24rpx;
        font-weight: 700;
        color: #fff;
      }

      &.buy { background: rgba(231, 76, 60, 0.15); }
      &.sell { background: rgba(39, 174, 96, 0.15); }
    }

    .trade-info {
      .trade-symbol {
        font-size: 26rpx;
        color: #fff;
        font-weight: 600;
        display: block;
      }
      .trade-name {
        font-size: 20rpx;
        color: #667788;
      }
    }
  }

  .trade-right {
    text-align: right;

    .trade-price {
      font-size: 24rpx;
      color: #fff;
      font-weight: 600;
      display: block;
    }
    .trade-qty {
      font-size: 20rpx;
      color: #8899aa;
    }
    .trade-time {
      font-size: 18rpx;
      color: #445566;
      margin-top: 4rpx;
      display: block;
    }
  }
}

// ── Utility ──
.up { color: #e74c3c; }
.down { color: #27ae60; }
.mono {
  font-family: 'DIN Alternate', 'Courier New', monospace;
}

/* 绩效面板 */
.perf-panel { padding: 12px; }
.perf-loading { text-align: center; padding: 40px 0; color: #999; font-size: 14px; }
.perf-metrics { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 16px; }
.perf-card {
  flex: 1 1 calc(33.33% - 8px); min-width: 100px;
  background: #f9fafb; border-radius: 8px; padding: 10px 12px;
  text-align: center;
}
.perf-label { font-size: 12px; color: #999; display: block; margin-bottom: 4px; }
.perf-value { font-size: 16px; font-weight: 600; color: #333; }
.perf-value.up { color: #e53e3e; }
.perf-value.down { color: #38a169; }
.perf-chart-section { margin-bottom: 16px; }
.perf-section-title { font-size: 14px; font-weight: 600; color: #333; display: block; margin-bottom: 8px; }
.perf-history-row {
  display: flex; align-items: center; padding: 10px 0;
  border-bottom: 1px solid #f0f0f0; gap: 8px;
}
.perf-history-period { font-size: 13px; color: #666; min-width: 80px; }
.perf-history-return { font-size: 14px; font-weight: 600; min-width: 70px; }
.perf-history-sharpe { font-size: 12px; color: #999; }
.perf-history-win { font-size: 12px; color: #999; margin-left: auto; }

</style>
