<template>
  <view class="agent-detail-page">
    <!-- 返回按钮 -->
    <view class="back-bar">
      <text class="back-btn" @click="goBack">&lt; 返回市场</text>
    </view>

    <!-- 加载中 -->
    <view v-if="loading" class="loading-box">
      <text class="loading-text">加载中...</text>
    </view>

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
        <canvas
          canvas-id="radarCanvas"
          id="radarCanvas"
          class="radar-canvas"
          @touchstart="noop"
        />
        <view class="radar-legend">
          <text class="legend-item" v-for="item in legendItems" :key="item.label">
            {{ item.label }}: {{ item.value }}
          </text>
        </view>
      </view>

      <!-- 收益曲线 -->
      <view class="perf-chart-section" v-if="salaryCurve.length > 0">
        <text class="section-title">收益曲线</text>
        <canvas
          canvas-id="chartCanvas"
          id="chartCanvas"
          class="chart-canvas"
          @touchstart="noop"
        />
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
import { getAgentDetail, hireAgent } from '@/api/agent'
import { getPointsBalance } from '@/api/points'

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
    nextTick(() => {
      drawRadar()
      drawChart()
    })
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
    uni.showToast({ title: '雇佣成功！', icon: 'success' })
    showHireModal.value = false
    setTimeout(() => uni.navigateBack(), 1200)
  } catch (e: any) {
    const msg = e?.response?.data?.detail || e?.message || '雇佣失败'
    uni.showToast({ title: msg, icon: 'none' })
  } finally {
    hiring.value = false
  }
}

const goBack = () => uni.navigateBack()

// ── Radar Chart ──
const drawRadar = () => {
  if (!radarScores.value) return
  const labels = Object.keys(radarScores.value)
  const values = labels.map(k => radarScores.value![k] || 0)
  const n = labels.length
  if (n === 0) return

  // Using uni.createSelectorQuery for H5 compatibility
  const query = uni.createSelectorQuery()
  query.select('#radarCanvas').fields({ node: true, size: true }).exec((res: any) => {
    const info = res[0]
    if (!info) return
    const w = info.width || 300
    const h = info.height || 260
    const cx = w / 2
    const cy = h / 2
    const r = Math.min(cx, cy) - 30
    const ctx = uni.createCanvasContext('radarCanvas')

    // Background grid
    for (let level = 1; level <= 5; level++) {
      const rr = (r * level) / 5
      ctx.beginPath()
      for (let i = 0; i < n; i++) {
        const angle = (Math.PI * 2 * i) / n - Math.PI / 2
        const x = cx + rr * Math.cos(angle)
        const y = cy + rr * Math.sin(angle)
        if (i === 0) ctx.moveTo(x, y)
        else ctx.lineTo(x, y)
      }
      ctx.closePath()
      ctx.setStrokeStyle('rgba(255,255,255,0.1)')
      ctx.stroke()
    }

    // Axis lines
    for (let i = 0; i < n; i++) {
      const angle = (Math.PI * 2 * i) / n - Math.PI / 2
      ctx.beginPath()
      ctx.moveTo(cx, cy)
      ctx.lineTo(cx + r * Math.cos(angle), cy + r * Math.sin(angle))
      ctx.setStrokeStyle('rgba(255,255,255,0.15)')
      ctx.stroke()
    }

    // Data polygon
    ctx.beginPath()
    for (let i = 0; i < n; i++) {
      const angle = (Math.PI * 2 * i) / n - Math.PI / 2
      const val = Math.max(0, Math.min(10, values[i])) / 10
      const x = cx + r * val * Math.cos(angle)
      const y = cy + r * val * Math.sin(angle)
      if (i === 0) ctx.moveTo(x, y)
      else ctx.lineTo(x, y)
    }
    ctx.closePath()
    ctx.setFillStyle('rgba(74, 144, 226, 0.2)')
    ctx.fill()
    ctx.setStrokeStyle('#4A90E2')
    ctx.setLineWidth(2)
    ctx.stroke()

    // Data points
    for (let i = 0; i < n; i++) {
      const angle = (Math.PI * 2 * i) / n - Math.PI / 2
      const val = Math.max(0, Math.min(10, values[i])) / 10
      const x = cx + r * val * Math.cos(angle)
      const y = cy + r * val * Math.sin(angle)
      ctx.beginPath()
      ctx.arc(x, y, 4, 0, Math.PI * 2)
      ctx.setFillStyle('#4A90E2')
      ctx.fill()
    }

    // Labels
    for (let i = 0; i < n; i++) {
      const angle = (Math.PI * 2 * i) / n - Math.PI / 2
      const lr = r + 24
      const lx = cx + lr * Math.cos(angle)
      const ly = cy + lr * Math.sin(angle)
      ctx.setFontSize(11)
      ctx.setFillStyle('#8899aa')
      ctx.setTextAlign('center')
      ctx.fillText(radarLabels[labels[i]] || labels[i], lx, ly + 5)
    }

    ctx.draw()
  })
}

// ── Performance Curve ──
const drawChart = () => {
  const curve = salaryCurve.value
  if (!curve || curve.length === 0) return

  const query = uni.createSelectorQuery()
  query.select('#chartCanvas').fields({ node: true, size: true }).exec((res: any) => {
    const info = res[0]
    if (!info) return
    const w = info.width || 340
    const h = info.height || 220
    const pad = { top: 16, right: 16, bottom: 32, left: 40 }
    const pw = w - pad.left - pad.right
    const ph = h - pad.top - pad.bottom

    const ctx = uni.createCanvasContext('chartCanvas')
    const data = curve.map(c => c.value)
    const minVal = Math.min(...data, 0)
    const maxVal = Math.max(...data, 0)
    const range = maxVal - minVal || 1

    // Background
    ctx.setFillStyle('#1a1a2e')
    ctx.fillRect(0, 0, w, h)

    // Grid lines
    for (let i = 0; i <= 4; i++) {
      const y = pad.top + (ph * i) / 4
      ctx.beginPath()
      ctx.moveTo(pad.left, y)
      ctx.lineTo(w - pad.right, y)
      ctx.setStrokeStyle('rgba(255,255,255,0.06)')
      ctx.stroke()

      const val = maxVal - (range * i) / 4
      ctx.setFontSize(10)
      ctx.setFillStyle('#667788')
      ctx.setTextAlign('right')
      ctx.fillText(val.toFixed(1) + '%', pad.left - 6, y + 3)
    }

    // Zero line
    if (minVal < 0 && maxVal > 0) {
      const zy = pad.top + ph * (maxVal / range)
      ctx.beginPath()
      ctx.moveTo(pad.left, zy)
      ctx.lineTo(w - pad.right, zy)
      ctx.setStrokeStyle('rgba(255,255,255,0.1)')
      ctx.stroke()
    }

    // Gradient fill
    if (data.length > 1) {
      ctx.beginPath()
      for (let i = 0; i < data.length; i++) {
        const x = pad.left + (pw * i) / (data.length - 1)
        const y = pad.top + ph * (1 - (data[i] - minVal) / range)
        if (i === 0) ctx.moveTo(x, y)
        else ctx.lineTo(x, y)
      }
      // Close to bottom
      ctx.lineTo(pad.left + pw, pad.top + ph)
      ctx.lineTo(pad.left, pad.top + ph)
      ctx.closePath()
      ctx.setFillStyle('rgba(74,144,226,0.08)')
      ctx.fill()
    }

    // Line
    ctx.beginPath()
    for (let i = 0; i < data.length; i++) {
      const x = pad.left + (pw * i) / (data.length - 1)
      const y = pad.top + ph * (1 - (data[i] - minVal) / range)
      if (i === 0) ctx.moveTo(x, y)
      else ctx.lineTo(x, y)
    }
    ctx.setStrokeStyle('#4A90E2')
    ctx.setLineWidth(2)
    ctx.setLineCap('round')
    ctx.stroke()

    // Dots
    for (let i = 0; i < data.length; i++) {
      const x = pad.left + (pw * i) / (data.length - 1)
      const y = pad.top + ph * (1 - (data[i] - minVal) / range)
      ctx.beginPath()
      ctx.arc(x, y, 3, 0, Math.PI * 2)
      ctx.setFillStyle(i === data.length - 1 ? '#4ade80' : '#4A90E2')
      ctx.fill()
    }

    // X labels
    if (data.length > 1) {
      const first = curve[0]
      const last = curve[curve.length - 1]
      ctx.setFontSize(9)
      ctx.setFillStyle('#556677')
      ctx.setTextAlign('left')
      if (first && first.date) ctx.fillText(first.date.substring(0, 10), pad.left, h - 6)
      ctx.setTextAlign('right')
      if (last && last.date) ctx.fillText(last.date.substring(0, 10), w - pad.right, h - 6)
    }

    ctx.draw()
  })
}

const formatPct = (v: number | null | undefined) => {
  if (v == null) return '--'
  return (v * 100).toFixed(2) + '%'
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
    .m-value { font-size: 32rpx; font-weight: 700; font-family: 'DIN Alternate', monospace; }
    .m-label { font-size: 22rpx; color: #667788; display: block; margin-top: 4rpx; }
  }
}

// Radar
.radar-section { padding: 24rpx; margin: 0 24rpx 24rpx; background: #1a1a2e; border-radius: 20rpx; }
.radar-canvas { width: 100%; height: 280rpx; margin-top: 12rpx; }
.radar-legend {
  display: flex; flex-wrap: wrap; margin-top: 12rpx; justify-content: center;
  .legend-item {
    font-size: 22rpx; color: #667788; margin: 4rpx 16rpx;
  }
}

// Chart
.perf-chart-section { padding: 24rpx; margin: 0 24rpx 24rpx; background: #1a1a2e; border-radius: 20rpx; }
.chart-canvas { width: 100%; height: 240rpx; margin-top: 12rpx; }

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
