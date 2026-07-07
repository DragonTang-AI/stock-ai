<template>
  <view class="detail-page">
    <!-- 加载中 -->
    <view v-if="loading" class="state-view">
      <text class="state-text">加载中...</text>
    </view>

    <!-- 错误 -->
    <view v-else-if="error" class="state-view">
      <text class="state-text error">{{ error }}</text>
      <button class="btn-retry" @click="loadData">重试</button>
    </view>

    <!-- 详情内容 -->
    <template v-else-if="detail">
      <!-- ====== 股票基本信息头部 ====== -->
      <view class="stock-header">
        <view class="header-top">
          <view class="name-row">
            <text class="stock-name">{{ detail.name }}</text>
            <text class="stock-symbol">{{ detail.symbol }}</text>
            <text class="market-tag">{{ marketLabel(detail.market) }}</text>
          </view>
          <view class="action-badge" :class="actionClass">
            {{ actionLabel }}
          </view>
        </view>

        <view class="price-row">
          <text class="current-price">{{ formatPrice(detail.current_price) }}</text>
          <view class="change-info" :class="changeClass">
            <text class="change-value">{{ formatChange(detail.change) }}</text>
            <text class="change-pct">{{ formatChangePct(detail.change_pct) }}</text>
          </view>
        </view>

        <!-- 综合置信度 -->
        <view class="confidence-bar">
          <view class="confidence-track">
            <view
              class="confidence-fill"
              :style="{ width: detail.confidence + '%' }"
              :class="confidenceColorClass"
            />
          </view>
          <text class="confidence-num">{{ detail.confidence }}%</text>
        </view>
      </view>

      <!-- ====== 价格锚点（目标/止损/止盈） ====== -->
      <view v-if="hasPriceTargets" class="price-targets">
        <view class="target-card up">
          <text class="target-label">止盈价</text>
          <text class="target-value">{{ formatPrice(detail.take_profit!) }}</text>
        </view>
        <view class="target-card neutral">
          <text class="target-label">目标价</text>
          <text class="target-value">{{ formatPrice(detail.target_price!) }}</text>
        </view>
        <view class="target-card down">
          <text class="target-label">止损价</text>
          <text class="target-value">{{ formatPrice(detail.stop_loss!) }}</text>
        </view>
      </view>

      <!-- ====== 综合推荐理由 ====== -->
      <view class="reason-section">
        <view class="section-header">
          <text class="section-title">推荐理由</text>
        </view>
        <view class="reason-tags">
          <text
            v-for="code in detail.reason_codes"
            :key="code"
            class="reason-tag"
            :class="reasonTagClass(code)"
          >{{ reasonCodeLabel(code) }}</text>
        </view>
        <text class="reason-text">{{ detail.reasoning }}</text>
      </view>

      <!-- ====== 4-Agent 评分面板 ====== -->
      <view class="agents-section">
        <view class="section-header">
          <text class="section-title">分 Agent 评分</text>
        </view>

        <view
          v-for="agent in detail.agents"
          :key="agent.agent"
          class="agent-card"
        >
          <view class="agent-head">
            <view class="agent-info">
              <text class="agent-name">{{ agentLabel(agent.agent) }}</text>
              <view class="agent-scores">
                <text class="agent-score">{{ agent.score }}分</text>
                <text class="agent-confidence">{{ agent.confidence }}% 置信</text>
              </view>
            </view>
            <view class="score-bar">
              <view
                class="score-fill"
                :style="{ width: agent.score + '%' }"
                :class="scoreColorClass(agent.score)"
              />
            </view>
          </view>

          <!-- Agent 级 reason_codes -->
          <view v-if="agent.reason_codes.length" class="agent-tags">
            <text
              v-for="code in agent.reason_codes"
              :key="code"
              class="agent-tag"
              :class="reasonTagClass(code)"
            >{{ reasonCodeLabel(code) }}</text>
          </view>

          <text class="agent-reasoning">{{ agent.reasoning }}</text>
        </view>
      </view>

      <!-- ====== 操作按钮 ====== -->
      <view class="action-bar">
        <button
          class="btn-watchlist"
          :class="{ active: isWatchlisted }"
          @click="handleToggleWatch"
        >
          {{ isWatchlisted ? '已加入自选' : '加入自选' }}
        </button>
      </view>

      <!-- 生成时间 -->
      <view v-if="detail.generated_at" class="footer">
        <text class="footer-text">分析生成于 {{ detail.generated_at }}</text>
      </view>
      <Disclaimer />
</template>
  </view>
  <Disclaimer />
</template>

<script setup lang="ts">
import Disclaimer from '@/components/compliance/Disclaimer.vue'
import { ref, computed, onMounted } from 'vue'
import {
  fetchStockDetail,
  addToWatchlist,
  removeFromWatchlist,
  type StockAnalysisDetail,
} from '@/api/selection'

// ---- 状态 ----
const detail = ref<StockAnalysisDetail | null>(null)
const loading = ref(true)
const error = ref('')
const isWatchlisted = ref(false)

// ---- 计算属性 ----
const actionLabel = computed(() => {
  const map: Record<string, string> = {
    BUY: '买入',
    ADD: '加仓',
    HOLD: '观望',
    REDUCE: '减仓',
    SELL: '卖出',
  }
  return map[detail.value?.action || ''] || detail.value?.action || '--'
})

const actionClass = computed(() => {
  const action = detail.value?.action || ''
  if (action === 'BUY' || action === 'ADD') return 'bullish'
  if (action === 'SELL' || action === 'REDUCE') return 'bearish'
  return 'neutral'
})

const changeClass = computed(() => {
  if (!detail.value) return ''
  return detail.value.change >= 0 ? 'up' : 'down'
})

const confidenceColorClass = computed(() => {
  const c = detail.value?.confidence || 0
  if (c >= 70) return 'high'
  if (c >= 40) return 'mid'
  return 'low'
})

const hasPriceTargets = computed(() => {
  const d = detail.value
  return d && (d.target_price != null || d.stop_loss != null || d.take_profit != null)
})

// ---- 生命周期 ----
onMounted(() => {
  const pages = getCurrentPages()
  const currentPage = pages[pages.length - 1] as any
  const query = currentPage?.$page?.options || currentPage?.options || {}
  const symbol = query.symbol || ''

  if (symbol) {
    loadData(decodeURIComponent(symbol))
  } else {
    error.value = '缺少股票代码参数'
    loading.value = false
  }
})

// ---- 数据加载 ----
async function loadData(symbol?: string) {
  const s = symbol || detail.value?.symbol
  if (!s) {
    error.value = '缺少股票代码'
    loading.value = false
    return
  }

  loading.value = true
  error.value = ''
  try {
    detail.value = await fetchStockDetail(s)
  } catch (e: any) {
    error.value = e?.message || '加载失败'
  } finally {
    loading.value = false
  }
}

async function handleToggleWatch() {
  if (!detail.value) return
  const symbol = detail.value.symbol
  try {
    if (isWatchlisted.value) {
      await removeFromWatchlist(symbol)
      isWatchlisted.value = false
      uni.showToast({ title: '已取消关注', icon: 'success' })
    } else {
      await addToWatchlist(symbol)
      isWatchlisted.value = true
      uni.showToast({ title: '已加入自选', icon: 'success' })
    }
  } catch {
    uni.showToast({ title: '操作失败', icon: 'none' })
  }
}

// ---- 标签映射 ----
function marketLabel(market: string): string {
  const map: Record<string, string> = { A: 'A股', HK: '港股', US: '美股' }
  return map[market] || market
}

function agentLabel(agent: string): string {
  const map: Record<string, string> = {
    Technical: '技术面 Agent',
    Fundamental: '基本面 Agent',
    Sentiment: '舆情面 Agent',
    Risk: '风控 Agent',
    technical: '技术面 Agent',
    fundamental: '基本面 Agent',
    sentiment: '舆情面 Agent',
    risk: '风控 Agent',
  }
  return map[agent] || agent
}

/** reason_code → 中文标签（对齐 signal.schema.json 枚举） */
function reasonCodeLabel(code: string): string {
  const map: Record<string, string> = {
    // 技术面
    TECH_MA_GOLDEN: '均线金叉',
    TECH_MA_DEAD: '均线死叉',
    TECH_RSI_OVERSOLD: 'RSI超卖',
    TECH_RSI_OVERBOUGHT: 'RSI超买',
    TECH_MACD_DIVERGE: 'MACD背离',
    TECH_BOLL_BREAK: '布林突破',
    TECH_VOLUME_SPIKE: '放量',
    TECH_TREND_UP: '趋势上行',
    TECH_TREND_DOWN: '趋势下行',
    // 基本面
    FUND_PE_LOW: '低PE',
    FUND_PE_HIGH: '高PE',
    FUND_PB_LOW: '低PB',
    FUND_PROFIT_GROW: '利润增长',
    FUND_ROE_HIGH: '高ROE',
    FUND_DEBT_LOW: '低负债',
    FUND_CASH_RICH: '现金充裕',
    FUND_DIVIDEND_HIGH: '高股息',
    // 舆情面
    SENT_POSITIVE: '舆情正面',
    SENT_NEGATIVE: '舆情负面',
    SENT_NEWS_HOT: '热点新闻',
    SENT_INST_BUY: '机构买入',
    SENT_RESEARCH_BULLISH: '研报看多',
    SENT_BANNER_PULL: '利好公告',
    SENT_BANNER_BAD: '利空公告',
    // 风控
    RISK_STOP_LOSS: '止损触发',
    RISK_TAKE_PROFIT: '止盈触发',
    RISK_POSITION_LIMIT: '仓位上限',
    RISK_LOSS_LIMIT: '亏损上限',
  }
  return map[code] || code
}

function reasonTagClass(code: string): string {
  if (code.startsWith('TECH_')) return 'tag-tech'
  if (code.startsWith('FUND_')) return 'tag-fund'
  if (code.startsWith('SENT_')) return 'tag-sent'
  if (code.startsWith('RISK_')) return 'tag-risk'
  return ''
}

function scoreColorClass(score: number): string {
  if (score >= 70) return 'high'
  if (score >= 40) return 'mid'
  return 'low'
}

// ---- 格式化 ----
function formatPrice(v: number | undefined): string {
  if (v == null) return '--'
  return v.toFixed(2)
}

function formatChange(v: number): string {
  if (v == null) return '--'
  const sign = v >= 0 ? '+' : ''
  return sign + v.toFixed(2)
}

function formatChangePct(v: number): string {
  if (v == null) return '--'
  const sign = v >= 0 ? '+' : ''
  return sign + v.toFixed(2) + '%'
}
</script>

<style lang="scss" scoped>
.detail-page {
  min-height: 100vh;
  background: $bg-page;
  padding-bottom: env(safe-area-inset-bottom);
}

// ---- 状态视图 ----
.state-view {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 200rpx 0;
  gap: 16rpx;
}

.state-text {
  font-size: $font-size-base;
  color: $text-hint;

  &.error { color: $color-danger; }
}

.btn-retry {
  margin-top: 24rpx;
  padding: 12rpx 48rpx;
  font-size: $font-size-sm;
  color: $color-primary;
  background: rgba(74, 144, 226, 0.1);
  border-radius: 8rpx;
  border: none;
  &::after { border: none; }
}

// ====== 股票头部 ======
.stock-header {
  background: $bg-card;
  padding: 24rpx 32rpx 20rpx;
}

.header-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16rpx;
}

.name-row {
  display: flex;
  align-items: baseline;
  gap: 12rpx;
  flex-wrap: wrap;
}

.stock-name {
  font-size: $font-size-xl;
  font-weight: 700;
  color: $text-primary;
}

.stock-symbol {
  font-size: $font-size-sm;
  color: $text-hint;
}

.market-tag {
  font-size: 20rpx;
  padding: 2rpx 10rpx;
  border-radius: 4rpx;
  background: rgba(74, 144, 226, 0.08);
  color: $color-primary;
}

.action-badge {
  padding: 6rpx 20rpx;
  border-radius: 8rpx;
  font-size: $font-size-sm;
  font-weight: 700;
  flex-shrink: 0;

  &.bullish {
    background: rgba(239, 83, 80, 0.1);
    color: #EF5350;
  }
  &.bearish {
    background: rgba(38, 166, 154, 0.1);
    color: #26A69A;
  }
  &.neutral {
    background: rgba(153, 153, 153, 0.1);
    color: #999;
  }
}

.price-row {
  display: flex;
  align-items: baseline;
  gap: 16rpx;
  margin-bottom: 20rpx;
}

.current-price {
  font-size: 56rpx;
  font-weight: 700;
  color: $text-primary;
  line-height: 1;
}

.change-info {
  display: flex;
  gap: 8rpx;
  padding: 4rpx 12rpx;
  border-radius: 6rpx;

  &.up {
    background: rgba(239, 83, 80, 0.1);
    color: #EF5350;
  }
  &.down {
    background: rgba(38, 166, 154, 0.1);
    color: #26A69A;
  }
}

.change-value,
.change-pct {
  font-size: $font-size-base;
  font-weight: 600;
}

// ---- 综合置信度条 ----
.confidence-bar {
  display: flex;
  align-items: center;
  gap: 16rpx;
}

.confidence-track {
  flex: 1;
  height: 10rpx;
  background: rgba(0, 0, 0, 0.06);
  border-radius: 5rpx;
  overflow: hidden;
}

.confidence-fill {
  height: 100%;
  border-radius: 5rpx;
  transition: width 0.6s ease;

  &.high { background: linear-gradient(90deg, #EF5350, #FF7043); }
  &.mid  { background: linear-gradient(90deg, #FFA726, #FFCA28); }
  &.low  { background: linear-gradient(90deg, #26A69A, #66BB6A); }
}

.confidence-num {
  font-size: $font-size-base;
  font-weight: 700;
  color: $color-primary;
  min-width: 64rpx;
  text-align: right;
}

// ====== 价格锚点 ======
.price-targets {
  display: flex;
  gap: 12rpx;
  padding: 16rpx 32rpx;
  margin-top: 16rpx;
  background: $bg-card;
}

.target-card {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6rpx;
  padding: 16rpx 0;
  border-radius: 8rpx;

  &.up     { background: rgba(239, 83, 80, 0.06); }
  &.neutral { background: rgba(74, 144, 226, 0.06); }
  &.down   { background: rgba(38, 166, 154, 0.06); }
}

.target-label {
  font-size: 20rpx;
  color: $text-hint;
}

.target-value {
  font-size: $font-size-base;
  font-weight: 700;
  color: $text-primary;
}

// ====== 推荐理由区域 ======
.reason-section {
  margin: 16rpx 24rpx 0;
  background: $bg-card;
  border-radius: $border-radius;
  padding: 24rpx 28rpx;
}

.section-header {
  margin-bottom: 16rpx;
}

.section-title {
  font-size: $font-size-base;
  font-weight: 700;
  color: $text-primary;
}

.reason-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 10rpx;
  margin-bottom: 16rpx;
}

.reason-tag {
  font-size: 20rpx;
  padding: 4rpx 14rpx;
  border-radius: 4rpx;
  font-weight: 500;

  &.tag-tech { background: rgba(33, 150, 243, 0.1);  color: #2196F3; }
  &.tag-fund { background: rgba(76, 175, 80, 0.1);  color: #4CAF50; }
  &.tag-sent { background: rgba(255, 152, 0, 0.1);  color: #FF9800; }
  &.tag-risk { background: rgba(156, 39, 176, 0.1); color: #9C27B0; }
}

.reason-text {
  font-size: $font-size-sm;
  color: $text-secondary;
  line-height: 1.7;
}

// ====== 4-Agent 评分 ======
.agents-section {
  margin: 16rpx 24rpx 0;
  background: $bg-card;
  border-radius: $border-radius;
  padding: 24rpx 28rpx;
}

.agent-card {
  padding: 20rpx 0;
  border-bottom: 1rpx solid $border-color;

  &:last-child {
    border-bottom: none;
    padding-bottom: 0;
  }
}

.agent-head {
  margin-bottom: 12rpx;
}

.agent-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10rpx;
}

.agent-name {
  font-size: $font-size-sm;
  font-weight: 600;
  color: $text-primary;
}

.agent-scores {
  display: flex;
  gap: 8rpx;
  align-items: baseline;
}

.agent-score {
  font-size: $font-size-sm;
  font-weight: 700;
  color: $color-primary;
}

.agent-confidence {
  font-size: 20rpx;
  color: $text-hint;
}

.score-bar {
  height: 8rpx;
  background: rgba(0, 0, 0, 0.06);
  border-radius: 4rpx;
  overflow: hidden;
}

.score-fill {
  height: 100%;
  border-radius: 4rpx;
  transition: width 0.5s ease;

  &.high { background: linear-gradient(90deg, #4CAF50, #66BB6A); }
  &.mid  { background: linear-gradient(90deg, #FFA726, #FFCA28); }
  &.low  { background: linear-gradient(90deg, #EF5350, #FF7043); }
}

.agent-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8rpx;
  margin-bottom: 10rpx;
}

.agent-tag {
  font-size: 18rpx;
  padding: 2rpx 10rpx;
  border-radius: 4rpx;

  &.tag-tech { background: rgba(33, 150, 243, 0.08);  color: #2196F3; }
  &.tag-fund { background: rgba(76, 175, 80, 0.08);  color: #4CAF50; }
  &.tag-sent { background: rgba(255, 152, 0, 0.08);  color: #FF9800; }
  &.tag-risk { background: rgba(156, 39, 176, 0.08); color: #9C27B0; }
}

.agent-reasoning {
  font-size: $font-size-sm;
  color: $text-secondary;
  line-height: 1.6;
}

// ====== 操作栏 ======
.action-bar {
  padding: 32rpx 24rpx;
}

.btn-watchlist {
  width: 100%;
  padding: 24rpx;
  font-size: $font-size-base;
  color: $color-primary;
  background: rgba(74, 144, 226, 0.08);
  border: 1rpx solid rgba(74, 144, 226, 0.25);
  border-radius: 12rpx;
  text-align: center;

  &::after { border: none; }

  &.active {
    color: $text-hint;
    background: rgba(0, 0, 0, 0.04);
    border-color: $border-color;
  }
}

// ====== 页脚 ======
.footer {
  display: flex;
  justify-content: center;
  padding: 16rpx 24rpx 32rpx;
}

.footer-text {
  font-size: 20rpx;
  color: $text-hint;
  opacity: 0.6;
}
</style>
