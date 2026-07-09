<template>
  <view class="advisor-page">
    <!-- ===== 诊断面板（保留原有） ===== -->
    <!-- 大盘温度条 -->
    <view class="temperature-bar" :class="'temp-' + tempLevel" v-if="diagnosis?.market_temperature">
      <view class="temp-left">
        <text class="temp-emoji">{{ diagnosis.market_temperature.emoji }}</text>
        <text class="temp-text">{{ diagnosis.market_temperature.temperature_text }}</text>
        <text class="temp-value" :class="diagnosis.market_temperature.avg_change_pct >= 0 ? 'up' : 'down'">
          {{ diagnosis.market_temperature.avg_change_pct >= 0 ? '+' : '' }}{{ diagnosis.market_temperature.avg_change_pct.toFixed(2) }}%
        </text>
      </view>
      <view class="temp-indices" v-if="diagnosis.market_temperature.indices.length">
        <text v-for="idx in diagnosis.market_temperature.indices" :key="idx.name" class="temp-idx">
          {{ idx.name }} {{ idx.price.toFixed(0) }}
          <text :class="idx.change_pct >= 0 ? 'up' : 'down'">{{ idx.change_pct >= 0 ? '+' : '' }}{{ idx.change_pct.toFixed(2) }}%</text>
        </text>
      </view>
    </view>

    <!-- 空仓 -->
    <view v-if="!diagnosis" class="empty-state">
      <text class="empty-icon">&#x1F916;</text>
      <text class="empty-text">加载中...</text>
    </view>
    <view v-else-if="diagnosis.summary.position_count === 0" class="empty-state">
      <text class="empty-icon">&#x1F4ED;</text>
      <text class="empty-text">还没有持仓</text>
      <text class="empty-sub" @click="navigateTo('/pages/selection/index')">先去选股看看吧&#x1F449;</text>
    </view>

    <!-- 诊断内容 -->
    <template v-if="diagnosis && diagnosis.summary.position_count > 0">
      <!-- 持仓诊断概览 -->
      <view class="card summary-card">
        <view class="card-header">
          <text class="card-icon">&#x1F4BC;</text>
          <text class="card-title">持仓诊断</text>
        </view>
        <view class="summary-main">
          <view class="summary-row">
            <text class="summary-label">总资产</text>
            <text class="summary-value">{{ formatMoney(diagnosis.summary.total_equity) }}</text>
            <text class="summary-pnl" :class="diagnosis.summary.total_profit >= 0 ? 'up' : 'down'">
              {{ diagnosis.summary.total_profit >= 0 ? '+' : '' }}{{ diagnosis.summary.total_profit_pct.toFixed(2) }}%
            </text>
          </view>
          <view class="summary-tags">
            <text class="tag">持仓 {{ diagnosis.summary.position_count }}只</text>
            <text class="tag">胜率 {{ diagnosis.summary.win_rate.toFixed(0) }}%</text>
            <text class="tag">现金 {{ diagnosis.summary.cash_ratio.toFixed(0) }}%</text>
          </view>
        </view>

        <view class="position-list">
          <view
            class="position-card"
            v-for="pos in diagnosis.positions" :key="pos.symbol"
            :class="'rating-' + pos.rating"
            @click="goDetail(pos.symbol)"
          >
            <view class="pos-top">
              <text class="pos-name">{{ pos.name }}</text>
              <text class="pos-pnl" :class="pos.profit_pct >= 0 ? 'up' : 'down'">
                {{ pos.profit_pct >= 0 ? '+' : '' }}{{ pos.profit_pct.toFixed(2) }}%
              </text>
              <view class="rating-tag" :class="pos.rating">
                <text class="rating-icon">{{ ratingIcons[pos.rating] }}</text>
                <text class="rating-text">{{ pos.rating_text }}</text>
              </view>
            </view>
            <view class="pos-signals" v-if="pos.signals.length">
              <view class="signal-item" v-for="sig in pos.signals" :key="sig.name">
                <text class="signal-icon">{{ signalIcons[sig.type] || '&#x2139;&#xFE0F;' }}</text>
                <text class="signal-text">{{ sig.name }}</text>
              </view>
            </view>
            <view class="pos-action" v-if="pos.action?.text">
              <text class="action-text">{{ pos.action.text }}</text>
            </view>
          </view>
        </view>
      </view>

      <!-- 风险提醒 -->
      <view class="card" v-if="diagnosis.risks.length">
        <view class="card-header">
          <text class="card-icon">&#x26A0;&#xFE0F;</text>
          <text class="card-title">风险提醒</text>
        </view>
        <view class="risk-list">
          <view class="risk-item" v-for="(risk, idx) in diagnosis.risks" :key="idx">
            <text class="risk-icon">{{ riskIcons[risk.level] }}</text>
            <view class="risk-body">
              <text class="risk-title">{{ risk.title }}</text>
              <text class="risk-desc" v-if="risk.desc">{{ risk.desc }}</text>
            </view>
          </view>
        </view>
      </view>

      <!-- 操作建议 -->
      <view class="card" v-if="diagnosis.suggestions.length">
        <view class="card-header">
          <text class="card-icon">&#x1F4CB;</text>
          <text class="card-title">操作建议</text>
        </view>
        <view class="suggestion-list">
          <view class="suggestion-item" v-for="(sg, idx) in diagnosis.suggestions" :key="idx">
            <text class="sg-priority" :class="'p-' + sg.priority">[{{ priorityLabel[sg.priority] }}]</text>
            <text class="sg-text">{{ sg.text }}</text>
          </view>
        </view>
      </view>
    </template>

    <!-- 免责声明 -->
    <view class="disclaimer" v-if="diagnosis?.disclaimer">
      <text>{{ diagnosis.disclaimer }}</text>
    </view>

    <!-- Agent 悬浮球 -->
    <view class="agent-fab" @click="showChat = true">
      <text class="fab-icon">&#x1F916;</text>
    </view>

    <!-- ===== 对话弹窗（点击入口后弹出） ===== -->
    <view class="chat-overlay" v-if="showChat">
      <view class="chat-popup">
        <!-- 弹窗头部 -->
        <view class="chat-popup-header">
          <text class="popup-back" @click="showChat = false">&#x2715;</text>
          <text class="popup-title">AI 投资助手</text>
          <view class="model-switch">
            <view
              class="model-opt" :class="{ active: chatModel === 'deepseek-v4-flash' }"
              @click="chatModel = 'deepseek-v4-flash'"
            >&#x26A1; 快速</view>
            <view
              class="model-opt" :class="{ active: chatModel === 'deepseek-v4-pro' }"
              @click="chatModel = 'deepseek-v4-pro'"
            >&#x1F9E0; 深度</view>
          </view>
        </view>

        <!-- 对话列表 -->
        <scroll-view class="chat-list" scroll-y :scroll-into-view="scrollToId" :scroll-with-animation="true">
          <view v-if="messages.length === 0" class="chat-welcome">
            <text class="welcome-icon">&#x1F916;</text>
            <text class="welcome-text">有什么可以帮你的？</text>
            <view class="quick-qs">
              <view class="quick-q" v-for="q in quickQuestions" :key="q" @click="askQuick(q)">{{ q }}</view>
            </view>
          </view>
          <view v-for="msg in messages" :key="msg.id" :id="'msg-' + msg.id" class="msg-row" :class="msg.role">
            <view class="msg-bubble" :class="msg.role === 'user' ? 'bubble-user' : 'bubble-ai'">
              <text class="msg-text">{{ msg.content }}</text>
              <text v-if="msg.role === 'ai' && msg.id === streamingId" class="cursor-blink">|</text>
            </view>
          </view>
        </scroll-view>

        <!-- 弹窗底部输入 -->
        <view class="chat-input-bar">
          <input
            class="chat-msg-input"
            v-model="inputText"
            placeholder="输入投资问题..."
            confirm-type="send"
            :disabled="streaming"
            @confirm="sendMessage"
          />
          <button class="chat-send-btn" @click="sendMessage" :disabled="!inputText.trim() || streaming">
            {{ streaming ? '...' : '发送' }}
          </button>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, nextTick, onMounted } from 'vue'
import { onShow, onPullDownRefresh } from '@dcloudio/uni-app'
import { getDiagnosis, chatStream, type DiagnosisData } from '@/api/advisor'

// ===== 诊断面板 =====
const diagnosis = ref<DiagnosisData | null>(null)
const tempLevel = ref('neutral')

const ratingIcons: Record<string, string> = { healthy: '\u2705', neutral: '\u26AA', caution: '\u26A0\uFE0F', risk: '\u{1F534}' }
const signalIcons: Record<string, string> = { bullish: '\u{1F4C8}', bearish: '\u{1F4C9}', warning: '\u26A0\uFE0F', info: '\u2139\uFE0F' }
const riskIcons: Record<string, string> = { high: '\u{1F534}', medium: '\u{1F7E1}', low: '\u{1F535}', info: '\u2139\uFE0F' }
const priorityLabel: Record<string, string> = { high: '高', medium: '中', low: '低' }

function getTempLevel(t: string): string {
  if (t.includes('热') || t.includes('hot')) return 'hot'
  if (t.includes('暖') || t.includes('warm')) return 'warm'
  if (t.includes('冷') || t.includes('cold')) return 'cold'
  if (t.includes('凉') || t.includes('cool')) return 'cool'
  return 'neutral'
}

function formatMoney(v: number): string {
  if (v == null || isNaN(v)) return '0.00'
  return v.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function navigateTo(url: string) { uni.navigateTo({ url }) }
function goDetail(symbol: string) { uni.navigateTo({ url: '/pages/detail/index?symbol=' + symbol }) }

async function loadDiagnosis() {
  try {
    const data = await getDiagnosis()
    diagnosis.value = data
    if (data.market_temperature?.temperature_text) {
      tempLevel.value = getTempLevel(data.market_temperature.temperature_text)
    }
  } catch { /* no-op */ }
}

// ===== 对话弹窗 =====
const showChat = ref(false)
const inputText = ref('')
const chatModel = ref('deepseek-v4-flash')
const streaming = ref(false)
const streamingId = ref(0)
const scrollToId = ref('')

interface Message { id: number; role: 'user' | 'ai'; content: string }
const messages = ref<Message[]>([])
let msgSeq = 0

const quickQuestions = [
  '我的持仓怎么样？',
  '大盘今天什么情况？',
  '茅台现在适合买入吗？',
]

function scrollToBottom() {
  nextTick(() => {
    scrollToId.value = 'msg-' + msgSeq
    nextTick(() => { scrollToId.value = '' })
  })
}

async function sendMessage() {
  const text = inputText.value.trim()
  if (!text || streaming.value) return
  inputText.value = ''

  msgSeq++
  messages.value.push({ id: msgSeq, role: 'user', content: text })
  scrollToBottom()

  msgSeq++
  const aiId = msgSeq
  messages.value.push({ id: aiId, role: 'ai', content: '' })
  streamingId.value = aiId
  streaming.value = true
  scrollToBottom()

  chatStream(
    text, chatModel.value,
    (token) => {
      const m = messages.value.find(x => x.id === aiId)
      if (m) m.content += token
      scrollToBottom()
    },
    () => { streaming.value = false; streamingId.value = 0 },
    (err) => {
      const m = messages.value.find(x => x.id === aiId)
      if (m) m.content = err
      streaming.value = false; streamingId.value = 0
    }
  )
}

function askQuick(q: string) { inputText.value = q; sendMessage() }

onMounted(() => { loadDiagnosis() })
onShow(() => { loadDiagnosis() })

onPullDownRefresh(async () => {
  await loadDiagnosis()
  uni.stopPullDownRefresh()
})
</script>

<style lang="scss" scoped>
.advisor-page { min-height: 100vh; background: $bg-page; padding-bottom: calc(120rpx + env(safe-area-inset-bottom)); }

/* ===== 诊断面板样式（保留原有） ===== */
.temperature-bar {
  padding: 20rpx 32rpx; color: #fff;
  &.temp-hot { background: linear-gradient(135deg, #DC2626 0%, #EF4444 100%); }
  &.temp-warm { background: linear-gradient(135deg, #EA580C 0%, #F97316 100%); }
  &.temp-neutral { background: linear-gradient(135deg, #6B7280 0%, #9CA3AF 100%); }
  &.temp-cool { background: linear-gradient(135deg, #2563EB 0%, #60A5FA 100%); }
  &.temp-cold { background: linear-gradient(135deg, #1E3A5F 0%, #1E40AF 100%); }
}
.temp-left { display: flex; align-items: baseline; gap: 8rpx; margin-bottom: 4rpx; }
.temp-emoji { font-size: 36rpx; }
.temp-text { font-size: $font-size-base; font-weight: 600; }
.temp-value { font-size: $font-size-base; font-weight: 700; }
.temp-indices { display: flex; flex-wrap: wrap; gap: 16rpx; margin-top: 4rpx; }
.temp-idx { font-size: $font-size-xs; opacity: 0.9; }

.card { margin: 16rpx 24rpx; background: $bg-card; border-radius: $border-radius-lg; padding: 24rpx; }
.card-header { display: flex; align-items: center; gap: 8rpx; margin-bottom: 16rpx; }
.card-icon { font-size: 28rpx; }
.card-title { font-size: $font-size-base; font-weight: 700; color: $text-primary; }

.summary-main { margin-bottom: 16rpx; }
.summary-row { display: flex; align-items: baseline; gap: 12rpx; margin-bottom: 12rpx; }
.summary-label { font-size: $font-size-xs; color: $text-hint; }
.summary-value { font-size: 56rpx; font-weight: 800; color: $text-primary; font-family: 'DIN Alternate','Helvetica Neue',Arial,sans-serif; }
.summary-pnl { font-size: $font-size-lg; font-weight: 600; }
.summary-tags { display: flex; gap: 12rpx; }
.tag { font-size: $font-size-xs; padding: 4rpx 16rpx; border-radius: 20rpx; background: $bg-page; color: $text-secondary; }

.position-list { display: flex; flex-direction: column; gap: 12rpx; }
.position-card { border-radius: $border-radius; padding: 20rpx; border-left: 6rpx solid $border-color; cursor: pointer;
  &:active { opacity: 0.85; }
  &.rating-healthy { border-left-color: #22C55E; }
  &.rating-neutral { border-left-color: #9CA3AF; }
  &.rating-caution { border-left-color: #F59E0B; }
  &.rating-risk { border-left-color: #EF4444; }
}
.pos-top { display: flex; align-items: center; gap: 12rpx; margin-bottom: 8rpx; }
.pos-name { font-size: $font-size-base; font-weight: 600; color: $text-primary; }
.pos-pnl { font-size: $font-size-sm; font-weight: 600; }
.rating-tag { display: flex; align-items: center; gap: 4rpx; padding: 4rpx 12rpx; border-radius: 8rpx; font-size: $font-size-xs; margin-left: auto;
  &.healthy { background: #DCFCE7; color: #166534; }
  &.neutral { background: #F3F4F6; color: #6B7280; }
  &.caution { background: #FEF3C7; color: #92400E; }
  &.risk { background: #FEE2E2; color: #991B1B; }
}
.rating-icon { font-size: 20rpx; }
.rating-text { font-weight: 500; }
.pos-signals { margin-top: 8rpx; display: flex; flex-wrap: wrap; gap: 6rpx 12rpx; }
.signal-item { display: flex; align-items: center; gap: 4rpx; }
.signal-icon { font-size: 22rpx; }
.signal-text { font-size: $font-size-xs; color: $text-secondary; }
.pos-action { margin-top: 8rpx; }
.action-text { font-size: $font-size-sm; color: $color-primary; font-weight: 500; }

.risk-list { display: flex; flex-direction: column; gap: 12rpx; }
.risk-item { display: flex; gap: 12rpx; align-items: flex-start; }
.risk-icon { font-size: 24rpx; margin-top: 2rpx; flex-shrink: 0; }
.risk-body { display: flex; flex-direction: column; gap: 4rpx; }
.risk-title { font-size: $font-size-sm; font-weight: 600; color: $text-primary; }
.risk-desc { font-size: $font-size-xs; color: $text-hint; }

.suggestion-list { display: flex; flex-direction: column; gap: 10rpx; }
.suggestion-item { display: flex; align-items: flex-start; gap: 8rpx; }
.sg-priority { font-size: $font-size-xs; font-weight: 700; flex-shrink: 0;
  &.p-high { color: #EF4444; }
  &.p-medium { color: #F59E0B; }
  &.p-low { color: #3B82F6; }
}
.sg-text { font-size: $font-size-sm; color: $text-primary; }

.disclaimer { padding: 16rpx 32rpx; text-align: center; }
.disclaimer text { font-size: $font-size-xs; color: $text-hint; }

.empty-state { display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 120rpx 0; }
.empty-icon { font-size: 80rpx; margin-bottom: 24rpx; }
.empty-text { font-size: $font-size-base; color: $text-secondary; }
.empty-sub { font-size: $font-size-sm; color: $color-primary; margin-top: 8rpx; cursor: pointer;
  &:active { opacity: 0.7; }
}

/* Agent 悬浮球 */
.agent-fab {
  position: fixed; bottom: calc(100rpx + env(safe-area-inset-bottom)); right: 32rpx;
  width: 96rpx; height: 96rpx; border-radius: 50%;
  background: linear-gradient(135deg, $color-primary, #7c3aed);
  box-shadow: 0 8rpx 32rpx rgba($color-primary, 0.4);
  display: flex; align-items: center; justify-content: center;
  z-index: 50; cursor: pointer;
  animation: fab-pulse 2.5s ease-in-out infinite;
  &:active { transform: scale(0.9); }
}
.fab-icon { font-size: 44rpx; }
@keyframes fab-pulse {
  0%, 100% { box-shadow: 0 8rpx 32rpx rgba($color-primary, 0.4); }
  50% { box-shadow: 0 8rpx 48rpx rgba($color-primary, 0.65); }
}

/* ===== 对话弹窗 ===== */
.chat-overlay {
  position: fixed; top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.5); z-index: 9999;
  display: flex; flex-direction: column; justify-content: flex-end;
}
.chat-popup {
  background: $bg-page; border-radius: 24rpx 24rpx 0 0;
  height: 85vh; display: flex; flex-direction: column;
  overflow: hidden;
}
.chat-popup-header {
  display: flex; align-items: center; padding: 24rpx 24rpx 16rpx; gap: 16rpx;
  background: $bg-card; border-bottom: 1rpx solid $border-color; flex-shrink: 0;
}
.popup-back { font-size: 36rpx; color: $text-hint; padding: 4rpx 8rpx; cursor: pointer; }
.popup-title { font-size: $font-size-lg; font-weight: 700; color: $text-primary; flex: 1; }
.model-switch { display: flex; gap: 8rpx; }
.model-opt {
  padding: 6rpx 20rpx; border-radius: 20rpx; font-size: $font-size-xs;
  background: $bg-page; color: $text-hint; border: 2rpx solid $border-color; cursor: pointer;
  white-space: nowrap;
  &:active { opacity: 0.8; }
  &.active { background: rgba($color-primary, 0.08); color: $color-primary; border-color: $color-primary; font-weight: 600; }
}

.chat-list { flex: 1; overflow-y: auto; padding: 24rpx; }

.chat-welcome { display: flex; flex-direction: column; align-items: center; padding: 80rpx 0; }
.welcome-icon { font-size: 80rpx; margin-bottom: 20rpx; }
.welcome-text { font-size: $font-size-base; color: $text-hint; }
.quick-qs { display: flex; flex-wrap: wrap; justify-content: center; gap: 12rpx; margin-top: 32rpx; }
.quick-q {
  padding: 10rpx 24rpx; border-radius: 24rpx; font-size: $font-size-sm;
  background: $bg-card; color: $text-primary; border: 1rpx solid $border-color; cursor: pointer;
  &:active { opacity: 0.7; background: rgba($color-primary, 0.05); }
}

.msg-row { display: flex; margin-bottom: 24rpx;
  &.user { justify-content: flex-end; }
  &.ai { justify-content: flex-start; }
}
.msg-bubble { max-width: 78%; padding: 20rpx 28rpx; border-radius: 20rpx; font-size: $font-size-base; line-height: 1.7; word-break: break-word; }
.bubble-user { background: $color-primary; color: #fff; border-bottom-right-radius: 6rpx; }
.bubble-ai { background: $bg-card; color: $text-primary; border: 1rpx solid $border-color; border-bottom-left-radius: 6rpx; }
.msg-text { white-space: pre-wrap; }
.cursor-blink { color: $color-primary; font-weight: 700; animation: blink 0.8s infinite; }
@keyframes blink { 0%,50% { opacity: 1; } 51%,100% { opacity: 0; } }

.chat-input-bar {
  display: flex; gap: 12rpx; padding: 16rpx 24rpx; padding-bottom: calc(16rpx + env(safe-area-inset-bottom));
  background: $bg-card; border-top: 1rpx solid $border-color; flex-shrink: 0;
}
.chat-msg-input {
  flex: 1; height: 76rpx; background: $bg-page; border-radius: $border-radius;
  padding: 0 20rpx; font-size: $font-size-sm; border: 1rpx solid $border-color;
}
.chat-send-btn {
  width: 120rpx; height: 76rpx; border-radius: $border-radius; font-size: $font-size-sm;
  font-weight: 600; color: #fff; background: $color-primary; border: none; flex-shrink: 0;
  &::after { border: none; }
  &[disabled] { opacity: 0.5; }
}

.up { color: $color-up; }
.down { color: $color-down; }
</style>
