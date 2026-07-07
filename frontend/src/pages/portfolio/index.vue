<template>
  <view class="portfolio-page">
    <!-- 离线提示横幅 -->
    <view v-if="offline" class="offline-banner">
      <text class="offline-icon">&#x1F4F6;</text>
      <text class="offline-text">当前处于离线模式，数据可能不是最新的</text>
    </view>

    <!-- 骨架屏 -->
    <LoadingSkeleton v-if="isLoading" scene="portfolio" :rows="4" />

    <!-- 账户卡片 -->
    <view class="account-card fade-in-view" v-else-if="account">
      <view class="account-header">
        <text class="account-type">模拟账户</text>
        <button class="btn-refresh" @click="refreshAll">刷新</button>
      </view>
      <view class="account-main">
        <text class="total-label">总资产</text>
        <view class="total-value">
          <text class="currency">&yen;</text>
          <text class="amount">{{ formatMoney(account.total_equity) }}</text>
        </view>
      </view>
      <view class="account-stats">
        <view class="stat-item">
          <text class="stat-label">可用余额</text>
          <text class="stat-value">{{ formatMoney(account.balance) }}</text>
        </view>
        <view class="stat-divider"></view>
        <view class="stat-item">
          <text class="stat-label">持仓市值</text>
          <text class="stat-value">{{ formatMoney(account.market_value) }}</text>
        </view>
        <view class="stat-divider"></view>
        <view class="stat-item">
          <text class="stat-label">累计盈亏</text>
          <NumberRolling
            class="stat-value"
            :class="account.profit >= 0 ? 'up' : 'down'"
            :value="account.profit"
            :precision="2"
            :prefix="account.profit >= 0 ? '+' : ''"
            :color-rule="'auto'"
            :duration="500"
            :immediate="true"
          />
        </view>
      </view>
    </view>

    <!-- 持仓分析看板 -->
    <view class="analytics-board fade-in-view" v-if="!isLoading && analytics">
      <view class="analytics-board-header">
        <text class="analytics-board-title">持仓分析</text>
        <text class="analytics-link" @click="goAnalytics">查看完整分析 →</text>
      </view>
      <!-- 盈亏概览 -->
      <view class="analytics-card">
        <text class="analytics-card-title">盈亏概览</text>
        <view class="overview-main">
          <NumberRolling
            class="overview-pnl"
            :class="analytics.total_profit >= 0 ? 'up' : 'down'"
            :value="Math.abs(analytics.total_profit)"
            :precision="2"
            :prefix="(analytics.total_profit >= 0 ? '+¥' : '-¥')"
            :color-rule="'auto'"
            :duration="600"
            :thousandth="true"
          />
          <NumberRolling
            class="overview-pnl-pct"
            :class="analytics.total_profit_pct >= 0 ? 'up' : 'down'"
            :value="analytics.total_profit_pct"
            :precision="2"
            :prefix="'(' + (analytics.total_profit_pct >= 0 ? '+' : '')"
            :suffix="'%)'"
            :color-rule="'auto'"
            :duration="500"
          />
        </view>
        <view class="overview-sub">
          <view class="overview-sub-item">
            <text class="sub-label">今日盈亏</text>
            <NumberRolling
              class="sub-value"
              :class="analytics.daily_profit >= 0 ? 'up' : 'down'"
              :value="analytics.daily_profit"
              :precision="2"
              :prefix="'¥' + (analytics.daily_profit >= 0 ? '+' : '')"
              :color-rule="'auto'"
              :duration="500"
            />
            <NumberRolling
              class="sub-pct"
              :class="analytics.daily_profit_pct >= 0 ? 'up' : 'down'"
              :value="analytics.daily_profit_pct"
              :precision="2"
              :prefix="'(' + (analytics.daily_profit_pct >= 0 ? '+' : '')"
              :suffix="'%)'"
              :color-rule="'auto'"
              :duration="400"
            />
          </view>
          <view class="overview-sub-item">
            <text class="sub-label">持仓市值</text>
            <text class="sub-value">&yen;{{ formatMoney(analytics.total_market_value) }}</text>
          </view>
        </view>
      </view>

      <!-- 持仓指标 -->
      <view class="analytics-card">
        <text class="analytics-card-title">持仓分析</text>
        <!-- 空持仓 -->
        <view v-if="analytics.position_count === 0" class="empty-analytics">
          <text>还没有持仓，去选股吧</text>
        </view>
        <template v-else>
          <view class="metrics-grid">
            <view class="metric-item">
              <text class="metric-value">{{ analytics.position_count }}</text>
              <text class="metric-label">持仓数</text>
            </view>
            <view class="metric-item">
              <text class="metric-value">{{ analytics.win_rate.toFixed(0) }}%</text>
              <text class="metric-label">胜率</text>
            </view>
            <view class="metric-item">
              <text class="metric-value">{{ analytics.top_holdings_concentration.toFixed(1) }}%</text>
              <text class="metric-label">集中度</text>
            </view>
          </view>
          <view class="metrics-best-worst">
            <view class="bw-item" v-if="analytics.best_position" @click="goDetail(analytics.best_position.symbol)">
              <text class="bw-label">最佳</text>
              <text class="bw-name">{{ analytics.best_position.name }}</text>
              <text class="bw-pnl up">+{{ analytics.best_position.profit_pct.toFixed(2) }}%</text>
              <text class="bw-arrow">&gt;</text>
            </view>
            <view class="bw-item" v-if="analytics.worst_position" @click="goDetail(analytics.worst_position.symbol)">
              <text class="bw-label">最差</text>
              <text class="bw-name">{{ analytics.worst_position.name }}</text>
              <text class="bw-pnl down">{{ analytics.worst_position.profit_pct.toFixed(2) }}%</text>
              <text class="bw-arrow">&gt;</text>
            </view>
          </view>
        </template>
      </view>

      <!-- 行业分布 -->
      <view class="analytics-card" v-if="analytics.holdings_distribution && analytics.holdings_distribution.length">
        <text class="analytics-card-title">行业分布</text>
        <view class="sector-list">
          <view class="sector-item" v-for="(item, idx) in analytics.holdings_distribution" :key="item.sector">
            <view class="sector-header">
              <view class="sector-dot" :style="{ background: sectorColors[idx % sectorColors.length] }"></view>
              <text class="sector-name">{{ item.sector }}</text>
              <text class="sector-cnt">{{ item.count }}只</text>
              <text class="sector-weight">{{ item.weight.toFixed(1) }}%</text>
            </view>
            <view class="sector-bar-wrap">
              <view class="sector-bar" :style="{ width: item.weight + '%', background: sectorColors[idx % sectorColors.length] }"></view>
            </view>
          </view>
        </view>
      </view>
    </view>

    <!-- Tab 切换 -->
    <view class="tab-bar">
      <view
        v-for="tab in tabs"
        :key="tab.key"
        class="tab-item"
        :class="{ active: activeTab === tab.key }"
        @click="switchTab(tab.key)"
      >
        {{ tab.label }}
        <text v-if="tab.key === 'orders' && orders.length" class="tab-badge">{{ orders.length }}</text>
      </view>
    </view>

    <!-- 持仓 Tab -->
    <scroll-view v-if="activeTab === 'positions'" class="content" scroll-y>
      <!-- 空持仓 -->
      <view v-else-if="positions.length === 0" class="empty-state">
        <text class="empty-icon">&#x1F4ED;</text>
        <text class="empty-text">暂无持仓</text>
        <text class="empty-sub">使用下方模拟下单功能开始交易</text>
      </view>

      <!-- 持仓列表 -->
      <view v-else>
        <view class="section-header">
          <text class="section-title">持仓 ({{ positions.length }})</text>
          <text class="section-tip">T+1 结算</text>
        </view>
        <view
          v-for="pos in positions"
          :key="pos.symbol"
          class="position-card"
          @click="goDetail(pos.symbol)"
        >
          <view class="pos-left">
            <text class="pos-name">{{ pos.name }}</text>
            <text class="pos-symbol">{{ pos.symbol }}</text>
          </view>
          <view class="pos-mid">
            <text class="pos-price">{{ pos.market_price.toFixed(2) }}</text>
            <text class="pos-cost">成本 {{ pos.cost_price.toFixed(2) }}</text>
          </view>
          <view class="pos-right">
            <text class="pos-pnl" :class="pos.profit >= 0 ? 'up' : 'down'">
              {{ pos.profit >= 0 ? '+' : '' }}{{ pos.profit.toFixed(2) }}
            </text>
            <text class="pos-qty">{{ pos.quantity }}股 / 可卖{{ pos.available }}</text>
          </view>
        </view>
      </view>

      <!-- 模拟下单面板 -->
      <view class="trade-section">
        <view class="section-header">
          <text class="section-title">模拟下单</text>
        </view>
        <view class="trade-form">
          <view class="form-row">
            <text class="form-label">股票</text>
            <input
              class="form-input"
              v-model="orderForm.symbol"
              placeholder="代码 如 000001.SZ"
              :adjust-position="true"
              :cursor-spacing="20"
            />
            <view class="side-toggle">
              <view class="side-btn buy" :class="{ active: orderForm.side === 'buy' }" @click="orderForm.side = 'buy'">买</view>
              <view class="side-btn sell" :class="{ active: orderForm.side === 'sell' }" @click="orderForm.side = 'sell'">卖</view>
            </view>
          </view>
          <view class="form-row">
            <text class="form-label">数量</text>
            <input
              class="form-input"
              v-model="orderForm.quantity"
              type="number"
              placeholder="100 股整数倍"
              :adjust-position="true"
              :cursor-spacing="20"
            />
            <button class="btn-submit" :class="orderForm.side" :disabled="submitting" @click="submitOrder">
              {{ submitting ? '提交中...' : (orderForm.side === 'buy' ? '买入' : '卖出') }}
            </button>
          </view>
        </view>
      </view>
    </scroll-view>

    <!-- 订单 Tab -->
    <scroll-view v-if="activeTab === 'orders'" class="content" scroll-y>
      <view v-if="orders.length === 0" class="empty-state">
        <text class="empty-icon">&#x1F4C4;</text>
        <text class="empty-text">暂无订单</text>
      </view>
      <view v-else v-for="order in orders" :key="order.id" class="order-card">
        <view class="order-top">
          <text class="order-name">{{ order.name || order.symbol }}</text>
          <text class="order-status" :class="order.status">{{ getStatusLabel(order.status) }}</text>
        </view>
        <view class="order-meta">
          <text>{{ order.side === 'buy' ? '买入' : '卖出' }} {{ order.quantity }}股</text>
          <text v-if="order.price">@ {{ order.price.toFixed(2) }}</text>
          <text class="order-time">{{ formatTime(order.created_at) }}</text>
        </view>
      </view>
    </scroll-view>

    <!-- 成交 Tab -->
    <scroll-view v-if="activeTab === 'trades'" class="content" scroll-y>
      <view v-if="trades.length === 0" class="empty-state">
        <text class="empty-icon">&#x1F4CA;</text>
        <text class="empty-text">暂无成交记录</text>
      </view>
      <view v-else v-for="trade in trades" :key="trade.id" class="trade-card">
        <view class="trade-top">
          <text class="trade-name">{{ trade.name || trade.symbol }}</text>
          <text :class="trade.side === 'buy' ? 'up' : 'down'">{{ trade.side === 'buy' ? '买入' : '卖出' }} {{ trade.quantity }}股</text>
        </view>
        <view class="trade-meta">
          <text>{{ trade.price.toFixed(2) }} &times; {{ trade.quantity }} = {{ formatMoney(trade.amount) }}</text>
          <text class="trade-time">{{ formatTime(trade.created_at) }}</text>
        </view>
      </view>
    </scroll-view>
    <Disclaimer />

    <!-- 下单二次确认 -->
    <ConfirmDialog
      :visible="showOrderConfirm"
      :title="(pendingOrderData?.side === 'buy' ? '确认买入' : '确认卖出')"
      :message="confirmOrderMessage"
      :impact="confirmOrderImpact"
      :confirm-text="pendingOrderData?.side === 'buy' ? '确认买入' : '确认卖出'"
      :cancel-text="'取消'"
      @confirm="confirmSubmitOrder"
      @cancel="cancelSubmitOrder"
    />
  </view>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { trackPageView } from '@/utils/tracker'
import Disclaimer from '@/components/compliance/Disclaimer.vue'
import LoadingSkeleton from '@/components/common/LoadingSkeleton.vue'
import NumberRolling from '@/components/common/NumberRolling.vue'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'
import { isOfflineMode, onNetworkChange } from '@/utils/offline'
import type { NetworkInfo } from '@/utils/network'
import {
  getAccount, getPositions, getOrders, placeOrder, getTrades, getPortfolioAnalytics,
  type AccountInfo, type PositionItem, type OrderItem, type TradeItem, type PositionAnalytics,
} from '@/api/portfolio'

const tabs = [
  { key: 'positions', label: '持仓' },
  { key: 'orders', label: '订单' },
  { key: 'trades', label: '成交' },
]

const STATUS_LABELS: Record<string, string> = {
  pending: '待成交',
  filled: '已成交',
  cancelled: '已撤单',
  rejected: '已拒绝',
}

const activeTab = ref('positions')
const isLoading = ref(false)
const submitting = ref(false)
const account = ref<AccountInfo | null>(null)
const positions = ref<PositionItem[]>([])
const orders = ref<OrderItem[]>([])
const trades = ref<TradeItem[]>([])
const orderForm = ref({ symbol: '', side: 'buy' as 'buy' | 'sell', quantity: '' })

// ─── 离线状态 ───
const offline = ref(isOfflineMode())
let unsubNetwork: (() => void) | null = null

// T-M011 持仓分析
const analytics = ref<PositionAnalytics | null>(null)
const sectorColors = ['#3B82F6', '#F59E0B', '#10B981', '#EF4444', '#8B5CF6', '#EC4899', '#06B6D4', '#F97316']

// ─── 二次确认 ───
const showOrderConfirm = ref(false)
const pendingOrderData = ref<{ symbol: string; side: 'buy' | 'sell'; quantity: number } | null>(null)

/** 确认弹窗信息 */
const confirmOrderMessage = computed(() => {
  if (!pendingOrderData.value) return ''
  const { symbol, side, quantity } = pendingOrderData.value
  const action = side === 'buy' ? '买入' : '卖出'
  return `${action} ${symbol}，数量 ${quantity} 股`
})

const confirmOrderImpact = computed(() => {
  if (!pendingOrderData.value) return ''
  const { side } = pendingOrderData.value
  if (side === 'buy') {
    return '下单后将扣减可用余额，A 股实行 T+1 结算规则，买入当日不可卖出。'
  }
  return '卖出后将释放持仓，成交后将收取印花税（0.1%）。请确认持仓数量充足。'
})

function formatMoney(v: number): string {
  if (v == null) return '0.00'
  return v.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function formatTime(iso: string): string {
  if (!iso) return ''
  const d = new Date(iso)
  return d.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

function getStatusLabel(s: string): string {
  return STATUS_LABELS[s] || s
}

function switchTab(key: string) {
  activeTab.value = key
  if (key === 'orders') loadOrders()
  else if (key === 'trades') loadTrades()
}

function goDetail(symbol: string) {
  uni.navigateTo({ url: '/pages/detail/index?symbol=' + symbol })
}

function goAnalytics() {
  uni.navigateTo({ url: '/pages/portfolio/analytics' })
}

async function loadAccount() {
  try { account.value = await getAccount() } catch { /* ignore */ }
}

async function loadPositions() {
  try {
    const res = await getPositions()
    positions.value = res.data || []
  } catch { /* ignore */ }
}

async function loadOrders() {
  try {
    const res = await getOrders()
    orders.value = res.data || []
  } catch { /* ignore */ }
}

async function loadTrades() {
  try {
    const res = await getTrades()
    trades.value = res.data || []
  } catch { /* ignore */ }
}

async function loadAnalytics() {
  try { analytics.value = await getPortfolioAnalytics() } catch { /* ignore */ }
}

async function refreshAll() {
  isLoading.value = true
  await Promise.all([loadAccount(), loadPositions(), loadAnalytics()])
  isLoading.value = false
}

async function submitOrder() {
  const sym = orderForm.value.symbol.trim().toUpperCase()
  const qty = parseInt(orderForm.value.quantity, 10)

  if (!sym) {
    uni.showToast({ title: '请输入股票代码', icon: 'none' })
    return
  }
  if (!qty || qty <= 0 || qty % 100 !== 0) {
    uni.showToast({ title: '数量须为 100 的整数倍', icon: 'none' })
    return
  }

  // 二次确认弹窗
  pendingOrderData.value = { symbol: sym, side: orderForm.value.side, quantity: qty }
  showOrderConfirm.value = true
}

/** 确认下单 */
async function confirmSubmitOrder() {
  if (!pendingOrderData.value) return
  const { symbol, side, quantity } = pendingOrderData.value

  showOrderConfirm.value = false
  submitting.value = true
  try {
    await placeOrder({ symbol, side, quantity, order_type: 'market' })
    uni.showToast({ title: '下单成功', icon: 'success' })
    orderForm.value = { symbol: '', side: 'buy', quantity: '' }
    await Promise.all([loadAccount(), loadPositions()])
  } catch (e: any) {
    const code = e.errorCode || ''
    if (code === 'INSUFFICIENT_BALANCE') {
      uni.showToast({ title: '余额不足，买不起', icon: 'none', duration: 2500 })
    } else if (code === 'INSUFFICIENT_AVAILABLE') {
      uni.showToast({ title: 'T+1 限制：今天买的明天才能卖', icon: 'none', duration: 2500 })
    } else if (code === 'NO_POSITION') {
      uni.showToast({ title: '未持有该股票', icon: 'none' })
    } else if (code === 'SYMBOL_NOT_FOUND') {
      uni.showToast({ title: '股票代码不存在', icon: 'none' })
    } else {
      uni.showToast({ title: e.detail || e.message || '下单失败', icon: 'none', duration: 2500 })
    }
  } finally {
    submitting.value = false
    pendingOrderData.value = null
  }
}

/** 取消下单 */
function cancelSubmitOrder() {
  showOrderConfirm.value = false
  pendingOrderData.value = null
}

onMounted(() => {
  refreshAll()
  // 注册网络状态监听
  unsubNetwork = onNetworkChange((info: NetworkInfo) => {
    offline.value = !info.isConnected
  })
})

onUnmounted(() => {
  // 清理网络监听
  if (unsubNetwork) {
    unsubNetwork()
    unsubNetwork = null
  }
})

onShow(() => {
  loadAnalytics()
  // 回前台时刷新离线状态
  offline.value = isOfflineMode()
  trackPageView('portfolio')
})
</script>

<style lang="scss" scoped>
.portfolio-page { min-height: 100vh; background: $bg-page; padding-bottom: env(safe-area-inset-bottom); }

/* Offline Banner */
.offline-banner {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12rpx;
  padding: 16rpx 24rpx;
  background: rgba(255, 193, 7, 0.12);
  border-bottom: 1rpx solid rgba(255, 193, 7, 0.3);
}

.offline-icon {
  font-size: 28rpx;
}

.offline-text {
  font-size: $font-size-sm;
  color: #F57F17;
  font-weight: 500;
}

/* Account Card */
.account-card {
  background: linear-gradient(135deg, $bg-primary 0%, #2d4a8a 100%);
  padding: 32rpx;
  color: $text-inverse;
}
.account-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24rpx; }
.account-type { font-size: $font-size-sm; color: rgba(255,255,255,0.7); }
.btn-refresh {
  font-size: $font-size-xs; color: rgba(255,255,255,0.9); background: rgba(255,255,255,0.15);
  border: none; padding: 8rpx 20rpx; border-radius: 20rpx;
  &::after { border: none; }
}
.account-main { margin-bottom: 32rpx; }
.total-label { font-size: $font-size-sm; color: rgba(255,255,255,0.6); }
.total-value { display: flex; align-items: baseline; gap: 4rpx; margin-top: 8rpx; }
.currency { font-size: $font-size-xl; font-weight: 600; opacity: 0.8; }
.amount { font-size: 64rpx; font-weight: 700; font-family: 'DIN Alternate','Helvetica Neue',Arial,sans-serif; }
.account-stats { display: flex; align-items: center; }
.stat-item { flex: 1; display: flex; flex-direction: column; }
.stat-label { font-size: $font-size-xs; color: rgba(255,255,255,0.6); margin-bottom: 8rpx; }
.stat-value { font-size: $font-size-lg; font-weight: 600;
  &.up { color: var(--color-up, #FF6B6B); }
  &.down { color: var(--color-down, #51CF66); }
}
.stat-divider { width: 1rpx; height: 60rpx; background: rgba(255,255,255,0.2); }

/* Tabs */
.tab-bar {
  display: flex; background: $bg-card; padding: 0 24rpx;
  border-bottom: 1rpx solid $border-color; position: sticky; top: 0; z-index: 10;
}
.tab-item {
  flex: 1; text-align: center; padding: 24rpx 0; font-size: $font-size-base;
  color: $text-secondary; position: relative;
  &.active { color: $color-primary; font-weight: 600;
    &::after {
      content: ''; position: absolute; bottom: 0; left: 50%;
      transform: translateX(-50%); width: 48rpx; height: 4rpx;
      background: $color-primary; border-radius: 2rpx;
    }
  }
}
.tab-badge {
  display: inline-block; background: $color-up; color: #fff; font-size: 18rpx;
  padding: 2rpx 10rpx; border-radius: 12rpx; margin-left: 8rpx; vertical-align: top;
}
.content { padding: 0 0 env(safe-area-inset-bottom); }

/* Section */
.section-header { display: flex; justify-content: space-between; align-items: center; padding: 24rpx 32rpx 12rpx; }
.section-title { font-size: $font-size-base; font-weight: 600; color: $text-primary; }
.section-tip { font-size: $font-size-xs; color: $text-hint; }

/* Skeleton */
.skeleton-list { padding: 24rpx; }
.skeleton-item { background: $bg-card; border-radius: $border-radius; padding: 28rpx; margin-bottom: 16rpx; }
.skeleton-line {
  background: linear-gradient(90deg,#f0f0f0 25%,#e0e0e0 50%,#f0f0f0 75%);
  background-size: 200% 100%; animation: shimmer 1.5s infinite; border-radius: 8rpx;
  &.title { width: 240rpx; height: 36rpx; margin-bottom: 12rpx; }
  &.price { width: 160rpx; height: 28rpx; }
}
@keyframes shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }

/* Empty */
.empty-state { display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 100rpx 0; }
.empty-icon { font-size: 80rpx; margin-bottom: 24rpx; }
.empty-text { font-size: $font-size-base; color: $text-secondary; }
.empty-sub { font-size: $font-size-xs; color: $text-hint; margin-top: 8rpx; }

/* Position Card */
.position-card {
  background: $bg-card; margin: 8rpx 24rpx; border-radius: $border-radius;
  padding: 24rpx; display: flex; align-items: center; cursor: pointer;
  &:active { opacity: 0.85; }
}
.pos-left { flex: 1; min-width: 0; }
.pos-name { font-size: $font-size-base; font-weight: 600; color: $text-primary; display: block; }
.pos-symbol { font-size: $font-size-xs; color: $text-hint; display: block; margin-top: 4rpx; }
.pos-mid { text-align: center; margin: 0 24rpx; flex-shrink: 0; }
.pos-price { font-size: $font-size-lg; font-weight: 700; color: $text-primary; display: block; }
.pos-cost { font-size: $font-size-xs; color: $text-hint; display: block; margin-top: 4rpx; }
.pos-right { text-align: right; flex-shrink: 0; }
.pos-pnl { font-size: $font-size-lg; font-weight: 700;
  &.up { color: $color-up; }
  &.down { color: $color-down; }
}
.pos-qty { font-size: $font-size-xs; color: $text-hint; display: block; margin-top: 4rpx; }

/* Trade Form */
.trade-section { margin: 24rpx; background: $bg-card; border-radius: $border-radius-lg; padding: 24rpx; }
.trade-form { display: flex; flex-direction: column; gap: 16rpx; }
.form-row { display: flex; align-items: center; gap: 12rpx; }
.form-label { width: 72rpx; font-size: $font-size-sm; color: $text-secondary; flex-shrink: 0; }
.form-input {
  flex: 1; height: 72rpx; background: $bg-page; border-radius: $border-radius;
  padding: 0 16rpx; font-size: $font-size-base; border: 1rpx solid $border-color;
}
.side-toggle { display: flex; border-radius: $border-radius; overflow: hidden; border: 1rpx solid $border-color; }
.side-btn {
  width: 72rpx; height: 72rpx; display: flex; align-items: center;
  justify-content: center; font-size: $font-size-base; font-weight: 600; cursor: pointer;
  &.buy { color: $color-up; &.active { background: $color-up; color: #fff; } }
  &.sell { color: $color-down; border-left: 1rpx solid $border-color; &.active { background: $color-down; color: #fff; } }
}
.btn-submit {
  width: 140rpx; height: 72rpx; border-radius: $border-radius; font-size: $font-size-base;
  font-weight: 600; color: #fff; border: none; flex-shrink: 0;
  &.buy { background: $color-up; }
  &.sell { background: $color-down; }
  &::after { border: none; }
  &[disabled] { opacity: 0.5; }
}

/* Order & Trade Cards */
.order-card, .trade-card { background: $bg-card; margin: 8rpx 24rpx; border-radius: $border-radius; padding: 20rpx 24rpx; }
.order-top, .trade-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8rpx; }
.order-name, .trade-name { font-size: $font-size-base; font-weight: 600; color: $text-primary; }
.order-status { font-size: $font-size-xs; padding: 4rpx 12rpx; border-radius: 6rpx;
  &.pending { background: #FFF8E1; color: #E6A23C; }
  &.filled { background: #F0FFF0; color: #67C23A; }
  &.cancelled { background: #F5F5F5; color: $text-hint; }
  &.rejected { background: #FFF0F0; color: #F56C6C; }
}
.order-meta, .trade-meta { display: flex; justify-content: space-between; align-items: center; font-size: $font-size-xs; color: $text-hint; }
.order-time, .trade-time { color: $text-hint; }

.up { color: $color-up; }
.down { color: $color-down; }

/* Analytics Board */
.analytics-board { padding: 0 24rpx; }
.analytics-board-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16rpx;
}
.analytics-board-title {
  font-size: $font-size-base;
  font-weight: 600;
  color: $text-primary;
}
.analytics-link {
  font-size: $font-size-sm;
  color: #4A90E2;
}
.analytics-card {
  background: $bg-card; border-radius: $border-radius-lg; padding: 28rpx;
  margin-bottom: 16rpx;
}
.analytics-card-title { font-size: $font-size-sm; font-weight: 600; color: $text-primary; display: block; margin-bottom: 16rpx; }

/* P&L Overview */
.overview-main { display: flex; align-items: baseline; gap: 12rpx; margin-bottom: 20rpx; }
.overview-pnl { font-size: 48rpx; font-weight: 800; font-family: 'DIN Alternate','Helvetica Neue',Arial,sans-serif; }
.overview-pnl-pct { font-size: $font-size-lg; font-weight: 600; }
.overview-sub { display: flex; gap: 32rpx; }
.overview-sub-item { display: flex; flex-wrap: wrap; align-items: baseline; gap: 6rpx; }
.sub-label { font-size: $font-size-xs; color: $text-hint; }
.sub-value { font-size: $font-size-base; font-weight: 600; color: $text-primary; }
.sub-pct { font-size: $font-size-xs; }

/* Metrics */
.metrics-grid { display: flex; margin-bottom: 20rpx; }
.metric-item {
  flex: 1; display: flex; flex-direction: column; align-items: center;
  padding: 12rpx 0; background: $bg-page; border-radius: $border-radius;
  &:not(:last-child) { margin-right: 12rpx; }
}
.metric-value { font-size: $font-size-xl; font-weight: 700; color: $text-primary; }
.metric-label { font-size: $font-size-xs; color: $text-hint; margin-top: 4rpx; }

.metrics-best-worst { display: flex; flex-direction: column; gap: 8rpx; }
.bw-item {
  display: flex; align-items: center; gap: 8rpx;
  background: $bg-page; border-radius: $border-radius; padding: 16rpx;
  cursor: pointer;
  &:active { opacity: 0.8; }
}
.bw-label { font-size: $font-size-xs; color: $text-hint; width: 56rpx; }
.bw-name { flex: 1; font-size: $font-size-sm; color: $text-primary; }
.bw-pnl { font-size: $font-size-base; font-weight: 600; }
.bw-arrow { font-size: $font-size-sm; color: $text-hint; }

.empty-analytics {
  text-align: center; padding: 32rpx 0; font-size: $font-size-sm; color: $text-hint;
}

/* Sector Distribution */
.sector-list { display: flex; flex-direction: column; gap: 16rpx; }
.sector-header { display: flex; align-items: center; gap: 8rpx; margin-bottom: 8rpx; }
.sector-dot { width: 16rpx; height: 16rpx; border-radius: 50%; flex-shrink: 0; }
.sector-name { font-size: $font-size-sm; color: $text-primary; flex: 1; }
.sector-cnt { font-size: $font-size-xs; color: $text-hint; }
.sector-weight { font-size: $font-size-sm; font-weight: 600; color: $text-primary; width: 80rpx; text-align: right; }
.sector-bar-wrap { height: 12rpx; background: $bg-page; border-radius: 6rpx; overflow: hidden; }
.sector-bar { height: 100%; border-radius: 6rpx; min-width: 4rpx; transition: width 0.5s ease; }
</style>
