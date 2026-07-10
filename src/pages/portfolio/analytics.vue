<template>
  <view class="analytics-page">
    <!-- 资产概览卡 -->
    <view class="section" v-if="assetOverview">
      <view class="section-title">资产概览</view>
      <view class="asset-grid">
        <view class="asset-card primary">
          <text class="asset-label">总资产</text>
          <text class="asset-value">&yen;{{ formatMoney(assetOverview.totalAssets) }}</text>
        </view>
        <view class="asset-card">
          <text class="asset-label">今日盈亏</text>
          <text class="asset-value" :class="assetOverview.todayPnl >= 0 ? 'up' : 'down'">
            {{ assetOverview.todayPnl >= 0 ? '+' : '' }}&yen;{{ formatMoney(Math.abs(assetOverview.todayPnl)) }}
          </text>
        </view>
        <view class="asset-card">
          <text class="asset-label">持仓盈亏</text>
          <text class="asset-value" :class="assetOverview.positionPnl >= 0 ? 'up' : 'down'">
            {{ assetOverview.positionPnl >= 0 ? '+' : '' }}&yen;{{ formatMoney(Math.abs(assetOverview.positionPnl)) }}
          </text>
        </view>
        <view class="asset-card">
          <text class="asset-label">持仓市值</text>
          <text class="asset-value">&yen;{{ formatMoney(assetOverview.positionValue) }}</text>
        </view>
        <view class="asset-card">
          <text class="asset-label">可用资金</text>
          <text class="asset-value">&yen;{{ formatMoney(assetOverview.availableCash) }}</text>
        </view>
      </view>
    </view>

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

    <!-- 收益率曲线（LineChart） -->
    <view class="section" v-if="equityCurve && equityCurve.dates.length">
      <view class="section-title">收益率曲线</view>
      <LineChart
        v-model="equityPeriod"
        :dates="equityCurve.dates"
        :values="equityCurve.equity"
        :benchmark-data="equityCurve.benchmark"
        :periods="periods"
        height="360rpx"
        :show-legend="true"
        legend-primary="账户净值"
        legend-secondary="基准"
      />
    </view>

    <!-- 持仓分布（PieChart） -->
    <view class="section" v-if="positionDist && positionDist.length">
      <view class="section-title">持仓分布</view>
      <PieChart
        :data="pieDistData"
        height="440rpx"
        :show-percent="true"
      />
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
            <view
              class="attr-bar-fill"
              :class="item.contribution >= 0 ? 'bg-up' : 'bg-down'"
              :style="getBarWidth(item)"
            ></view>
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

    <!-- 免责声明 -->
    <Disclaimer />
  </view>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import LineChart from '@/components/charts/LineChart.vue'
import PieChart from '@/components/charts/PieChart.vue'
import Disclaimer from '@/components/compliance/Disclaimer.vue'
import {
  fetchEquityCurve, fetchAttribution, fetchDashboardSummary, fetchStatistics,
  fetchAssetOverview, fetchPositionDistribution,
  type DashboardSummary, type AttributionItem, type AssetOverview, type PositionDistItem,
} from '@/api/analysis'

const periods = [
  { label: '1日', value: '1d' },
  { label: '1周', value: '1w' },
  { label: '1月', value: '1m' },
  { label: '3月', value: '3m' },
  { label: '6月', value: '6m' },
  { label: '1年', value: '1y' },
  { label: '全部', value: 'all' },
]

const equityPeriod = ref('1m')
const dashboard = ref<DashboardSummary | null>(null)
const equityCurve = ref<{ dates: string[]; equity: number[]; benchmark?: number[] } | null>(null)
const statistics = ref<{ winRate: number; profitLossRatio: number; maxSingleProfit: number; maxSingleLoss: number; sharpeRatio: number; maxDrawdown: number } | null>(null)
const attribution = ref<{ items: AttributionItem[] } | null>(null)
const assetOverview = ref<AssetOverview | null>(null)
const positionDist = ref<PositionDistItem[] | null>(null)
const isLoading = ref(false)

const hasData = computed(() =>
  assetOverview.value || dashboard.value || equityCurve.value || statistics.value ||
  (attribution.value && attribution.value.items.length) ||
  (positionDist.value && positionDist.value.length)
)

const sortedAttribution = computed(() => {
  if (!attribution.value) return []
  return [...attribution.value.items].sort((a, b) => Math.abs(b.contribution) - Math.abs(a.contribution))
})

const maxContribution = computed(() => {
  if (!sortedAttribution.value.length) return 1
  return Math.max(...sortedAttribution.value.map(i => Math.abs(i.contribution)), 1)
})

const pieDistData = computed(() => {
  if (!positionDist.value) return []
  return positionDist.value.map(d => ({ name: d.name, value: d.value }))
})

function getBarWidth(item: AttributionItem) {
  return { width: `${(Math.abs(item.contribution) / maxContribution.value) * 100}%` }
}

function formatMoney(v: number): string {
  if (v == null) return '0.00'
  return Math.abs(v).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

async function loadAnalytics() {
  isLoading.value = true
  try {
    const [dash, stat, attr, curve, overview, dist] = await Promise.all([
      fetchDashboardSummary().catch(() => null),
      fetchStatistics().catch(() => null),
      fetchAttribution(equityPeriod.value).catch(() => null),
      fetchEquityCurve(equityPeriod.value).catch(() => null),
      fetchAssetOverview().catch(() => null),
      fetchPositionDistribution().catch(() => null),
    ])
    dashboard.value = dash
    statistics.value = stat
    attribution.value = attr
    equityCurve.value = curve
    assetOverview.value = overview
    positionDist.value = dist
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

// 监听周期变化（LineChart v-model 驱动）
import { watch } from 'vue'
watch(equityPeriod, (newVal, oldVal) => {
  if (newVal !== oldVal) switchPeriod(newVal)
})

onMounted(loadAnalytics)
onShow(() => {
  if (!hasData.value) loadAnalytics()
})
</script>

<style scoped lang="scss">
.analytics-page {
  min-height: 100vh;
  background: #f5f6fa;
  padding-bottom: calc(env(safe-area-inset-bottom) + 32rpx);
}

.section {
  background: #fff;
  margin: 16rpx 24rpx;
  border-radius: 16rpx;
  padding: 24rpx;
}

.section-title {
  font-size: 28rpx;
  font-weight: 600;
  color: #1a1a2e;
  margin-bottom: 16rpx;
}

/* ===== 资产概览卡 ===== */
.asset-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 12rpx;
}

.asset-card {
  flex: 1 1 calc(50% - 6rpx);
  min-width: 200rpx;
  background: #f8f9fc;
  border-radius: 12rpx;
  padding: 20rpx 16rpx;

  &.primary {
    flex: 1 1 100%;
    background: linear-gradient(135deg, #4A90E2, #2d4a8a);
    .asset-label { color: rgba(255,255,255,0.7); }
    .asset-value { color: #fff; font-size: 40rpx; }
  }
}

.asset-label {
  display: block;
  font-size: 22rpx;
  color: #999;
  margin-bottom: 6rpx;
}

.asset-value {
  font-size: 28rpx;
  font-weight: 700;
  color: #1a1a2e;
}

/* ===== 看板概览 ===== */
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

/* ===== 统计指标 ===== */
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

/* ===== 归因分析 ===== */
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

/* ===== 颜色 ===== */
.up { color: #E25C5C; }
.down { color: #34C759; }
.neutral { color: #1a1a2e; }

/* ===== 状态 ===== */
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
