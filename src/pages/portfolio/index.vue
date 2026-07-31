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
        <button class="btn-topup" @click="showTopupModal = true">充值</button>
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
      <view class="analytics-card">
        <text class="analytics-card-title">持仓分析</text>
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
              <text class="metric-value">{{ formatPercent(analytics.win_rate, 0) }}</text>
              <text class="metric-label">胜率</text>
            </view>
            <view class="metric-item">
              <text class="metric-value">{{ formatPercent(analytics.top_holdings_concentration, 1) }}</text>
              <text class="metric-label">集中度</text>
            </view>
          </view>
          <view class="metrics-best-worst">
            <view class="bw-item" v-if="analytics.best_position" @click="goDetail(analytics.best_position.symbol)">
              <text class="bw-label">最佳</text>
              <text class="bw-name">{{ analytics.best_position.name }}</text>
              <text class="bw-pnl up">+{{ formatPercent(analytics.best_position.profit_pct, 2) }}</text>
              <text class="bw-arrow">&gt;</text>
            </view>
            <view class="bw-item" v-if="analytics.worst_position" @click="goDetail(analytics.worst_position.symbol)">
              <text class="bw-label">最差</text>
              <text class="bw-name">{{ analytics.worst_position.name }}</text>
              <text class="bw-pnl down">{{ formatPercent(analytics.worst_position.profit_pct, 2) }}</text>
              <text class="bw-arrow">&gt;</text>
            </view>
          </view>
        </template>
      </view>
      <view class="analytics-card" v-if="analytics.holdings_distribution && analytics.holdings_distribution.length">
        <text class="analytics-card-title">行业分布</text>
        <view class="sector-list">
          <view class="sector-item" v-for="(item, idx) in analytics.holdings_distribution" :key="item.sector">
            <view class="sector-header">
              <view class="sector-dot" :style="{ background: sectorColors[idx % sectorColors.length] }"></view>
              <text class="sector-name">{{ item.sector }}</text>
              <text class="sector-cnt">{{ item.count }}只</text>
              <text class="sector-weight">{{ formatPercent(item.weight, 1) }}</text>
            </view>
            <view class="sector-bar-wrap">
              <view class="sector-bar" :style="{ width: item.weight + '%', background: sectorColors[idx % sectorColors.length] }"></view>
            </view>
          </view>
        </view>
      </view>
    </view>

    <!-- Tab 切换（精简为2个主Tab） -->
    <view class="tab-bar">
      <view
        v-for="tab in tabs"
        :key="tab.key"
        class="tab-item"
        :class="{ active: activeTab === tab.key }"
        @click="switchTab(tab.key)"
      >
        {{ tab.label }}
      </view>
    </view>

    <!-- 持仓 Tab -->
    <scroll-view v-if="activeTab === 'positions'" class="content" scroll-y>
      <view v-if="positions.length === 0" class="empty-state">
        <text class="empty-icon">&#x1F4ED;</text>
        <text class="empty-text">暂无持仓</text>
        <text class="empty-sub">点击下方"交易"按钮开始模拟下单</text>
      </view>

      <view v-else>
        <view class="section-header">
          <text class="section-title">持仓 ({{ positions.length }})</text>
          <text class="section-tip">T+1 结算 · 点击可快速卖出</text>
        </view>
        <view
          v-for="pos in positions"
          :key="pos.symbol"
          class="position-card"
          @click="openTradeForSell(pos)"
        >
          <view class="pos-left">
            <text class="pos-name">{{ pos.name }}</text>
            <text class="pos-symbol">{{ pos.symbol }}</text>
          </view>
          <view class="pos-mid">
            <text class="pos-price">{{ formatMoney(pos.market_price, 2) }}</text>
            <text class="pos-cost">成本 {{ formatMoney(pos.cost_price, 2) }}</text>
          </view>
          <view class="pos-right">
            <text class="pos-pnl" :class="pos.profit >= 0 ? 'up' : 'down'">
              {{ formatSigned(pos.profit, 2) }}
            </text>
            <text class="pos-qty">{{ pos.quantity }}股 / 可卖{{ pos.available }}</text>
          </view>
        </view>
      </view>

      <!-- 底部占位，防止内容被FAB遮挡 -->
      <view style="height: 160rpx"></view>
    </scroll-view>

    <!-- AI托管 Tab -->
    <!-- 订单 Tab -->
    <scroll-view v-if="activeTab === 'orders'" class="content" scroll-y @scrolltolower="loadMoreOrders">
      <view v-if="orders.length === 0" class="empty-state">
        <text class="empty-icon">📄</text>
        <text class="empty-text">暂无订单</text>
        <text class="empty-sub">使用交易面板开始下单</text>
      </view>
      <view v-else v-for="order in orders" :key="order.id" class="order-card">
        <view class="order-top">
          <text class="order-name">{{ order.name || order.symbol }}</text>
          <text class="order-status" :class="order.status">{{ getStatusLabel(order.status) }}</text>
        </view>
        <view class="order-meta">
          <text>{{ order.side === 'buy' ? '买入' : '卖出' }} {{ order.quantity }}股</text>
          <text v-if="order.price">@ {{ formatMoney(order.price, 2) }}</text>
          <text class="order-time">{{ formatTime(order.created_at) }}</text>
        </view>
      </view>
      <view v-if="orders.length > 0 && ordersHasMore" class="load-more-bar" @click="loadMoreOrders">
        <uni-load-more v-if="ordersLoadingMore" status="loading" />
        <text v-else class="load-more-text">加载更多</text>
      </view>
    </scroll-view>

    <!-- 成交 Tab -->
    <scroll-view v-if="activeTab === 'trades'" class="content" scroll-y @scrolltolower="loadMoreTrades">
      <view v-if="trades.length === 0" class="empty-state">
        <text class="empty-icon">📊</text>
        <text class="empty-text">暂无成交记录</text>
        <text class="empty-sub">订单成交后记录将显示在此</text>
      </view>
      <view v-else v-for="trade in trades" :key="trade.id" class="trade-card">
        <view class="trade-top">
          <text class="trade-name">{{ trade.name || trade.symbol }}</text>
          <text :class="trade.side === 'buy' ? 'up' : 'down'">{{ trade.side === 'buy' ? '买入' : '卖出' }} {{ trade.quantity }}股</text>
        </view>
        <view class="trade-meta">
          <text>{{ formatMoney(trade.price, 2) }} &times; {{ trade.quantity }} = {{ formatMoney(trade.amount) }}</text>
          <text class="trade-time">{{ formatTime(trade.created_at) }}</text>
        </view>
        <view class="trade-source">
          <text v-if="trade.source === 'agent'" class="src-tag src-agent">{{ trade.trader_name }} 手笔</text>
          <text v-else class="src-tag src-user">用户自己</text>
        </view>
      </view>
    </scroll-view>

    <Disclaimer />

    <!-- 浮动交易按钮 (FAB) -->
    <view class="trade-fab" @click="openTradeModal()">
      <text class="fab-icon">💹</text>
      <text class="fab-label">交易</text>
    </view>

    <!-- ─── 全屏交易面板 Modal ─── -->
    <view class="trade-modal-mask" v-if="showTradeModal" @click="closeTradeModal">
      <view class="trade-modal" @click.stop>
        <!-- 顶部导航 -->
        <view class="trade-modal-header">
          <text class="trade-modal-title">模拟交易</text>
          <view class="trade-modal-close" @click="closeTradeModal">✕</view>
        </view>

        <scroll-view class="trade-modal-body" scroll-y>

          <!-- 1. 股票搜索区 -->
          <view class="tm-section">
            <view class="tm-search-wrap">
              <input
                class="tm-search-input"
                v-model="searchQuery"
                placeholder="输入股票代码/名称搜索"
                :adjust-position="true"
                :cursor-spacing="20"
                @input="onSearchInput"
                @focus="searchFocused = true"
              />
              <text class="tm-search-icon">🔍</text>
            </view>
            <view v-if="searchResults.length > 0 && searchFocused" class="tm-search-dropdown">
              <view
                v-for="r in searchResults"
                :key="r.symbol"
                class="tm-search-item"
                @click="selectStock(r)"
              >
                <view class="tm-search-item-left">
                  <text class="tm-search-name">{{ r.name }}</text>
                  <text class="tm-search-code">{{ r.symbol }}</text>
                </view>
                <text v-if="r.price != null" class="tm-search-price" :class="(r.change_pct ?? 0) >= 0 ? 'up' : 'down'">
                  {{ formatMoney(r.price, 2) }}
                </text>
              </view>
            </view>
          </view>

          <!-- 2. 行情展示卡 -->
          <view class="tm-quote-card" v-if="quoteData">
            <view class="tm-quote-top">
              <view class="tm-quote-left">
                <text class="tm-quote-name">{{ quoteData.name }}</text>
                <text class="tm-quote-symbol">{{ quoteData.symbol }}</text>
              </view>
              <view class="tm-quote-right">
                <text class="tm-quote-price" :class="quoteData.change >= 0 ? 'up' : 'down'">{{ formatMoney(quoteData.price, 2) }}</text>
                <text class="tm-quote-change" :class="quoteData.change >= 0 ? 'up' : 'down'">
                  {{ quoteData.change >= 0 ? '+' : '' }}{{ formatPercent(quoteData.change_pct, 2) }}
                </text>
              </view>
            </view>
            <view class="tm-quote-detail">
              <view class="tm-qd-item">
                <text class="tm-qd-label">最高</text>
                <text class="tm-qd-value">{{ formatMoney(quoteData.high, 2) }}</text>
              </view>
              <view class="tm-qd-item">
                <text class="tm-qd-label">最低</text>
                <text class="tm-qd-value">{{ formatMoney(quoteData.low, 2) }}</text>
              </view>
              <view class="tm-qd-item">
                <text class="tm-qd-label">昨收</text>
                <text class="tm-qd-value">{{ formatMoney(quoteData.prev_close, 2) }}</text>
              </view>
              <view class="tm-qd-item">
                <text class="tm-qd-label">涨跌额</text>
                <text class="tm-qd-value" :class="quoteData.change >= 0 ? 'up' : 'down'">{{ formatSigned(quoteData.change, 2) }}</text>
              </view>
            </view>
          </view>
          <view class="tm-quote-card tm-quote-empty" v-else>
            <text class="tm-quote-empty-text">请搜索并选择一只股票</text>
          </view>

          <!-- 3. 交易方向切换 -->
          <view class="tm-side-switch" v-if="quoteData">
            <view
              class="tm-side-btn"
              :class="{ active: tradeSide === 'buy' }"
              @click="tradeSide = 'buy'; calcPresets()"
            >买入</view>
            <view
              class="tm-side-btn sell"
              :class="{ active: tradeSide === 'sell' }"
              @click="tradeSide = 'sell'; calcPresets()"
            >卖出</view>
          </view>

          <!-- 4. 价格输入 -->
          <view class="tm-section" v-if="quoteData">
            <text class="tm-section-label">委托价格</text>
            <view class="tm-price-row">
              <input
                class="tm-price-input"
                v-model="tradePrice"
                type="digit"
                placeholder="输入价格"
                :adjust-position="true"
                :cursor-spacing="20"
              />
              <view class="tm-price-refs">
                <text class="tm-price-ref" @click="tradePrice = String(quoteData.price)">
                  市价 {{ formatMoney(quoteData.price, 2) }}
                </text>
                <text class="tm-price-ref" @click="tradePrice = String(formatMoney(quoteData.price * 1.10, 2))">
                  涨停 {{ formatMoney(quoteData.price * 1.10, 2) }}
                </text>
                <text class="tm-price-ref" @click="tradePrice = String(formatMoney(quoteData.price * 0.90, 2))">
                  跌停 {{ formatMoney(quoteData.price * 0.90, 2) }}
                </text>
              </view>
            </view>
          </view>

          <!-- 5. 数量选择 -->
          <view class="tm-section" v-if="quoteData">
            <text class="tm-section-label">委托数量</text>
            <input
              class="tm-qty-input"
              v-model="tradeQty"
              type="number"
              placeholder="100的整数倍"
              :adjust-position="true"
              :cursor-spacing="20"
            />
            <view class="tm-qty-presets">
              <view
                v-for="p in qtyPresets"
                :key="p.label"
                class="tm-qty-chip"
                :class="{ active: p.active }"
                @click="applyPreset(p)"
              >
                {{ p.label }}
              </view>
            </view>
            <view class="tm-qty-hint">
              <text v-if="tradeSide === 'buy'">可用余额：&yen;{{ formatMoney(account?.balance || 0) }}</text>
              <text v-else-if="tradeSide === 'sell' && currentPosition">
                可卖：{{ currentPosition.available }}股 / 成本：{{ formatMoney(currentPosition.cost_price, 2) }}
              </text>
            </view>
          </view>

          <!-- 6. 预估金额 -->
          <view class="tm-section" v-if="quoteData && tradePrice && tradeQty">
            <view class="tm-estimate">
              <text class="tm-estimate-label">预估金额</text>
              <text class="tm-estimate-value">
                &yen;{{ formatMoney(parseFloat(tradePrice) * parseInt(tradeQty || '0')) }}
              </text>
            </view>
          </view>

          <!-- 7. 交易按钮 -->
          <view class="tm-action" v-if="quoteData">
            <button
              class="tm-submit-btn"
              :class="tradeSide"
              :disabled="!canTrade || submitting"
              @click="handleTradeSubmit"
            >
              <text v-if="!canTrade">非交易时段</text>
              <text v-else-if="submitting">提交中...</text>
              <text v-else>{{ tradeSide === 'buy' ? '买入' : '卖出' }} {{ quoteData.name }}</text>
            </button>
          </view>

          <!-- 8. 最近订单 -->
          <view class="tm-section" v-if="orders.length > 0">
            <view class="tm-recent-header">
              <text class="tm-section-label">最近订单</text>
              <text class="tm-view-all" @click="switchTab('orders'); closeTradeModal()">查看全部 &gt;</text>
            </view>
            <view v-for="o in orders.slice(0, 3)" :key="o.id" class="tm-recent-order">
              <view class="tm-ro-top">
                <text class="tm-ro-name">{{ o.name || o.symbol }}</text>
                <text class="tm-ro-status" :class="o.status">{{ getStatusLabel(o.status) }}</text>
              </view>
              <view class="tm-ro-meta">
                <text>{{ o.side === 'buy' ? '买入' : '卖出' }} {{ o.quantity }}股</text>
                <text class="tm-ro-time">{{ formatTime(o.created_at) }}</text>
              </view>
            </view>
          </view>

          <view style="height: 40rpx"></view>
        </scroll-view>
      </view>
    </view>

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

    <!-- 充值弹窗 -->
    <view class="topup-modal-mask" v-if="showTopupModal" @click="showTopupModal = false">
      <view class="topup-modal" @click.stop>
        <text class="topup-modal-title">模拟充值</text>
        <text class="topup-modal-sub">选择充值金额（模拟资金）</text>
        <view class="topup-options">
          <view
            class="topup-option"
            :class="{ active: topupAmount === 100000 }"
            @click="topupAmount = 100000"
          >
            <text class="topup-opt-amount">10 万</text>
            <text class="topup-opt-label">￥100,000</text>
          </view>
          <view
            class="topup-option"
            :class="{ active: topupAmount === 1000000 }"
            @click="topupAmount = 1000000"
          >
            <text class="topup-opt-amount">100 万</text>
            <text class="topup-opt-label">￥1,000,000</text>
          </view>
        </view>
        <view class="topup-actions">
          <button class="topup-btn-cancel" @click="showTopupModal = false">取消</button>
          <button class="topup-btn-confirm" :disabled="topupSubmitting" @click="handleTopup">
            {{ topupSubmitting ? '充值中...' : '确认充值' }}
          </button>
        </view>
      </view>
    </view>
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
  getAccount, getPositions, getOrders, placeOrder, getTrades, getPortfolioAnalytics, topupAccount,
  type AccountInfo, type PositionItem, type OrderItem, type TradeItem, type PositionAnalytics,
} from '@/api/portfolio'
import { searchStocks, fetchQuote, type SearchResult, type QuoteSnapshot } from '@/api/market'
import { formatPercent, formatSigned } from '@/utils/format'
import { useShowRefresh, touchRefreshKey } from '@/utils/refresh-cache'

// ─── Tab 定义 ───
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
const ordersPage = ref(1)
const ordersTotal = ref(0)
const ordersHasMore = ref(true)
const ordersLoadingMore = ref(false)
const trades = ref<TradeItem[]>([])
const tradesPage = ref(1)
const tradesTotal = ref(0)
const tradesHasMore = ref(true)
const tradesLoadingMore = ref(false)
const orderForm = ref({ symbol: '', side: 'buy' as 'buy' | 'sell', quantity: '' })

// ─── 离线状态 ───
const offline = ref(isOfflineMode())
let unsubNetwork: (() => void) | null = null

// ─── 持仓分析 ───
const analytics = ref<PositionAnalytics | null>(null)
const sectorColors = ['#3B82F6', '#F59E0B', '#10B981', '#EF4444', '#8B5CF6', '#EC4899', '#06B6D4', '#F97316']

// ─── AI托管状态 ───
const hostedStatus = ref<HostedStatus | null>(null)
const hostedLoading = ref(false)

// ─── 二次确认 ───
const showOrderConfirm = ref(false)
const pendingOrderData = ref<{ symbol: string; side: 'buy' | 'sell'; quantity: number } | null>(null)

// ─── 充值 ───
const showTopupModal = ref(false)
const topupAmount = ref(100000)
const topupSubmitting = ref(false)

// ─── 交易面板 ───
const showTradeModal = ref(false)
const searchQuery = ref('')
const searchResults = ref<SearchResult[]>([])
const searchFocused = ref(false)
const quoteData = ref<QuoteSnapshot | null>(null)
const tradeSide = ref<'buy' | 'sell'>('buy')
const tradePrice = ref('')
const tradeQty = ref('')
const selectedSymbol = ref('')
const buyInPosition = ref(false) // 是否是从持仓点击进来的

interface QtyPreset {
  label: string
  value: number
  active: boolean
}
const qtyPresets = ref<QtyPreset[]>([])

// ─── 计算属性 ───

/** 当前持仓中是否有选中的股票（卖出时用） */
const currentPosition = computed(() => {
  if (!selectedSymbol.value || !positions.value.length) return null
  return positions.value.find(p => p.symbol === selectedSymbol.value) || null
})

/** 是否可以交易（交易时段检查） */
const canTrade = computed(() => {
  return isMarketHours()
})

/** 确认弹窗信息 */
const confirmOrderMessage = computed(() => {
  if (!pendingOrderData.value) return ''
  const { symbol, side, quantity } = pendingOrderData.value
  const action = side === 'buy' ? '买入' : '卖出'
  const price = tradePrice.value ? parseFloat(tradePrice.value).toFixed(2) : '市价'
  return `${action} ${symbol}，${quantity}股 @ ${price}`
})

const confirmOrderImpact = computed(() => {
  if (!pendingOrderData.value) return ''
  const { side } = pendingOrderData.value
  if (side === 'buy') {
    return '下单后将扣减可用余额，A 股实行 T+1 结算规则，买入当日不可卖出。'
  }
  return '卖出后将释放持仓，成交后将收取印花税（0.1%）。请确认持仓数量充足。'
})

// ─── 工具函数 ───

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

/** A股交易时段判断 */
function isMarketHours(): boolean {
  const now = new Date()
  const utc8 = new Date(now.getTime() + now.getTimezoneOffset() * 60000 + 8 * 3600000)
  const dow = utc8.getDay()
  const h = utc8.getHours()
  const m = utc8.getMinutes()
  const mins = h * 60 + m
  if (dow === 0 || dow === 6) return false
  // 9:30-11:30, 13:00-15:00
  return (mins >= 570 && mins < 690) || (mins >= 780 && mins < 900)
}

// ─── 交易面板逻辑 ───

/** 打开交易面板 */
function openTradeModal() {
  showTradeModal.value = true
  buyInPosition.value = false
  loadOrders()
}

/** 从持仓点击打开（卖出方向） */
function openTradeForSell(pos: PositionItem) {
  showTradeModal.value = true
  buyInPosition.value = true
  selectedSymbol.value = pos.symbol
  searchQuery.value = pos.name || pos.symbol
  tradeSide.value = 'sell'
  tradeQty.value = ''
  tradePrice.value = ''
  loadQuote(pos.symbol)
  loadOrders()
}

/** 关闭交易面板 */
function closeTradeModal() {
  showTradeModal.value = false
  searchQuery.value = ''
  searchResults.value = []
  searchFocused.value = false
  quoteData.value = null
  selectedSymbol.value = ''
  tradePrice.value = ''
  tradeQty.value = ''
  tradeSide.value = 'buy'
  qtyPresets.value = []
}

/** 股票搜索输入 */
let searchTimer: ReturnType<typeof setTimeout> | null = null
async function onSearchInput() {
  if (searchTimer) clearTimeout(searchTimer)
  const q = searchQuery.value.trim()
  if (!q) {
    searchResults.value = []
    return
  }
  searchTimer = setTimeout(async () => {
    searchResults.value = await searchStocks(q, 10)
  }, 200)
}

/** 选中股票 */
async function selectStock(r: SearchResult) {
  selectedSymbol.value = r.symbol
  searchQuery.value = r.name && r.symbol ? `${r.name} (${r.symbol})` : r.symbol
  searchResults.value = []
  searchFocused.value = false
  tradePrice.value = ''
  tradeQty.value = ''
  if (buyInPosition.value) {
    tradeSide.value = 'sell'
    buyInPosition.value = false
  } else {
    tradeSide.value = 'buy'
  }
  loadQuote(r.symbol)
}

/** 加载行情 */
async function loadQuote(symbol: string) {
  try {
    quoteData.value = await fetchQuote(symbol)
    tradePrice.value = String(quoteData.value.price)
    calcPresets()
  } catch (e) {
    console.error('[Portfolio] loadQuote 失败', e);
    uni.showToast({ title: '获取行情失败', icon: 'none' })
  }
}

/** 计算快捷数量按钮 */
function calcPresets() {
  const price = parseFloat(tradePrice.value)
  if (!price || price <= 0) return
  const presets: QtyPreset[] = []
  if (tradeSide.value === 'buy') {
    const balance = account.value?.balance || 0
    const maxShares = Math.floor(balance / price / 100) * 100
    const ratios = [0.25, 0.5, 0.75, 1]
    const labels = ['1/4仓', '1/2仓', '3/4仓', '全仓']
    presets.push(...ratios.map((r, i) => ({
      label: labels[i],
      value: Math.floor(maxShares * r / 100) * 100,
      active: false,
    })))
  } else {
    const available = currentPosition.value?.available || 0
    if (available > 0) {
      const ratios = [0.25, 0.5, 0.75, 1]
      const labels = ['1/4', '1/2', '3/4', '全部']
      presets.push(...ratios.map((r, i) => ({
        label: labels[i],
        value: Math.round(available * r / 100) * 100,
        active: false,
      })))
    }
  }
  qtyPresets.value = presets
}

/** 应用快捷数量 */
function applyPreset(p: QtyPreset) {
  if (p.value <= 0) {
    uni.showToast({ title: '可用资金/持仓不足', icon: 'none' })
    return
  }
  tradeQty.value = String(p.value)
  qtyPresets.value = qtyPresets.value.map(pp => ({
    ...pp,
    active: pp.label === p.label,
  }))
}

/** 提交交易（先校验再确认） */
async function handleTradeSubmit() {
  const sym = selectedSymbol.value
  const qty = parseInt(tradeQty.value, 10)
  const price = parseFloat(tradePrice.value)

  if (!sym) {
    uni.showToast({ title: '请先搜索选择股票', icon: 'none' })
    return
  }
  if (!qty || qty <= 0 || qty % 100 !== 0) {
    uni.showToast({ title: '数量须为 100 的整数倍', icon: 'none' })
    return
  }
  if (!price || price <= 0) {
    uni.showToast({ title: '请输入有效价格', icon: 'none' })
    return
  }

  // 二次确认
  pendingOrderData.value = { symbol: sym, side: tradeSide.value, quantity: qty }
  showOrderConfirm.value = true
  submitting.value = true
}

// ─── 下单确认逻辑 ───

/** 确认下单 */
async function confirmSubmitOrder() {
  if (!pendingOrderData.value) return
  const { symbol, side, quantity } = pendingOrderData.value
  const price = parseFloat(tradePrice.value) || 0

  showOrderConfirm.value = false
  submitting.value = true
  try {
    await placeOrder({ symbol, side, quantity, order_type: 'LIMIT', price }, true)
    uni.showToast({ title: '下单成功', icon: 'success' })
    uni.vibrateShort({ type: 'medium' })
    closeTradeModal()
    await Promise.all([loadAccount(), loadPositions(), loadOrders()])
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
  submitting.value = false
}

// ─── 数据加载 ───

function switchTab(key: string) {
  activeTab.value = key
  if (key === 'orders') loadOrders()
  if (key === 'trades') loadTrades()
}

function goDetail(symbol: string) {
  uni.navigateTo({ url: '/pages/detail/index?code=' + symbol })
}

function goAnalytics() {
  uni.navigateTo({ url: '/pages/portfolio/analytics' })
}

async function loadAccount() {
  try { account.value = await getAccount() } catch (e) { console.error('[Portfolio] loadAccount 失败', e); }
}

async function loadPositions() {
  try {
    const res = await getPositions()
    positions.value = res.data || []
  } catch (e) { console.error('[Portfolio] loadPositions 失败', e); }
}

async function loadOrders() {
  ordersPage.value = 1
  ordersHasMore.value = true
  try {
    const res = await getOrders(undefined, 20, 0)
    orders.value = res.data || []
    ordersTotal.value = res.total
    ordersHasMore.value = res.data.length >= 20
  } catch (e) { console.error('[Portfolio] loadOrders 失败', e); }
}

async function loadMoreOrders() {
  if (ordersLoadingMore.value || !ordersHasMore.value) return
  ordersLoadingMore.value = true
  try {
    const offset = ordersPage.value * 20
    const res = await getOrders(undefined, 20, offset)
    orders.value.push(...(res.data || []))
    ordersPage.value++
    ordersHasMore.value = orders.value.length < res.total
  } catch (e) { console.error('[Portfolio] loadMoreOrders 失败', e); }
  finally { ordersLoadingMore.value = false }
}

async function loadTrades() {
  tradesPage.value = 1
  tradesHasMore.value = true
  try {
    const res = await getTrades(20, 0)
    trades.value = res.data || []
    tradesTotal.value = res.total
    tradesHasMore.value = res.data.length >= 20
  } catch (e) { console.error('[Portfolio] loadTrades 失败', e); }
}

async function loadMoreTrades() {
  if (tradesLoadingMore.value || !tradesHasMore.value) return
  tradesLoadingMore.value = true
  try {
    const offset = tradesPage.value * 20
    const res = await getTrades(20, offset)
    trades.value.push(...(res.data || []))
    tradesPage.value++
    tradesHasMore.value = trades.value.length < res.total
  } catch (e) { console.error('[Portfolio] loadMoreTrades 失败', e); }
  finally { tradesLoadingMore.value = false }
}

async function loadAnalytics() {
  try { analytics.value = await getPortfolioAnalytics() } catch (e) { console.error('[Portfolio] loadAnalytics 失败', e); }
}

async function loadHostedStatus() {
  hostedLoading.value = true
  try { hostedStatus.value = await getHostedStatus() } catch (e) { console.error('[Portfolio] loadHostedStatus 失败', e); }
  finally { hostedLoading.value = false }
}

async function refreshAll() {
  touchRefreshKey('portfolio')
  isLoading.value = true
  await Promise.all([loadAccount(), loadPositions(), loadAnalytics()])
  isLoading.value = false
}

async function handleTopup() {
  if (!topupAmount.value) return
  topupSubmitting.value = true
  try {
    const res = await topupAccount(topupAmount.value)
    uni.showToast({ title: res.message || '充值成功', icon: 'success', duration: 2000 })
    uni.vibrateShort({ type: 'medium' })
    showTopupModal.value = false
    await loadAccount()
    await loadAnalytics()
  } catch (e: any) {
    uni.showToast({ title: e?.message || '充值失败', icon: 'none' })
  } finally {
    topupSubmitting.value = false
  }
}

onMounted(() => {
  refreshAll()
  unsubNetwork = onNetworkChange((info: NetworkInfo) => {
    offline.value = !info.isConnected
  })
})

onUnmounted(() => {
  if (unsubNetwork) {
    unsubNetwork()
    unsubNetwork = null
  }
})
onShow(() => {
  useShowRefresh('portfolio', () => {
    loadAnalytics()
    if (activeTab.value === 'orders') loadOrders()
    if (activeTab.value === 'trades') loadTrades()
  })
  offline.value = isOfflineMode()
  trackPageView('portfolio')
})

</script>
<style lang="scss" scoped>
.portfolio-page { min-height: 100vh; background: $bg-page; padding-bottom: env(safe-area-inset-bottom); }

/* Offline Banner */
.offline-banner {
  display: flex; align-items: center; justify-content: center; gap: 12rpx;
  padding: 16rpx 24rpx; background: rgba(255, 193, 7, 0.12);
  border-bottom: 1rpx solid rgba(255, 193, 7, 0.3);
}
.offline-icon { font-size: 28rpx; }
.offline-text { font-size: $font-size-sm; color: #F57F17; font-weight: 500; }

/* Account Card */
.account-card {
  background: linear-gradient(135deg, $bg-primary 0%, #2d4a8a 100%);
  padding: 32rpx; color: $text-inverse;
}
.account-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24rpx; }
.account-type { font-size: $font-size-sm; color: rgba(255,255,255,0.7); }
.btn-refresh {
  font-size: $font-size-xs; color: rgba(255,255,255,0.9); background: rgba(255,255,255,0.15);
  border: none; padding: 8rpx 20rpx; border-radius: 20rpx;
  &::after { border: none; }
}
.btn-topup {
  font-size: $font-size-xs; color: #fff; background: linear-gradient(135deg, #F59E0B, #F97316);
  border: none; padding: 8rpx 20rpx; border-radius: 20rpx; font-weight: 600;
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
.content { padding: 0 0 env(safe-area-inset-bottom); }

/* Section */
.section-header { display: flex; justify-content: space-between; align-items: center; padding: 24rpx 32rpx 12rpx; }
.section-title { font-size: $font-size-base; font-weight: 600; color: $text-primary; }
.section-tip { font-size: $font-size-xs; color: $text-hint; }

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
  position: relative;
}
.position-card::after {
  content: '快速卖出 ›'; position: absolute; right: 24rpx; bottom: -4rpx;
  font-size: 18rpx; color: $color-up; opacity: 0.5;
}
.pos-left { flex: 1; min-width: 0; }
.pos-name { font-size: $font-size-base; font-weight: 600; color: $text-primary; display: block; }
.pos-symbol { font-size: $font-size-xs; color: $text-hint; display: block; margin-top: 4rpx; }
.pos-mid { text-align: center; margin: 0 24rpx; flex-shrink: 0; }
.pos-price { font-size: $font-size-lg; font-weight: 700; color: $text-primary; display: block; }
.pos-cost { font-size: $font-size-xs; color: $text-hint; display: block; margin-top: 4rpx; }
.pos-right { text-align: right; flex-shrink: 0; }
.pos-pnl { font-size: $font-size-lg; font-weight: 700;
  &.up { color: $color-up; } &.down { color: $color-down; }
}
.pos-qty { font-size: $font-size-xs; color: $text-hint; display: block; margin-top: 4rpx; }

/* ─── Floating Action Button ─── */
.trade-fab {
  position: fixed; right: 32rpx; bottom: 120rpx; z-index: 100;
  display: flex; flex-direction: column; align-items: center; gap: 4rpx;
  width: 112rpx; height: 112rpx; border-radius: 56rpx;
  background: linear-gradient(135deg, #FF4757, #E74C3C);
  box-shadow: 0 6rpx 24rpx rgba(231, 76, 60, 0.45);
  justify-content: center;
  cursor: pointer;
  transition: transform 0.15s;
  &:active { transform: scale(0.92); }
}
.fab-icon { font-size: 40rpx; line-height: 1; }
.fab-label { font-size: 22rpx; color: #fff; font-weight: 700; letter-spacing: 2rpx; }

/* ─── 交易面板 Modal ─── */
.trade-modal-mask {
  position: fixed; top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.6); z-index: 999;
  display: flex; align-items: flex-end;
}
.trade-modal {
  width: 100%; height: 90vh; background: $bg-page;
  border-radius: 24rpx 24rpx 0 0;
  display: flex; flex-direction: column;
}
.trade-modal-header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 28rpx 32rpx; background: #fff;
  border-bottom: 1rpx solid $border-color;
  flex-shrink: 0;
}
.trade-modal-title { font-size: 34rpx; font-weight: 700; color: $text-primary; }
.trade-modal-close {
  width: 52rpx; height: 52rpx; border-radius: 26rpx;
  background: #f5f5f5; display: flex; align-items: center;
  justify-content: center; font-size: 28rpx; color: #999; cursor: pointer;
}
.trade-modal-body { flex: 1; padding: 20rpx 32rpx; }
.trade-modal-body::-webkit-scrollbar { display: none; }

/* 通用 section */
.tm-section { margin-bottom: 20rpx; }
.tm-section-label { font-size: $font-size-sm; font-weight: 600; color: $text-primary; display: block; margin-bottom: 12rpx; }

/* 搜索区 */
.tm-search-wrap { position: relative; }
.tm-search-input {
  width: 100%; height: 80rpx; background: #f5f6fa; border-radius: 16rpx;
  padding: 0 32rpx 0 72rpx; font-size: $font-size-base;
  box-sizing: border-box;
}
.tm-search-icon { position: absolute; left: 24rpx; top: 50%; transform: translateY(-50%); font-size: 32rpx; }
.tm-search-dropdown {
  background: #fff; border-radius: 12rpx; margin-top: 8rpx;
  box-shadow: 0 4rpx 20rpx rgba(0,0,0,0.1); max-height: 400rpx; overflow-y: auto;
}
.tm-search-item {
  display: flex; justify-content: space-between; align-items: center;
  padding: 20rpx 24rpx; cursor: pointer; border-bottom: 1rpx solid #f0f0f0;
  &:active { background: #f5f6fa; }
  &:last-child { border-bottom: none; }
}
.tm-search-item-left { display: flex; flex-direction: column; gap: 4rpx; }
.tm-search-name { font-size: $font-size-base; font-weight: 600; color: $text-primary; }
.tm-search-code { font-size: $font-size-xs; color: $text-hint; }
.tm-search-price { font-size: $font-size-base; font-weight: 700; }
.tm-search-price.up { color: $color-up; }
.tm-search-price.down { color: $color-down; }

/* 行情卡 */
.tm-quote-card {
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
  border-radius: 16rpx; padding: 28rpx; margin-bottom: 20rpx;
}
.tm-quote-empty {
  display: flex; align-items: center; justify-content: center;
  min-height: 160rpx;
}
.tm-quote-empty-text { color: rgba(255,255,255,0.5); font-size: $font-size-sm; }
.tm-quote-top { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 24rpx; }
.tm-quote-left { display: flex; flex-direction: column; gap: 4rpx; }
.tm-quote-name { font-size: 36rpx; font-weight: 700; color: #fff; }
.tm-quote-symbol { font-size: $font-size-xs; color: rgba(255,255,255,0.5); }
.tm-quote-right { text-align: right; }
.tm-quote-price { font-size: 48rpx; font-weight: 800; font-family: 'DIN Alternate',Arial,sans-serif; }
.tm-quote-price.up { color: $color-up; }
.tm-quote-price.down { color: $color-down; }
.tm-quote-change { font-size: $font-size-sm; font-weight: 600; margin-top: 4rpx; display: block; }
.tm-quote-change.up { color: $color-up; }
.tm-quote-change.down { color: $color-down; }
.tm-quote-detail { display: flex; gap: 0; }
.tm-qd-item { flex: 1; display: flex; flex-direction: column; align-items: center; gap: 4rpx; }
.tm-qd-label { font-size: 20rpx; color: rgba(255,255,255,0.5); }
.tm-qd-value { font-size: $font-size-sm; font-weight: 600; color: rgba(255,255,255,0.9); }
.tm-qd-value.up { color: $color-up; }
.tm-qd-value.down { color: $color-down; }

/* 方向切换 */
.tm-side-switch {
  display: flex; border-radius: 12rpx; overflow: hidden;
  margin-bottom: 20rpx; border: 2rpx solid $border-color;
}
.tm-side-btn {
  flex: 1; height: 80rpx; display: flex; align-items: center;
  justify-content: center; font-size: $font-size-base; font-weight: 700;
  color: $text-secondary; background: #fff;
  transition: all 0.15s;
  &.active { background: $color-up; color: #fff; border-color: $color-up; }
  &.sell.active { background: #2ED573; color: #fff; }
}

/* 价格 */
.tm-price-row { display: flex; flex-direction: column; gap: 12rpx; }
.tm-price-input {
  width: 100%; height: 80rpx; background: #fff; border: 2rpx solid $border-color;
  border-radius: 12rpx; padding: 0 20rpx; font-size: 36rpx; font-weight: 700;
  color: $text-primary; box-sizing: border-box;
}
.tm-price-refs { display: flex; gap: 12rpx; }
.tm-price-ref {
  padding: 8rpx 16rpx; background: #f0f2f5; border-radius: 8rpx;
  font-size: 22rpx; color: #4A90E2; cursor: pointer; flex-shrink: 0;
  &:active { opacity: 0.7; }
}

/* 数量 */
.tm-qty-input {
  width: 100%; height: 80rpx; background: #fff; border: 2rpx solid $border-color;
  border-radius: 12rpx; padding: 0 20rpx; font-size: 36rpx; font-weight: 700;
  color: $text-primary; box-sizing: border-box; margin-bottom: 12rpx;
}
.tm-qty-presets { display: flex; gap: 12rpx; margin-bottom: 8rpx; }
.tm-qty-chip {
  flex: 1; height: 64rpx; display: flex; align-items: center;
  justify-content: center; border-radius: 32rpx; font-size: $font-size-sm;
  font-weight: 600; color: $text-secondary; background: #f0f2f5; cursor: pointer;
  transition: all 0.15s;
  &.active { background: $color-primary; color: #fff; }
  &:active { opacity: 0.7; }
}
.tm-qty-hint { font-size: $font-size-xs; color: $text-hint; margin-top: 4rpx; }

/* 预估金额 */
.tm-estimate {
  display: flex; justify-content: space-between; align-items: center;
  padding: 16rpx 20rpx; background: #fff; border-radius: 12rpx;
}
.tm-estimate-label { font-size: $font-size-sm; color: $text-secondary; }
.tm-estimate-value { font-size: 36rpx; font-weight: 800; color: $color-primary; font-family: 'DIN Alternate',Arial,sans-serif; }

/* 交易按钮 */
.tm-action { margin-bottom: 20rpx; }
.tm-submit-btn {
  width: 100%; height: 96rpx; border-radius: 48rpx; font-size: 34rpx;
  font-weight: 700; color: #fff; border: none;
  transition: all 0.15s;
  &.buy { background: linear-gradient(135deg, #FF4757, #E74C3C); }
  &.sell { background: linear-gradient(135deg, #2ED573, #00B894); }
  &[disabled] { opacity: 0.4; }
  &::after { border: none; }
}

/* 最近订单 */
.tm-recent-header { display: flex; justify-content: space-between; align-items: center; }
.tm-view-all { font-size: $font-size-xs; color: #4A90E2; cursor: pointer; }
.tm-recent-order {
  padding: 16rpx 0; border-bottom: 1rpx solid #f0f0f0;
}
.tm-ro-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6rpx; }
.tm-ro-name { font-size: $font-size-sm; font-weight: 600; color: $text-primary; }
.tm-ro-status { font-size: 20rpx; padding: 2rpx 10rpx; border-radius: 6rpx; }
.tm-ro-status.pending { background: #FFF8E1; color: #E6A23C; }
.tm-ro-status.filled { background: #F0FFF0; color: #67C23A; }
.tm-ro-status.cancelled { background: #f5f5f5; color: #999; }
.tm-ro-status.rejected { background: #FFF0F0; color: #F56C6C; }
.tm-ro-meta { display: flex; justify-content: space-between; font-size: 20rpx; color: $text-hint; }
.tm-ro-time { color: $text-hint; }

/* Analytics Board */
.analytics-board { padding: 0 24rpx; }
.analytics-board-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16rpx; }
.analytics-board-title { font-size: $font-size-base; font-weight: 600; color: $text-primary; }
.analytics-link { font-size: $font-size-sm; color: #4A90E2; }
.analytics-card {
  background: $bg-card; border-radius: $border-radius-lg; padding: 28rpx; margin-bottom: 16rpx;
}
.analytics-card-title { font-size: $font-size-sm; font-weight: 600; color: $text-primary; display: block; margin-bottom: 16rpx; }
.overview-main { display: flex; align-items: baseline; gap: 12rpx; margin-bottom: 20rpx; }
.overview-pnl { font-size: 48rpx; font-weight: 800; font-family: 'DIN Alternate','Helvetica Neue',Arial,sans-serif; }
.overview-pnl-pct { font-size: $font-size-lg; font-weight: 600; }
.overview-sub { display: flex; gap: 32rpx; }
.overview-sub-item { display: flex; flex-wrap: wrap; align-items: baseline; gap: 6rpx; }
.sub-label { font-size: $font-size-xs; color: $text-hint; }
.sub-value { font-size: $font-size-base; font-weight: 600; color: $text-primary; }
.sub-pct { font-size: $font-size-xs; }
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
  background: $bg-page; border-radius: $border-radius; padding: 16rpx; cursor: pointer;
  &:active { opacity: 0.8; }
}
.bw-label { font-size: $font-size-xs; color: $text-hint; width: 56rpx; }
.bw-name { flex: 1; font-size: $font-size-sm; color: $text-primary; }
.bw-pnl { font-size: $font-size-base; font-weight: 600; }
.bw-arrow { font-size: $font-size-sm; color: $text-hint; }
.empty-analytics { text-align: center; padding: 32rpx 0; font-size: $font-size-sm; color: $text-hint; }
.sector-list { display: flex; flex-direction: column; gap: 16rpx; }
.sector-header { display: flex; align-items: center; gap: 8rpx; margin-bottom: 8rpx; }
.sector-dot { width: 16rpx; height: 16rpx; border-radius: 50%; flex-shrink: 0; }
.sector-name { font-size: $font-size-sm; color: $text-primary; flex: 1; }
.sector-cnt { font-size: $font-size-xs; color: $text-hint; }
.sector-weight { font-size: $font-size-sm; font-weight: 600; color: $text-primary; width: 80rpx; text-align: right; }
.sector-bar-wrap { height: 12rpx; background: $bg-page; border-radius: 6rpx; overflow: hidden; }
.sector-bar { height: 100%; border-radius: 6rpx; min-width: 4rpx; transition: width 0.5s ease; }

/* AI托管 */
.hosted-section { background: $bg-card; margin: 16rpx 24rpx; border-radius: $border-radius-lg; padding: 28rpx; }
.hosted-mode-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24rpx; }
.hosted-label { font-size: $font-size-base; font-weight: 600; color: $text-primary; }
.hosted-toggle { font-size: $font-size-xs; padding: 6rpx 20rpx; border-radius: 20rpx; background: #f0f0f0; color: $text-hint; }
.hosted-toggle.active { background: rgba(74, 144, 226, 0.12); color: #4A90E2; }
.hosted-stats-grid { display: flex; gap: 16rpx; margin-bottom: 24rpx; }
.hosted-stat-item { flex: 1; text-align: center; display: flex; flex-direction: column; gap: 6rpx; padding: 16rpx 0; background: $bg-page; border-radius: $border-radius; }
.hosted-stat-num { font-size: $font-size-xl; font-weight: 700; color: $text-primary; }
.hosted-stat-label { font-size: $font-size-xs; color: $text-hint; }
.hosted-link { display: flex; justify-content: space-between; align-items: center; color: #4A90E2; font-size: $font-size-sm; font-weight: 500; padding: 12rpx 0 0; border-top: 1rpx solid $border-color; }
.hosted-arrow { font-size: $font-size-sm; }
.loading-state { display: flex; align-items: center; justify-content: center; padding: 120rpx 0; font-size: 28rpx; color: $text-hint; }
.btn-retry { margin-top: 24rpx; background: $color-primary; color: #fff; border-radius: 12rpx; font-size: 26rpx; padding: 12rpx 48rpx; }
/* Order & Trade Cards */
.order-card, .trade-card { background: $bg-card; margin: 8rpx 24rpx; border-radius: $border-radius; padding: 20rpx 24rpx; }
.order-top, .trade-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8rpx; }
.order-name, .trade-name { font-size: $font-size-base; font-weight: 600; color: $text-primary; }
.order-status { font-size: 20rpx; padding: 2rpx 10rpx; border-radius: 6rpx; font-weight: 500; }
.order-status.pending { background: #FFF8E1; color: #E6A23C; }
.order-status.filled { background: #F0FFF0; color: #67C23A; }
.order-status.cancelled { background: #f5f5f5; color: #999; }
.order-status.rejected { background: #FFF0F0; color: #F56C6C; }
.order-meta, .trade-meta { display: flex; justify-content: space-between; align-items: center; font-size: $font-size-xs; color: $text-hint; }
.trade-source { margin-top: 8rpx; display: flex; align-items: center; }
.src-tag { display: inline-flex; align-items: center; padding: 2rpx 14rpx; border-radius: 8rpx; font-size: 20rpx; line-height: 1.6; }
.src-agent { background: var(--color-primary, #4A90E2); color: #FFFFFF; }
.src-user { background: rgba(153, 153, 153, 0.15); color: var(--text-hint, #999999); }
.order-time, .trade-time { color: $text-hint; }
.trade-top .up { color: $color-up; }
.trade-top .down { color: $color-down; }


/* --- 分页加载更多 --- */
.load-more-bar {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 24rpx 0;
}
.load-more-text {
  font-size: 26rpx;
  color: var(--color-primary, #4A90E2);
}
</style>