<template>
  <view class="dashboard-page">
    <LoadingSkeleton v-if="loading" scene="dashboard" :rows="4" />
    <view class="page-header" v-if="!loading">
      <text class="page-title">数据看板</text>
      <text class="page-subtitle">投资业绩一览</text>
    </view>
    <view class="section-card summary-card" v-if="!loading">
      <view class="card-header">
        <text class="card-title">业绩概览</text>
      </view>
      <view class="summary-grid">
        <view class="summary-item" v-for="item in summaryItems" :key="item.label">
          <NumberRolling
            v-if="item.isNumber"
            class="summary-value"
            :class="item.colorClass"
            :value="item.rawValue"
            :precision="item.precision"
            :prefix="item.prefix"
            :suffix="item.suffix"
            :color-rule="'auto'"
            :duration="500"
            :immediate="true"
          />
          <text v-else class="summary-value" :class="item.colorClass">{{ item.display }}</text>
          <text class="summary-label">{{ item.label }}</text>
        </view>
      </view>
    </view>
    <view class="section-card">
      <view class="card-header">
        <text class="card-title">收益率曲线</text>
      </view>
      <LineChart
        :modelValue="period"
        :dates="equityDates"
        :values="equityValues"
        :benchmarkData="equityBenchmark"
        :periods="periodOptions"
        :height="chartHeight"
        :showLegend="true"
        :legendPrimary="equityLegendPrimary"
        :legendSecondary="equityLegendSecondary"
        :yAxisFormatter="formatPercent"
        @update:modelValue="onPeriodChange"
      />
    </view>
    <view class="section-card">
      <view class="card-header">
        <text class="card-title">归因分析</text>
        <view class="period-tabs">
          <text
            v-for="p in periodOptions"
            :key="p.value"
            class="period-tab"
            :class="{ active: attributionPeriod === p.value }"
            @click="onAttributionPeriodChange(p.value)"
          >{{ p.label }}</text>
        </view>
      </view>
      <view v-if="attributionItems.length">
        <BarChart
          :data="attributionBarData"
          :height="attributionChartHeight"
          :horizontal="true"
          :positiveColor="positiveColor"
          :negativeColor="negativeColor"
        />
        <view class="attribution-legend">
          <view class="legend-item">
            <view class="legend-dot positive-dot"></view>
            <text class="legend-text">正贡献</text>
          </view>
          <view class="legend-item">
            <view class="legend-dot negative-dot"></view>
            <text class="legend-text">负贡献</text>
          </view>
        </view>
      </view>
      <EmptyState v-else icon="chart" description="暂无归因数据" />
    </view>
    <view class="section-card">
      <view class="card-header">
        <text class="card-title">持仓明细</text>
      </view>
      <view v-if="positions.length">
        <view class="position-table">
          <view class="table-header">
            <text class="col-symbol">股票</text>
            <text class="col-qty">持仓</text>
            <text class="col-cost">成本</text>
            <text class="col-price">现价</text>
            <text class="col-pnl">盈亏</text>
          </view>
          <view class="table-row" v-for="pos in positions" :key="pos.symbol">
            <view class="col-symbol">
              <text class="symbol-text">{{ formatSymbol(pos.symbol) }}</text>
              <text class="market-tag">{{ pos.market === 'A' ? '沪' : '港' }}</text>
            </view>
            <text class="col-qty">{{ pos.qty }}</text>
            <text class="col-cost">{{ formatMoney(pos.avg_cost, pos.market) }}</text>
            <text class="col-price">{{ formatMoney(pos.last_price, pos.market) }}</text>
            <text class="col-pnl" :class="pos.unrealized_pnl >= 0 ? 'pnl-positive' : 'pnl-negative'">
              {{ formatPnl(pos.unrealized_pnl, pos.market) }}
            </text>
          </view>
        </view>
      </view>
      <EmptyState v-else title="暂无持仓" description="开始交易后此处显示持仓明细" />
    </view>
    <Disclaimer />
  </view>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import LineChart from '@/components/charts/LineChart.vue'
import BarChart from '@/components/charts/BarChart.vue'
import Disclaimer from '@/components/compliance/Disclaimer.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import LoadingSkeleton from '@/components/common/LoadingSkeleton.vue'
import NumberRolling from '@/components/common/NumberRolling.vue'
import { trackPageView } from '@/utils/tracker'

import {
  fetchDashboardSummary,
  fetchEquityCurve,
  fetchAttribution,
  type DashboardSummary,
  type AttributionItem,
} from '@/api/analysis'
import { fetchPositions, type Position } from '@/api/trading'

const periodOptions = [
  { label: '1D', value: '1D' },
  { label: '1W', value: '1W' },
  { label: '1M', value: '1M' },
  { label: '3M', value: '3M' },
  { label: '6M', value: '6M' },
  { label: '1Y', value: '1Y' },
  { label: '全部', value: 'ALL' },
]

const period = ref<string>('1M')
const attributionPeriod = ref<string>('1M')
const loading = ref(false)

const summary = ref<DashboardSummary | null>(null)
const equityDates = ref<string[]>([])
const equityValues = ref<number[]>([])
const equityBenchmark = ref<number[] | undefined>(undefined)
const attributionItems = ref<AttributionItem[]>([])
const positions = ref<Position[]>([])

const summaryItems = computed(() => {
  const s = summary.value
  if (!s) return []
  return [
    { label: '总收益率', display: formatPercentDisplay(s.totalReturn), rawValue: s.totalReturn * 100, precision: 2, prefix: s.totalReturn >= 0 ? '+' : '', suffix: '%', isNumber: true, colorClass: s.totalReturn >= 0 ? 'val-positive' : 'val-negative' },
    { label: '年化收益', display: formatPercentDisplay(s.annualizedReturn), rawValue: s.annualizedReturn * 100, precision: 2, prefix: s.annualizedReturn >= 0 ? '+' : '', suffix: '%', isNumber: true, colorClass: s.annualizedReturn >= 0 ? 'val-positive' : 'val-negative' },
    { label: '跑赢大盘', display: formatPercentDisplay(s.beatBenchmark), rawValue: s.beatBenchmark * 100, precision: 2, prefix: s.beatBenchmark >= 0 ? '+' : '', suffix: '%', isNumber: true, colorClass: s.beatBenchmark >= 0 ? 'val-positive' : 'val-negative' },
    { label: '夏普比率', display: s.sharpeRatio.toFixed(2), rawValue: s.sharpeRatio, precision: 2, prefix: '', suffix: '', isNumber: true, colorClass: s.sharpeRatio >= 0 ? 'val-positive' : 'val-negative' },
    { label: '最大回撤', display: formatPercentDisplay(s.maxDrawdown), rawValue: s.maxDrawdown * 100, precision: 2, prefix: '', suffix: '%', isNumber: true, colorClass: 'val-negative' },
    { label: '胜率', display: `${(s.winRate * 100).toFixed(1)}%`, rawValue: 0, precision: 0, prefix: '', suffix: '', isNumber: false, colorClass: s.winRate >= 0.5 ? 'val-positive' : 'val-negative' },
  ]
})

const attributionBarData = computed(() => {
  return attributionItems.value.map(item => ({
    label: item.label,
    value: item.contribution,
    percentage: item.percentage,
  }))
})

const chartHeight = '400rpx'
const attributionChartHeight = computed(() => {
  const count = attributionItems.value.length
  return count > 0 ? `${Math.max(300, count * 48)}rpx` : '300rpx'
})
const equityLegendPrimary = '账户净值'
const equityLegendSecondary = '基准'
const positiveColor = '#34C759'
const negativeColor = '#E25C5C'

function formatPercent(val: number): string { return `${val >= 0 ? '+' : ''}${(val * 100).toFixed(2)}%` }
function formatPercentDisplay(val: number): string { return `${val >= 0 ? '+' : ''}${(val * 100).toFixed(2)}%` }
function formatSymbol(symbol: string): string { return symbol.replace(/\.[A-Z]{2,4}$/, '') }
function formatMoney(val: number | null, market: string): string {
  if (val === null) return '--'
  const currency = market === 'HK' ? 'HK$' : '¥'
  return `${currency}${val.toFixed(2)}`
}
function formatPnl(val: number, market: string): string {
  const sign = val >= 0 ? '+' : ''
  const currency = market === 'HK' ? 'HK$' : '¥'
  return `${sign}${currency}${Math.abs(val).toFixed(2)}`
}

async function loadSummary() { try { summary.value = await fetchDashboardSummary() } catch (e) { console.warn('[Dashboard] 加载业绩概览失败', e) } }
async function loadEquityCurve() {
  try { const res = await fetchEquityCurve(period.value); equityDates.value = res.dates; equityValues.value = res.equity; equityBenchmark.value = res.benchmark }
  catch (e) { console.warn('[Dashboard] 加载收益率曲线失败', e); equityDates.value = []; equityValues.value = []; equityBenchmark.value = undefined }
}
async function loadAttribution() {
  try { const res = await fetchAttribution(attributionPeriod.value); attributionItems.value = res.items }
  catch (e) { console.warn('[Dashboard] 加载归因分析失败', e); attributionItems.value = [] }
}
async function loadPositions() { try { positions.value = await fetchPositions() } catch (e) { console.warn('[Dashboard] 加载持仓失败', e); positions.value = [] } }
function onPeriodChange(val: string) { period.value = val; loadEquityCurve() }
function onAttributionPeriodChange(val: string) { attributionPeriod.value = val; loadAttribution() }

onMounted(async () => {
  loading.value = true
  await Promise.all([loadSummary(), loadEquityCurve(), loadAttribution(), loadPositions()])
  loading.value = false
})

onShow(() => {
  trackPageView('dashboard')
})
</script>

<style scoped lang="scss">
.dashboard-page {
  padding: 24rpx 24rpx calc(env(safe-area-inset-bottom) + 48rpx);
  background: var(--bg-page, #F5F5F7);
  min-height: 100vh;
}

.page-header { padding: 16rpx 0 24rpx; display: flex; flex-direction: column; gap: 4rpx; }
.page-title { font-size: 40rpx; font-weight: 700; color: var(--text-primary, #1A1A2E); }
.page-subtitle { font-size: 24rpx; color: var(--text-hint, #999); }

.section-card {
  background: var(--bg-card, #fff);
  border-radius: 20rpx;
  padding: 28rpx 24rpx;
  margin-bottom: 24rpx;
  box-shadow: var(--shadow-card, 0 2rpx 12rpx rgba(0,0,0,0.04));
}

.card-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 20rpx; flex-wrap: wrap; gap: 12rpx; }
.card-title { font-size: 30rpx; font-weight: 600; color: var(--text-primary, #1A1A2E); }

.summary-card { background: linear-gradient(135deg, #1A1A2E 0%, #16213E 100%); }
.summary-card .card-title { color: #fff; }
.summary-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 24rpx 16rpx; }
.summary-item { display: flex; flex-direction: column; align-items: center; gap: 6rpx; }
.summary-value {
  font-size: 32rpx; font-weight: 700; font-variant-numeric: tabular-nums;
  &.val-positive { color: var(--color-success, #34C759); }
  &.val-negative { color: var(--color-danger, #E25C5C); }
}
.summary-label { font-size: 22rpx; color: rgba(255,255,255,0.65); }

.period-tabs { display: flex; gap: 8rpx; }
.period-tab {
  font-size: 22rpx; color: var(--text-hint, #999); padding: 6rpx 16rpx;
  border-radius: 20rpx; background: var(--bg-input, #f5f6fa); cursor: pointer;
  &.active { color: #fff; background: var(--color-primary, #4A90E2); }
}

.attribution-legend { display: flex; justify-content: center; gap: 32rpx; padding: 16rpx 0 0; }
.legend-item { display: flex; align-items: center; gap: 8rpx; }
.legend-dot { width: 16rpx; height: 16rpx; border-radius: 4rpx; }
.positive-dot { background: var(--color-success, #34C759); }
.negative-dot { background: var(--color-danger, #E25C5C); }
.legend-text { font-size: 22rpx; color: var(--text-secondary, #666); }

.position-table { width: 100%; overflow-x: auto; }
.table-header { display: flex; align-items: center; padding: 12rpx 0; border-bottom: 1rpx solid var(--border-color, #f0f0f0); }
.table-row { display: flex; align-items: center; padding: 16rpx 0; border-bottom: 1rpx solid var(--border-color, #f8f8f8); }
.table-header text { font-size: 22rpx; color: var(--text-hint, #999); font-weight: 500; }
.col-symbol { flex: 2; display: flex; align-items: center; gap: 8rpx; }
.symbol-text { font-size: 26rpx; font-weight: 600; color: var(--text-primary, #333); }
.market-tag { font-size: 18rpx; color: #fff; background: var(--color-primary, #4A90E2); border-radius: 6rpx; padding: 2rpx 8rpx; }
.col-qty, .col-cost, .col-price, .col-pnl { flex: 1; text-align: right; font-size: 24rpx; color: var(--text-primary, #333); font-variant-numeric: tabular-nums; }
.col-qty { color: var(--text-secondary, #666); }
.pnl-positive { color: var(--color-success, #34C759); }
.pnl-negative { color: var(--color-danger, #E25C5C); }
</style>
