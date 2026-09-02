<template>
  <view class="live-board-page">
    <!-- 顶部市场状态 -->
    <view class="market-status-bar">
      <view class="market-info">
        <view class="status-dot" :class="marketState === 'trading' ? 'dot-trading' : 'dot-off'"></view>
        <text class="market-text">{{ marketState === 'trading' ? '交易时段 · 实时运行中' : '非交易时段 · 交易员休息中' }}</text>
      </view>
      <view class="sched-badge" :class="{ 'sched-off': !schedulerRunning }">
        {{ schedulerRunning ? '调度运行中' : '调度已暂停' }}
      </view>
    </view>

    <!-- 运行中的交易员状态区 -->
    <view class="agent-status-section">
      <view class="section-title-row">
        <text class="section-title">运行中的交易员</text>
        <text class="section-sub">{{ activeCount }} 个活跃</text>
      </view>
      <view v-if="agents.length === 0" class="status-empty">
        <text class="empty-text">还没有雇佣交易员</text>
        <text class="empty-sub">前往交易员市场雇佣后即可在此查看实时状态</text>
      </view>
      <view v-else class="agent-status-list">
        <view v-for="ag in agents" :key="ag.hire_id" class="agent-status-card" @click="goConsole(ag.hire_id)">
          <view class="agent-head">
            <view class="agent-avatar">
              <text class="avatar-text">{{ ag.trader_name[0] }}</text>
            </view>
            <view class="agent-id">
              <text class="agent-name">{{ ag.trader_name }}</text>
              <text class="agent-tag">{{ ag.trader_tag }}</text>
            </view>
            <view class="runtime-badge" :class="'rt-' + ag.runtime_status">
              <view class="rt-dot"></view>
              <text>{{ ag.runtime_label }}</text>
            </view>
          </view>
          <view class="agent-body">
            <view class="agent-metrics">
              <view class="metric-item">
                <text class="metric-label">实时盈亏</text>
                <text class="metric-value" :class="ag.current_pnl >= 0 ? 'val-up' : 'val-down'">
                  {{ formatPnl(ag.current_pnl) }}
                </text>
              </view>
              <view class="metric-item">
                <text class="metric-label">管理模式</text>
                <text class="metric-value">{{ modeText(ag.management_mode) }}</text>
              </view>
              <view class="metric-item">
                <text class="metric-label">最近动作</text>
                <text class="metric-value metric-last">{{ ag.last_action || '--' }}</text>
              </view>
            </view>
          </view>
        </view>
      </view>
    </view>

    <!-- 资金走势（近30日已实现盈亏累计） -->
    <view class="curve-section">
      <view class="section-title-row">
        <text class="section-title">资金走势</text>
        <text class="section-sub">近30日已实现盈亏累计</text>
      </view>
      <view v-if="curveHires.length === 0" class="curve-empty">
        <text class="empty-text">暂无资金曲线</text>
        <text class="empty-sub">交易员完成止盈/止损平仓后，这里将展示已实现盈亏走势</text>
      </view>
      <view v-else class="curve-card">
        <view class="curve-legend">
          <view v-for="ch in curveHires" :key="ch.hire_id" class="legend-item">
            <view class="legend-dot" :style="{ background: curveColor(ch.hire_id) }"></view>
            <text class="legend-name">{{ ch.trader_name }}</text>
            <text class="legend-pnl" :class="curveLast(ch) >= 0 ? 'pnl-up' : 'pnl-down'">{{ formatPnl(curveLast(ch)) }}</text>
          </view>
        </view>
        <view id="equityChart" class="curve-canvas"></view>
      </view>
    </view>

    <!-- 实时成交记录 -->
    <view class="trades-section">
      <view class="section-title-row">
        <text class="section-title">实时交易记录</text>
        <text class="section-sub">点击记录查看决策理由</text>
      </view>
      <view v-if="trades.length === 0" class="trades-empty">
        <text class="empty-text">暂无成交记录</text>
        <text class="empty-sub">交易员启动后将在这里展示实时交易动态</text>
      </view>
      <view v-else class="trade-list">
        <view v-for="t in trades" :key="t.id" class="trade-card" @click="goDetail(t)">
          <view class="trade-head">
            <view class="trade-side">
              <view class="action-badge" :class="t.action === 'buy' ? 'act-buy' : 'act-sell'">
                {{ t.action === 'buy' ? '买入' : '卖出' }}
              </view>
              <view class="trade-stock">
                <text class="stock-name">{{ t.symbol_name || t.symbol }}</text>
                <text class="stock-code">{{ t.symbol }} · {{ t.market === 'HK' ? '港股' : 'A股' }}</text>
              </view>
            </view>
            <view class="trade-trader">
              <text class="trader-label">交易员</text>
              <text class="trader-name">{{ t.trader_name }}</text>
            </view>
          </view>
          <view class="trade-body">
            <view class="trade-metrics">
              <view class="metric-item">
                <text class="metric-label">成交价</text>
                <text class="metric-value">{{ t.price }}</text>
              </view>
              <view class="metric-item">
                <text class="metric-label">数量</text>
                <text class="metric-value">{{ t.quantity }}</text>
              </view>
              <view class="metric-item">
                <text class="metric-label">信心指数</text>
                <text class="metric-value" :class="confidenceClass(t.confidence)">{{ t.confidence }}%</text>
              </view>
            </view>
            <view class="trade-reason" v-if="t.reasoning">
              <text class="reason-label">决策理由</text>
              <text class="reason-text">{{ truncate(t.reasoning, 36) }}</text>
            </view>
            <view class="trade-foot">
              <text class="trade-status" :class="'st-' + t.exec_status">{{ execText(t.exec_status) }}</text>
              <text class="trade-time">{{ formatTime(t.created_at) }}</text>
            </view>
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, onMounted, onUnmounted } from 'vue'
import { onPullDownRefresh } from '@dcloudio/uni-app'
import { getLiveBoard, type LiveBoardResponse, type LiveBoardTrade, type LiveBoardAgentCurve } from '@/api/agent'
import { formatPercent } from '@/utils/format'
import F2 from '@antv/f2'

const board = ref<LiveBoardResponse>({ agents: [], trades: [], agent_curves: [], scheduler_running: false, market_state: 'off_hours' })
const isLoading = ref(true)

const agents = computed(() => board.value.agents)
const trades = computed(() => board.value.trades)
const marketState = computed(() => board.value.market_state)
const schedulerRunning = computed(() => board.value.scheduler_running)
const activeCount = computed(() => board.value.agents.filter((a: any) => a.status === 'active').length)
const agentCurves = computed(() => board.value.agent_curves || [])
const CURVE_COLORS = ['#4A90E2', '#7B68EE', '#f39c12', '#2ecc71', '#e67e22', '#1abc9c', '#e84393']
const curveColor = (hireId: number) => {
  const idx = agentCurves.value.findIndex((c: LiveBoardAgentCurve) => c.hire_id === hireId)
  return CURVE_COLORS[(idx >= 0 ? idx : 0) % CURVE_COLORS.length]
}
const curveHires = computed(() => (agentCurves.value || []).filter((c: LiveBoardAgentCurve) => c.points.length >= 2))
const curveLast = (c: LiveBoardAgentCurve) => (c.points.length > 0 ? c.points[c.points.length - 1].equity : 0)

let pollTimer: ReturnType<typeof setInterval> | null = null

const loadData = async () => {
  try {
    board.value = await getLiveBoard()
    await nextTick()
    setTimeout(() => renderEquityChart(), 60)
  } catch (e: any) {
    uni.showToast({ title: e?.message || '看板加载失败', icon: 'none' })
  } finally {
    isLoading.value = false
  }
}

const formatPnl = (v: number) => {
  if (v == null) return '--'
  return (v >= 0 ? '+' : '') + v.toFixed(2)
}
const formatPct = (v: number | null | undefined) => {
  if (v == null) return '--'
  return formatPercent(v, 1)
}
const modeText = (m: string) => {
  if (m === 'full_managed') return '全托管'
  if (m === 'advisory') return '顾问'
  return m || '--'
}
const execText = (s: string) => {
  if (s === 'auto_executed') return '已自动成交'
  if (s === 'confirmed') return '已确认成交'
  if (s === 'pending') return '待确认'
  return s || '--'
}
const confidenceClass = (c: number) => {
  if (c >= 70) return 'conf-high'
  if (c >= 50) return 'conf-mid'
  return 'conf-low'
}
const truncate = (s: string, len: number) => {
  if (!s) return ''
  return s.length > len ? s.slice(0, len) + '...' : s
}
const formatTime = (iso: string) => {
  if (!iso) return '--'
  const d = new Date(iso)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

const goConsole = (hireId: number) => {
  uni.navigateTo({ url: `/pages/agent-console/index?hire_id=${hireId}` })
}
const goDetail = (t: LiveBoardTrade) => {
  uni.navigateTo({ url: `/pages/agent-market/signal-detail?id=${t.id}` })
}

onMounted(() => {
  loadData()
  pollTimer = setInterval(loadData, 15000)
})
onUnmounted(() => {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
})
onPullDownRefresh(() => {
  loadData().then(() => uni.stopPullDownRefresh())
})

let equityChart: any = null

const renderEquityChart = () => {
  if (curveHires.value.length === 0) return
  const container = document.getElementById('equityChart')
  if (!container) return

  if (equityChart) {
    try { equityChart.destroy() } catch (e) { /* ignore */ }
    equityChart = null
  }
  container.innerHTML = ''
  const canvas = document.createElement('canvas')
  container.appendChild(canvas)

  const w = container.clientWidth || 340
  const h = 300

  const chart = new F2.Chart({
    el: canvas,
    pixelRatio: window.devicePixelRatio || 1,
    width: w,
    height: h,
    padding: [28, 56, 36, 8]
  })

  const source: any[] = []
  curveHires.value.forEach((ch: LiveBoardAgentCurve) => {
    ch.points.forEach((p) => {
      source.push({ date: p.date, name: ch.trader_name, value: p.equity })
    })
  })
  if (source.length === 0) return

  chart.source(source, {
    date: { range: [0, 1] },
    value: { tickCount: 5 }
  })
  chart.axis('date', {
    label: { fontSize: 9, fill: '#556677', formatter: (v: string) => String(v).slice(5) },
    line: { stroke: 'rgba(255,255,255,0.1)' }
  })
  chart.axis('value', {
    label: { fontSize: 10, fill: '#667788' },
    grid: { stroke: 'rgba(255,255,255,0.06)' },
    line: null
  })
  chart.tooltip({
    showCrosshairs: true,
    crosshairsStyle: { stroke: 'rgba(255,255,255,0.15)' }
  })
  chart.line()
    .position('date*value')
    .color('name', curveHires.value.map((ch: LiveBoardAgentCurve) => curveColor(ch.hire_id)))
    .size(2)
  chart.render()

  equityChart = chart
}
</script>

<style scoped lang="scss">
.live-board-page {
  min-height: 100vh;
  background: #0f0f1a;
  padding: 20rpx 24rpx 120rpx;
}

/* 顶部市场状态 */
.market-status-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: linear-gradient(135deg, #141432 0%, #0f1f3d 100%);
  border-radius: 16rpx;
  padding: 22rpx 28rpx;
  margin-bottom: 24rpx;
  border: 1rpx solid rgba(74, 144, 226, 0.25);

  .market-info {
    display: flex;
    align-items: center;
    gap: 12rpx;

    .market-text {
      font-size: 26rpx;
      color: #c8d6e5;
    }
  }
  .status-dot {
    width: 16rpx;
    height: 16rpx;
    border-radius: 50%;
    &.dot-trading {
      background: #2ecc71;
      box-shadow: 0 0 12rpx rgba(46, 204, 113, 0.8);
      animation: pulse 1.6s infinite;
    }
    &.dot-off {
      background: #7f8c8d;
    }
  }
  .sched-badge {
    font-size: 22rpx;
    color: #2ecc71;
    background: rgba(46, 204, 113, 0.12);
    border-radius: 20rpx;
    padding: 6rpx 20rpx;
    &.sched-off {
      color: #e67e22;
      background: rgba(230, 126, 34, 0.12);
    }
  }
}
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

/* 区块标题 */
.section-title-row {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 20rpx;

  .section-title {
    font-size: 32rpx;
    font-weight: 700;
    color: #ffffff;
  }
  .section-sub {
    font-size: 22rpx;
    color: #667788;
  }
}

/* 交易员状态区 */
.agent-status-section {
  margin-bottom: 36rpx;
}
.agent-status-list {
  display: flex;
  flex-direction: column;
  gap: 20rpx;
}
.agent-status-card {
  background: #16162a;
  border-radius: 16rpx;
  padding: 24rpx;
  border: 1rpx solid rgba(74, 144, 226, 0.15);

  .agent-head {
    display: flex;
    align-items: center;
    gap: 16rpx;

    .agent-avatar {
      width: 72rpx;
      height: 72rpx;
      border-radius: 50%;
      background: linear-gradient(135deg, #4A90E2, #7B68EE);
      display: flex;
      align-items: center;
      justify-content: center;
      .avatar-text {
        color: #fff;
        font-size: 32rpx;
        font-weight: 700;
      }
    }
    .agent-id {
      flex: 1;
      .agent-name {
        font-size: 30rpx;
        font-weight: 600;
        color: #fff;
        display: block;
      }
      .agent-tag {
        font-size: 22rpx;
        color: #667788;
      }
    }
    .runtime-badge {
      display: flex;
      align-items: center;
      gap: 8rpx;
      font-size: 22rpx;
      border-radius: 20rpx;
      padding: 8rpx 18rpx;
      .rt-dot {
        width: 12rpx;
        height: 12rpx;
        border-radius: 50%;
      }
      &.rt-trading {
        color: #2ecc71;
        background: rgba(46, 204, 113, 0.12);
        .rt-dot { background: #2ecc71; animation: pulse 1.6s infinite; }
      }
      &.rt-resting {
        color: #95a5a6;
        background: rgba(149, 165, 166, 0.12);
        .rt-dot { background: #95a5a6; }
      }
      &.rt-paused {
        color: #e67e22;
        background: rgba(230, 126, 34, 0.12);
        .rt-dot { background: #e67e22; }
      }
      &.rt-configuring {
        color: #f1c40f;
        background: rgba(241, 196, 15, 0.12);
        .rt-dot { background: #f1c40f; }
      }
      &.rt-expired {
        color: #e74c3c;
        background: rgba(231, 76, 60, 0.12);
        .rt-dot { background: #e74c3c; }
      }
    }
  }
  .agent-body {
    margin-top: 18rpx;
    .agent-metrics {
      display: flex;
      gap: 24rpx;
      .metric-item {
        flex: 1;
        .metric-label {
          font-size: 20rpx;
          color: #556677;
          display: block;
        }
        .metric-value {
          font-size: 26rpx;
          color: #c8d6e5;
          font-weight: 600;
          &.val-up { color: #e74c3c; }
          &.val-down { color: #2ecc71; }
        }
        .metric-last {
          font-size: 22rpx;
          color: #8899aa;
          font-weight: 400;
        }
      }
    }
  }
}

/* 成交记录 */
.trades-section {
  margin-top: 8rpx;
}
.trade-list {
  display: flex;
  flex-direction: column;
  gap: 20rpx;
}
.trade-card {
  background: #16162a;
  border-radius: 16rpx;
  padding: 24rpx;
  border: 1rpx solid rgba(74, 144, 226, 0.12);

  .trade-head {
    display: flex;
    justify-content: space-between;
    align-items: center;
    .trade-side {
      display: flex;
      align-items: center;
      gap: 16rpx;
      .action-badge {
        font-size: 24rpx;
        font-weight: 600;
        border-radius: 10rpx;
        padding: 8rpx 20rpx;
        &.act-buy { color: #e74c3c; background: rgba(231, 76, 60, 0.15); }
        &.act-sell { color: #2ecc71; background: rgba(46, 204, 113, 0.15); }
      }
      .trade-stock {
        .stock-name {
          font-size: 30rpx;
          font-weight: 600;
          color: #fff;
          display: block;
        }
        .stock-code {
          font-size: 20rpx;
          color: #556677;
        }
      }
    }
    .trade-trader {
      text-align: right;
      .trader-label {
        font-size: 20rpx;
        color: #556677;
        display: block;
      }
      .trader-name {
        font-size: 26rpx;
        color: #4A90E2;
        font-weight: 600;
      }
    }
  }
  .trade-body {
    margin-top: 16rpx;
    border-top: 1rpx solid rgba(255, 255, 255, 0.05);
    padding-top: 16rpx;
    .trade-metrics {
      display: flex;
      gap: 24rpx;
      .metric-item {
        .metric-label {
          font-size: 20rpx;
          color: #556677;
          display: block;
        }
        .metric-value {
          font-size: 26rpx;
          color: #c8d6e5;
          font-weight: 600;
          &.conf-high { color: #2ecc71; }
          &.conf-mid { color: #f1c40f; }
          &.conf-low { color: #e67e22; }
        }
      }
    }
    .trade-reason {
      margin-top: 12rpx;
      background: rgba(74, 144, 226, 0.08);
      border-radius: 10rpx;
      padding: 12rpx 16rpx;
      .reason-label {
        font-size: 20rpx;
        color: #4A90E2;
        display: block;
        margin-bottom: 4rpx;
      }
      .reason-text {
        font-size: 24rpx;
        color: #8899aa;
      }
    }
    .trade-foot {
      display: flex;
      justify-content: space-between;
      margin-top: 14rpx;
      .trade-status {
        font-size: 20rpx;
        &.st-auto_executed { color: #2ecc71; }
        &.st-confirmed { color: #4A90E2; }
        &.st-pending { color: #e67e22; }
      }
      .trade-time {
        font-size: 20rpx;
        color: #556677;
      }
    }
  }
}

.curve-section {
  margin-bottom: 36rpx;
}
.curve-card {
  background: #16162a;
  border-radius: 16rpx;
  padding: 24rpx 16rpx;
  border: 1rpx solid rgba(74, 144, 226, 0.15);
}
.curve-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 20rpx;
  padding: 0 8rpx 16rpx;
  .legend-item {
    display: flex;
    align-items: center;
    gap: 10rpx;
    .legend-dot {
      width: 16rpx;
      height: 16rpx;
      border-radius: 50%;
    }
    .legend-name {
      font-size: 22rpx;
      color: #c8d6e5;
    }
    .legend-pnl {
      font-size: 20rpx;
      font-weight: 600;
      &.pnl-up { color: #e74c3c; }
      &.pnl-down { color: #2ecc71; }
    }
  }
}
.curve-canvas {
  width: 100%;
  height: 300px;
  position: relative;
}
.curve-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 64rpx 0;
  background: #16162a;
  border-radius: 16rpx;
  color: #999;
  .empty-text {
    font-size: 28rpx;
    color: #8899aa;
  }
  .empty-sub {
    font-size: 22rpx;
    color: #556677;
    margin-top: 10rpx;
  }
}

.status-empty, .trades-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80rpx 0;
  background: #16162a;
  border-radius: 16rpx;
  color: #999;
  .empty-text {
    font-size: 28rpx;
    color: #8899aa;
  }
  .empty-sub {
    font-size: 22rpx;
    color: #556677;
    margin-top: 10rpx;
  }
}
</style>
