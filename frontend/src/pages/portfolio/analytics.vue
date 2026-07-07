<template>
  <view class="analytics-page">
    <!-- 看板概览 -->
    <view class="section" v-if="dashboard">
      <view class="section-title">看板概览</view>
      <view class="dashboard-grid">
        <view class="dash-item">
          <text class="dash-label">总收益率</text>
          <text class="dash-value" :class="dashboard.totalReturn >= 0 ? 'up' : 'down'">
            {{ dashboard.totalReturn >= 0 ? '+' : '' }}{{ dashboard.totalReturn.toFixed(2) }}%
          </text>
        </view>
        <view class="dash-item">
          <text class="dash-label">年化收益</text>
          <text class="dash-value" :class="dashboard.annualizedReturn >= 0 ? 'up' : 'down'">
            {{ dashboard.annualizedReturn >= 0 ? '+' : '' }}{{ dashboard.annualizedReturn.toFixed(2) }}%
          </text>
        </view>
        <view class="dash-item">
          <text class="dash-label">夏普比率</text>
          <text class="dash-value neutral">{{ dashboard.sharpeRatio.toFixed(2) }}</text>
        </view>
        <view class="dash-item">
          <text class="dash-label">最大回撤</text>
          <text class="dash-value down">{{ dashboard.maxDrawdown.toFixed(2) }}%</text>
        </view>
        <view class="dash-item">
          <text class="dash-label">胜率</text>
          <text class="dash-value neutral">{{ dashboard.winRate.toFixed(1) }}%</text>
        </view>
        <view class="dash-item" v-if="dashboard.beatBenchmark !== undefined">
          <text class="dash-label">超额收益</text>
          <text class="dash-value" :class="dashboard.beatBenchmark >= 0 ? 'up' : 'down'">
            {{ dashboard.beatBenchmark >= 0 ? '+' : '' }}{{ dashboard.beatBenchmark.toFixed(2) }}%
          </text>
        </view>
      </view>
    </view>

    <!-- 收益率曲线 -->
    <view class="section" v-if="equityCurve">
      <view class="section-header">
        <text class="section-title">收益率曲线</text>
        <view class="period-tabs">
          <text
            v-for="p in periods"
            :key="p.value"
            class="period-tab"
            :class="{ active: equityPeriod === p.value }"
            @click="switchPeriod(p.value)"
          >{{ p.label }}</text>
        </view>
      </view>
      <view class="chart-container" v-if="equityCurve.dates.length">
        <view class="chart-y-axis">
          <text v-for="label in yAxisLabels" :key="label" class="y-label">{{ label }}</text>
        </view>
        <view class="chart-area">
          <view class="chart-line" :style="lineStyle"></view>
          <view v-for="(point, idx) in chartPoints" :key="idx" class="chart-dot" :style="point.style">
            <view class="dot-tooltip" v-if="idx === chartPoints.length - 1">
              <text class="tooltip-text">{{ equityCurve.equity[idx].toFixed(2) }}</text>
            </view>
          </view>
        </view>
        <view class="chart-x-axis">
          <text class="x-label">{{ equityCurve.dates[0] }}</text>
          <text class="x-label">{{ equityCurve.dates[equityCurve.dates.length - 1] }}</text>
        </view>
      </view>
      <view class="chart-legend">
        <view class="legend-item">
          <view class="legend-dot primary"></view>
          <text class="legend-text">账户净值</text>
        </view>
        <view class="legend-item" v-if="equityCurve.benchmark && equityCurve.benchmark.length">
          <view class="legend-dot secondary"></view>
          <text class="legend-text">基准</text>
        </view>
      </view>
    </view>

    <!-- 统计指标 -->
    <view class="section" v-if="statistics">
      <view class="section-title">统计指标</view>
      <view class="stats-list">
        <view class="stat-row">
          <text class="stat-label">胜率</text>
          <text class="stat-value neutral">{{ statistics.winRate.toFixed(1) }}%</text>
        </view>
        <view class="stat-row">
          <text class="stat-label">盈亏比</text>
          <text class="stat-value neutral">{{ statistics.profitLossRatio.toFixed(2) }}</text>
        </view>
        <view class="stat-row">
          <text class="stat-label">最大单笔盈利</text>
          <text class="stat-value up">+{{ statistics.maxSingleProfit.toFixed(2) }}</text>
        </view>
        <view class="stat-row">
          <text class="stat-label">最大单笔亏损</text>
          <text class="stat-value down">{{ statistics.maxSingleLoss.toFixed(2) }}</text>
        </view>
        <view class="stat-row">
          <text class="stat-label">夏普比率</text>
          <text class="stat-value neutral">{{ statistics.sharpeRatio.toFixed(2) }}</text>
        </view>
        <view class="stat-row">
          <text class="stat-label">最大回撤</text>
          <text class="stat-value down">{{ statistics.maxDrawdown.toFixed(2) }}%</text>
        </view>
      </view>
    </view>

    <!-- 归因分析 -->
    <view class="section" v-if="attribution && attribution.items.length">
      <view class="section-title">归因分析</view>
      <view class="attribution-list">
        <view class="attr-item" v-for="item in sortedAttribution" :key="item.label">
          <view class="attr-header">
            <text class="attr-name">{{ item.label }}</text>
            <text class="attr-pct" :class="item.contribution >= 0 ? 'up' : 'down'">
              {{ item.contribution >= 0 ? '+' : '' }}{{ item.contribution.toFixed(2) }}%
            </text>
          </view>
          <view class="attr-bar-bg">
            <view class="attr-bar-fill" :class="item.contribution >= 0 ? 'bg-up' : 'bg-down'" :style="getBarWidth(item)"></view>
          </view>
        </view>
      </view>
    </view>

    <!-- 加载状态 -->
    <view class="loading-state" v-if="isLoading">
      <text class="loading-text">加载分析数据...</text>
    </view>

    <!-- 空状态 -->
    <view class="empty-state" v-if="!isLoading && !hasData">
      <text class="empty-text">暂无分析数据</text>
      <text class="empty-hint">完成交易后即可查看持仓分析</text>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import {
  fetchEquityCurve, fetchAttribution, fetchDashboardSummary, fetchStatistics,
  type DashboardSummary, type AttributionItem,
} from '@/api/analysis'

const periods = [
  { label: '1月', value: '1m' },
  { label: '3月', value: '3m' },
  { label: '6月', value: '6m' },
  { label: '1年', value: '1y' },
]

const equityPeriod = ref('1m')
const dashboard = ref<DashboardSummary | null>(null)
const equityCurve = ref<{ dates: string[]; equity: number[]; benchmark?: number[] } | null>(null)
const statistics = ref<{ winRate: number; profitLossRatio: number; maxSingleProfit: number; maxSingleLoss: number; sharpeRatio: number; maxDrawdown: number } | null>(null)
const attribution = ref<{ items: AttributionItem[] } | null>(null)
const isLoading = ref(false)

const hasData = computed(() => dashboard.value || equityCurve.value || statistics.value || (attribution.value && attribution.value.items.length))

const sortedAttribution = computed(() => {
  if (!attribution.value) return []
  return [...attribution.value.items].sort((a, b) => Math.abs(b.contribution) - Math.abs(a.contribution))
})

const maxContribution = computed(() => {
  if (!sortedAttribution.value.length) return 1
  return Math.max(...sortedAttribution.value.map(i => Math.abs(i.contribution)), 1)
})

const yAxisLabels = computed(() => {
  if (!equityCurve.value || !equityCurve.value.equity.length) return []
  const values = equityCurve.value.equity
  const max = Math.max(...values)
  const min = Math.min(...values)
  return [max.toFixed(0), ((max + min) / 2).toFixed(0), min.toFixed(0)]
})

const chartPoints = computed(() => {
  if (!equityCurve.value || !equityCurve.value.equity.length) return []
  const values = equityCurve.value.equity
  const max = Math.max(...values)
  const min = Math.min(...values)
  const range = max - min || 1
  return values.map((v, i) => ({
    left: `${(i / (values.length - 1 || 1)) * 100}%`,
    bottom: `${((v - min) / range) * 100}%`,
    style: { left: `${(i / (values.length - 1 || 1)) * 100}%`, bottom: `${((v - min) / range) * 100}%` },
  }))
})

const lineStyle = computed(() => {
  if (!equityCurve.value || !equityCurve.value.equity.length) return {}
  const values = equityCurve.value.equity
  const max = Math.max(...values)
  const min = Math.min(...values)
  const range = max - min || 1
  const points = values.map((v, i) => `${(i / (values.length - 1 || 1)) * 100} ${100 - ((v - min) / range) * 100}`)
  return { clipPath: `polygon(0 100%, ${points.join(',')}, 100% 100%)` }
})

function getBarWidth(item: AttributionItem) {
  return { width: `${(Math.abs(item.contribution) / maxContribution.value) * 100}%` }
}

function formatMoney(v: number): string {
  return Math.abs(v).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

async function loadAnalytics() {
  isLoading.value = true
  try {
    const [dash, stat, attr, curve] = await Promise.all([
      fetchDashboardSummary().catch(() => null),
      fetchStatistics().catch(() => null),
      fetchAttribution(equityPeriod.value).catch(() => null),
      fetchEquityCurve(equityPeriod.value).catch(() => null),
    ])
    dashboard.value = dash
    statistics.value = stat
    attribution.value = attr
    equityCurve.value = curve
  } catch {
    /* handled individually */
  } finally {
    isLoading.value = false
  }
}

async function switchPeriod(period: string) {
  equityPeriod.value = period
  try {
    const [curve, attr] = await Promise.all([
      fetchEquityCurve(period),
      fetchAttribution(period),
    ])
    equityCurve.value = curve
    attribution.value = attr
  } catch { /* ignore */ }
}

onMounted(loadAnalytics)
onShow(() => {
  if (!hasData.value) loadAnalytics()
})
</script>

<style scoped lang="scss">
.analytics-page {
  min-height: 100vh;
  background: #f5f6fa;
  padding-bottom: 32rpx;
}

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
  margin-bottom: 16rpx;
}

.section-title {
  font-size: 28rpx;
  font-weight: 600;
  color: #1a1a2e;
}

.period-tabs {
  display: flex;
  gap: 8rpx;
}

.period-tab {
  font-size: 22rpx;
  color: #999;
  padding: 6rpx 16rpx;
  border-radius: 20rpx;
  background: #f5f6fa;
  &.active {
    color: #fff;
    background: #4A90E2;
  }
}

/* Dashboard Grid */
.dashboard-grid {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 16rpx;
}

.dash-item {
  background: #f8f9fc;
  border-radius: 12rpx;
  padding: 20rpx 16rpx;
  text-align: center;
}

.dash-label {
  display: block;
  font-size: 22rpx;
  color: #999;
  margin-bottom: 8rpx;
}

.dash-value {
  font-size: 30rpx;
  font-weight: 700;
}

/* Chart */
.chart-container {
  position: relative;
  height: 320rpx;
  display: flex;
  padding-left: 80rpx;
  margin-bottom: 8rpx;
}

.chart-y-axis {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 80rpx;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.y-label {
  font-size: 18rpx;
  color: #ccc;
  line-height: 1;
}

.chart-area {
  position: relative;
  flex: 1;
  height: 100%;
}

.chart-line {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(180deg, rgba(74,144,226,0.15) 0%, rgba(74,144,226,0.02) 100%);
}

.chart-line::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
}

.chart-dot {
  position: absolute;
  width: 12rpx;
  height: 12rpx;
  background: #4A90E2;
  border-radius: 50%;
  transform: translate(-50%, 50%);
  .dot-tooltip {
    position: absolute;
    bottom: 16rpx;
    left: 50%;
    transform: translateX(-50%);
    background: #333;
    border-radius: 6rpx;
    padding: 4rpx 12rpx;
    white-space: nowrap;
  }
  .tooltip-text {
    font-size: 20rpx;
    color: #fff;
  }
}

.chart-x-axis {
  display: flex;
  justify-content: space-between;
  padding: 0 0 0 80rpx;
}

.x-label {
  font-size: 18rpx;
  color: #ccc;
}

.chart-legend {
  display: flex;
  justify-content: center;
  gap: 32rpx;
  padding: 16rpx 0 0 80rpx;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 8rpx;
}

.legend-dot {
  width: 16rpx;
  height: 16rpx;
  border-radius: 50%;
  &.primary { background: #4A90E2; }
  &.secondary { background: #F5A623; }
}

.legend-text {
  font-size: 22rpx;
  color: #666;
}

/* Statistics */
.stats-list {
  display: flex;
  flex-direction: column;
  gap: 4rpx;
}

.stat-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20rpx 0;
  border-bottom: 1rpx solid #f0f0f0;
  &:last-child { border-bottom: none; }
}

.stat-label {
  font-size: 26rpx;
  color: #666;
}

.stat-value {
  font-size: 26rpx;
  font-weight: 600;
}

/* Attribution */
.attr-item {
  margin-bottom: 16rpx;
  &:last-child { margin-bottom: 0; }
}

.attr-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8rpx;
}

.attr-name {
  font-size: 24rpx;
  color: #333;
}

.attr-pct {
  font-size: 24rpx;
  font-weight: 600;
}

.attr-bar-bg {
  height: 12rpx;
  background: #f0f0f0;
  border-radius: 6rpx;
  overflow: hidden;
}

.attr-bar-fill {
  height: 100%;
  border-radius: 6rpx;
  transition: width 0.3s ease;
  &.bg-up { background: #4A90E2; }
  &.bg-down { background: #E25C5C; }
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
  padding: 80rpx 0;
}

.loading-text {
  font-size: 28rpx;
  color: #999;
}

.empty-text {
  font-size: 28rpx;
  color: #999;
  margin-bottom: 8rpx;
}

.empty-hint {
  font-size: 24rpx;
  color: #ccc;
}
</style>
