<template>
  <view class="agent-detail-page">
    <!-- 返回按钮 -->
    <view class="back-bar">
      <text class="back-btn" @click="goBack">&lt; 返回市场</text>
    </view>

    <!-- 加载中 -->
    <SkeletonScreen v-if="loading" type="detail" />

    <template v-else-if="agent">
      <!-- 头像 + 名称 -->
      <view class="hero-section">
        <view class="hero-avatar">
          <text class="hero-avatar-text">{{ agent.code_name[0] }}</text>
        </view>
        <text class="hero-name">{{ agent.code_name }}</text>
        <text class="hero-tag">{{ agent.tag }}</text>
        <text class="hero-masters">{{ agent.masters }}</text>

        <view v-if="agent.is_hired" class="hired-status">
          <text class="hired-mode">{{ managementModeLabel }}</text>
          <text class="hired-date">雇佣于 {{ formatDate(agent.hired_at) }}</text>
        </view>
      </view>

      <!-- 业绩指标 -->
      <view class="metrics-section">
        <text class="section-title">历史业绩</text>
        <view class="metrics-grid">
          <view class="m-item">
            <text class="m-value" :class="(agent.annual_return || 0) > 0 ? 'up' : 'down'">
              {{ formatPct(agent.annual_return) }}
            </text>
            <text class="m-label">年化收益</text>
          </view>
          <view class="m-item">
            <text class="m-value down">{{ formatPct(agent.max_drawdown) }}</text>
            <text class="m-label">最大回撤</text>
          </view>
          <view class="m-item">
            <text class="m-value">{{ agent.sharpe_ratio }}</text>
            <text class="m-label">夏普比率</text>
          </view>
          <view class="m-item">
            <text class="m-value">{{ formatPct(agent.win_rate) }}</text>
            <text class="m-label">胜率</text>
          </view>
          <view class="m-item">
            <text class="m-value">{{ agent.total_trades }}</text>
            <text class="m-label">总交易数</text>
          </view>
          <view class="m-item">
            <text class="m-value">{{ agent.profit_share_pct }}%</text>
            <text class="m-label">盈利分成</text>
          </view>
        </view>
      </view>

      <!-- 雷达图 -->
      <view class="radar-section" v-if="radarScores">
        <text class="section-title">能力雷达图</text>
        <view id="radarContainer" class="chart-container"></view>
        <view class="radar-legend">
          <text class="legend-item" v-for="item in legendItems" :key="item.label">
            {{ item.label }}: {{ item.value }}
          </text>
        </view>
      </view>

      <!-- 收益曲线 -->
      <view class="perf-chart-section" v-if="salaryCurve.length > 0">
        <text class="section-title">收益曲线</text>
        <view id="chartContainer" class="chart-container"></view>
      </view>

      <!-- 近期表现 -->
      <view class="perf-section" v-if="agent.recent_performances && agent.recent_performances.length">
        <text class="section-title">近期表现</text>
        <view class="perf-list">
          <view class="perf-row" v-for="p in agent.recent_performances" :key="p.period_end">
            <text class="perf-period">{{ p.period }}</text>
            <text class="perf-ret" :class="p.return_pct > 0 ? 'up' : 'down'">
              {{ (p.return_pct > 0 ? '+' : '') + formatPct(p.return_pct) }}
            </text>
          </view>
        </view>
      </view>

      <!-- 策略介绍 -->
      <view class="strategy-section">
        <text class="section-title">策略介绍</text>
        <text class="strategy-text">{{ agent.strategy_detail || agent.description }}</text>
      </view>

      <!-- 交易理念 -->
      <view class="desc-section">
        <text class="section-title">投资哲学</text>
        <text class="desc-text">{{ agent.philosophy || agent.description }}</text>
      </view>


      <!-- 底部雇佣栏 -->
      <view class="bottom-bar">
        <template v-if="agent.is_hired">
          <view class="bottom-hired">
            <text class="bottom-hired-text">已雇佣 · {{ managementModeLabel }}</text>
          </view>
        </template>
        <template v-else>
          <view class="bottom-price">
            <text class="bottom-price-val">{{ agent.hire_price_points }}</text>
            <text class="bottom-price-unit">积分/30天</text>
          </view>
          <view class="bottom-btn" @click="showHireModal = true">
            <text>雇佣交易员</text>
          </view>
        </template>
      </view>
    </template>

    <!-- 雇佣确认弹窗 -->
    <view class="modal-mask" v-if="showHireModal" @click="showHireModal = false">
      <view class="modal-box" @click.stop>
        <text class="modal-title">确认雇佣</text>

        <view class="modal-agent-info">
          <text class="modal-agent-name">{{ agent?.code_name }}</text>
          <text class="modal-agent-tag">{{ agent?.tag }}</text>
        </view>

        <view class="modal-fields">
          <view class="modal-field">
            <text class="modal-field-label">所需积分</text>
            <text class="modal-field-val price">{{ agent?.hire_price_points }} 积分</text>
          </view>
          <view class="modal-field">
            <text class="modal-field-label">当前余额</text>
            <text class="modal-field-val" :class="userBalance >= (agent?.hire_price_points || 0) ? 'enough' : 'lack'">
              {{ userBalance }} 积分
            </text>
          </view>
          <view class="modal-field">
            <text class="modal-field-label">管理模式</text>
            <view class="modal-mode-select">
              <view
                :class="['mode-option', hireMode === 'advisory' ? 'mode-active' : '']"
                @click="hireMode = 'advisory'"
              >
                <text>建议模式</text>
              </view>
              <view
                :class="['mode-option', hireMode === 'full_managed' ? 'mode-active' : '']"
                @click="hireMode = 'full_managed'"
              >
                <text>完全托管</text>
              </view>
            </view>
          </view>
        </view>

        <view class="modal-actions">
          <view class="modal-btn cancel" @click="showHireModal = false">
            <text>取消</text>
          </view>
          <view class="modal-btn confirm" @click="doHire">
            <text>{{ hiring ? '雇佣中...' : '确认雇佣' }}</text>
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue'
import F2 from '@antv/f2'
import SkeletonScreen from '@/components/common/SkeletonScreen.vue'
import { getAgentDetail, hireAgent } from '@/api/agent'
import { getPointsBalance } from '@/api/points'
import { formatPercent } from '@/utils/format'

const agent = ref<any>(null)
const loading = ref(true)
const showHireModal = ref(false)
const hireMode = ref('advisory')
const hiring = ref(false)
const userBalance = ref(0)
const radarScores = ref<Record<string, number> | null>(null)
const salaryCurve = ref<{ date: string; value: number }[]>([])
const legendItems = ref<{ label: string; value: number }[]>([])

const managementModeLabel = ref('')

const radarLabels: Record<string, string> = {
  stock_picking: '选股能力',
  timing: '择时能力',
  risk_control: '风险控制',
  industry_research: '行业研究',
  position_management: '仓位管理',
  stability: '稳定性',
}

const loadData = async (agentId: string) => {
  try {
    loading.value = true
    const [detailRes, balRes] = await Promise.allSettled([
      getAgentDetail(agentId),
      getPointsBalance(),
    ])

    if (detailRes.status === 'fulfilled' && detailRes.value) {
      agent.value = detailRes.value.data || detailRes.value
      managementModeLabel.value = (agent.value?.management_mode === 'full_managed')
        ? '完全托管' : '建议模式'

      if (agent.value?.radar_scores) {
        radarScores.value = agent.value.radar_scores
        legendItems.value = Object.entries(agent.value.radar_scores).map(([k, v]) => ({
          label: radarLabels[k] || k,
          value: v as number,
        }))
      }

      if (agent.value?.salary_curve && agent.value.salary_curve.length > 0) {
        salaryCurve.value = agent.value.salary_curve
      } else if (agent.value?.recent_performances) {
        salaryCurve.value = agent.value.recent_performances.map((p: any) => ({
          date: p.period_end,
          value: p.return_pct * 100,
        })).reverse()
      }
    }

    if (balRes.status === 'fulfilled' && balRes.value) {
      const balData = balRes.value.data || balRes.value
      userBalance.value = balData.balance ?? 0
    }

    await nextTick()
    // Use setTimeout to ensure canvas is ready
    setTimeout(() => {
      renderRadar()
      renderChart()
    }, 300)
  } catch (e) {
    console.error('加载交易员详情失败', e)
    uni.showToast({ title: '加载失败', icon: 'none' })
  } finally {
    loading.value = false
  }
}

const doHire = async () => {
  if (!agent.value) return
  hiring.value = true
  try {
    const result = await hireAgent(agent.value.id, hireMode.value)
    const data = (result as any).data || result
    const userAgentId = data.user_agent_id
    showHireModal.value = false
    uni.navigateTo({ url: '/pages/agent-config/index?hire_id=' + userAgentId })
  } catch (e: any) {
    const msg = e?.response?.data?.detail || e?.message || '雇佣失败'
    uni.showToast({ title: msg, icon: 'none' })
  } finally {
    hiring.value = false
  }
}

const goBack = () => uni.navigateBack()

// ── Radar Chart (F2) ──
let radarChart: any = null

const renderRadar = () => {
  if (!radarScores.value) return
  // 固定轴序：正上→右上→右→右下→下→左下（顺时针）
  const radarOrder = ['position_management', 'industry_research', 'stock_picking', 'risk_control', 'stability', 'timing']
  const labels = radarOrder.filter(k => k in radarScores.value!)
  const values = labels.map(k => radarScores.value![k] || 0)
  if (labels.length === 0) return

  const container = document.getElementById('radarContainer')
  if (!container) return

  if (radarChart) {
    radarChart.destroy()
    radarChart = null
  }

  // Clear container
  container.innerHTML = ''
  const radarCanvas = document.createElement('canvas')
  container.appendChild(radarCanvas)

  const data = labels.map((k, i) => ({
    item: radarLabels[k] || k,
    score: values[i]
  }))

  const w = container.clientWidth || 300
  const h = 280

  const chart = new F2.Chart({
    el: radarCanvas,
    pixelRatio: window.devicePixelRatio || 1,
    width: w,
    height: h,
    padding: [40, 40, 40, 40]
  })

  chart.source(data, {
    score: { min: 0, max: 10, tickCount: 5 }
  })
  chart.coord('polar', {
    transposed: false,
    inner: 0
  })
  chart.axis('score', {
    grid: { type: 'line', lineDash: null },
    label: { fontSize: 10, fill: '#667788' },
    line: null
  })
  chart.axis('item', {
    grid: { lineDash: null },
    label: { fontSize: 11, fill: '#8899aa' },
    line: null
  })
  chart.area()
    .position('item*score')
    .color('rgba(74,144,226,0.15)')
  chart.line()
    .position('item*score')
    .color('#4A90E2')
    .size(2)
  chart.point()
    .position('item*score')
    .color('#4A90E2')
    .size(4)
  chart.render()

  radarChart = chart
}

// ── Performance Curve (F2) ──
let lineChart: any = null

const renderChart = () => {
  const curve = salaryCurve.value
  if (!curve || curve.length === 0) return

  const container = document.getElementById('chartContainer')
  if (!container) return

  if (lineChart) {
    lineChart.destroy()
    lineChart = null
  }

  container.innerHTML = ''
  const lineCanvas = document.createElement('canvas')
  container.appendChild(lineCanvas)

  const w = container.clientWidth || 340
  const h = 260

  const chart = new F2.Chart({
    el: lineCanvas,
    pixelRatio: window.devicePixelRatio || 1,
    width: w,
    height: h,
    padding: [20, 16, 36, 44]
  })

  const source = curve.map(c => ({
    date: c.period || c.date,
    value: c.value
  }))

  chart.source(source, {
    value: { tickCount: 5 }
  })
  chart.axis('date', {
    label: { fontSize: 9, fill: '#556677' },
    line: { stroke: 'rgba(255,255,255,0.1)' }
  })
  chart.axis('value', {
    label: { fontSize: 10, fill: '#667788' },
    grid: { stroke: 'rgba(255,255,255,0.06)' },
    line: null
  })
  chart.area()
    .position('date*value')
    .color('rgba(74,144,226,0.08)')
  chart.line()
    .position('date*value')
    .color('#4A90E2')
    .size(2)
  chart.point()
    .position('date*value')
    .color('value', (val: number) => {
      const last = source[source.length - 1]
      return (val === last.value && source.length > 1) ? '#4ade80' : '#4A90E2'
    })
    .size(3)
  chart.render()

  lineChart = chart
}

const formatPct = (v: number | null | undefined) => {
  if (v == null) return '--'
  return formatPercent(v, 2)
}

const formatDate = (d: string | null) => {
  if (!d) return ''
  return d.substring(0, 10)
}

const noop = () => {}

onMounted(() => {
  // Uni-App onLoad equivalent - get route query
  const pages = getCurrentPages()
  const page = pages[pages.length - 1]
      const options = (page as any)?.options || {}
      if (options.id) {
        loadData(options.id)
  }
})
</script>

<style scoped lang="scss">
.agent-detail-page {
  min-height: 100vh;
  background: #0f0f1a;
  padding-bottom: 180rpx;
}

.back-bar {
  padding: 16rpx 24rpx;
  .back-btn { font-size: 28rpx; color: #4A90E2; }
}

.loading-box {
  display: flex;
  justify-content: center;
  padding: 100rpx;
  .loading-text { color: #667788; font-size: 28rpx; }
}

.hero-section {
  text-align: center;
  padding: 40rpx 24rpx 32rpx;

  .hero-avatar {
    width: 120rpx; height: 120rpx;
    border-radius: 32rpx;
    background: linear-gradient(135deg, #4A90E2, #7B68EE);
    display: flex; align-items: center; justify-content: center;
    margin: 0 auto 24rpx;

    .hero-avatar-text { font-size: 56rpx; font-weight: 700; color: #fff; }
  }

  .hero-name { font-size: 44rpx; font-weight: 700; color: #fff; display: block; }
  .hero-tag { font-size: 28rpx; color: #4A90E2; display: block; margin-top: 8rpx; }
  .hero-masters { font-size: 24rpx; color: #667788; display: block; margin-top: 12rpx; }

  .hired-status {
    margin-top: 24rpx; padding: 16rpx 32rpx;
    background: rgba(39, 174, 96, 0.12); border-radius: 12rpx; display: inline-block;

    .hired-mode { font-size: 26rpx; color: #27ae60; font-weight: 600; }
    .hired-date { font-size: 22rpx; color: #667788; display: block; margin-top: 4rpx; }
  }
}

.section-title { font-size: 32rpx; font-weight: 700; color: #fff; display: block; margin-bottom: 20rpx; }

.metrics-section { padding: 24rpx; margin: 0 24rpx 24rpx; background: #1a1a2e; border-radius: 20rpx; }

.metrics-grid {
  display: flex; flex-wrap: wrap;
  .m-item {
    width: 33.33%; text-align: center; padding: 16rpx 0;
    .m-value { font-size: 32rpx; font-weight: 700; font-family: "DIN Alternate", monospace; color: #e0e0e0; }
    .m-label { font-size: 22rpx; color: #667788; display: block; margin-top: 4rpx; }
  }
}

// Radar
.radar-section { padding: 24rpx; margin: 0 24rpx 24rpx; background: #1a1a2e; border-radius: 20rpx; }
.chart-container { width: 100%; height: 300px; margin-top: 12rpx; background: transparent; }
.radar-legend {
  display: flex; flex-wrap: wrap; margin-top: 12rpx; justify-content: center;
  .legend-item {
    font-size: 22rpx; color: #667788; margin: 4rpx 16rpx;
  }
}

// Chart
.perf-chart-section { padding: 24rpx; margin: 0 24rpx 24rpx; background: #1a1a2e; border-radius: 20rpx; }
/* chart moved to .chart-container */

.strategy-section, .desc-section {
  padding: 24rpx; margin: 0 24rpx 24rpx; background: #1a1a2e; border-radius: 20rpx;
  .strategy-text, .desc-text { font-size: 26rpx; color: #99aabb; line-height: 1.6; }
}

.perf-section { padding: 24rpx; margin: 0 24rpx 24rpx; background: #1a1a2e; border-radius: 20rpx; }
.perf-list {
  .perf-row {
    display: flex; justify-content: space-between; padding: 16rpx 0;
    border-bottom: 1rpx solid rgba(255,255,255,0.04);
    .perf-period { font-size: 26rpx; color: #8899aa; }
    .perf-ret { font-size: 28rpx; font-weight: 600; }
  }
}

// Modal
.modal-mask {
  position: fixed; top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.65);
  display: flex; align-items: center; justify-content: center;
  z-index: 999;
}
.modal-box {
  width: 600rpx; background: #1a1a2e; border-radius: 24rpx; padding: 40rpx 32rpx 32rpx;
}
.modal-title { font-size: 36rpx; font-weight: 700; color: #fff; display: block; text-align: center; margin-bottom: 28rpx; }
.modal-agent-info { text-align: center; margin-bottom: 24rpx; }
.modal-agent-name { font-size: 32rpx; font-weight: 600; color: #e0e0e0; }
.modal-agent-tag { font-size: 24rpx; color: #667788; display: block; margin-top: 4rpx; }
.modal-fields { background: rgba(255,255,255,0.04); border-radius: 12rpx; padding: 20rpx 24rpx; margin-bottom: 28rpx; }
.modal-field {
  display: flex; justify-content: space-between; align-items: center; padding: 12rpx 0;
  .modal-field-label { font-size: 26rpx; color: #8899aa; }
  .modal-field-val { font-size: 28rpx; font-weight: 600; color: #ddd; }
  .price { color: #f0c060; }
  .enough { color: #4ade80; }
  .lack { color: #ef4444; }
}
.modal-mode-select { display: flex; gap: 12rpx; }
.mode-option {
  padding: 10rpx 24rpx; border-radius: 8rpx; border: 1rpx solid rgba(255,255,255,0.12);
  font-size: 24rpx; color: #667788;
}
.mode-active { border-color: #4A90E2; color: #4A90E2; background: rgba(74,144,226,0.1); }
.modal-actions { display: flex; gap: 16rpx; }
.modal-btn {
  flex: 1; text-align: center; padding: 22rpx 0; border-radius: 16rpx; font-size: 28rpx;
  &.cancel { background: rgba(255,255,255,0.08); color: #8899aa; }
  &.confirm { background: linear-gradient(135deg, #4A90E2, #7B68EE); color: #fff; font-weight: 600; }
}

.bottom-bar {
  position: fixed; bottom: 0; left: 0; right: 0;
  padding: 24rpx 32rpx;
  padding-bottom: calc(24rpx + env(safe-area-inset-bottom));
  background: #1a1a2e; border-top: 1rpx solid rgba(255,255,255,0.06);
  display: flex; justify-content: space-between; align-items: center;

  .bottom-price { display: flex; align-items: baseline; }
  .bottom-price-val { font-size: 40rpx; font-weight: 700; color: #f0c060; }
  .bottom-price-unit { font-size: 26rpx; color: #667788; margin-left: 6rpx; }
  .bottom-btn {
    background: linear-gradient(135deg, #4A90E2, #7B68EE);
    color: #fff; font-size: 30rpx; padding: 20rpx 48rpx; border-radius: 32rpx; font-weight: 500;
  }
  .bottom-hired { width: 100%; text-align: center; }
  .bottom-hired-text { font-size: 28rpx; color: #27ae60; font-weight: 500; }
}

.up { color: #e74c3c; }
.down { color: #27ae60; }
</style>
