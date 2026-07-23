<template>
  <view class="console-page">
    <!-- 顶部：交易员信息 + 模式切换 -->
    <view class="header">
      <view class="trader-info">
        <view class="trader-avatar">
          <text class="avatar-text">{{ traderName[0] || 'A' }}</text>
        </view>
        <view class="trader-meta">
          <text class="trader-name">{{ traderName }}</text>
          <text class="trader-tag">{{ traderTag }}</text>
        </view>
      </view>
      <view class="mode-switch" @click="toggleMode">
        <text class="mode-text">{{ managementMode === 'full_managed' ? '托管模式' : '建议模式' }}</text>
        <view class="switch-track" :class="{ active: managementMode === 'full_managed' }">
          <view class="switch-knob"></view>
        </view>
      </view>
    </view>

    <!-- 概览卡片 -->
    <view class="overview-row">
      <view class="ov-card">
        <text class="ov-value">¥{{ formatMoney(overview.total_assets) }}</text>
        <text class="ov-label">总资产</text>
      </view>
      <view class="ov-card">
        <text class="ov-value" :class="overview.unrealized_pnl >= 0 ? 'up' : 'down'">
          {{ formatPct(overview.unrealized_pnl) }}
        </text>
        <text class="ov-label">浮动盈亏</text>
      </view>
      <view class="ov-card">
        <text class="ov-value">{{ overview.position_count }}</text>
        <text class="ov-label">持仓数</text>
      </view>
      <view class="ov-card">
        <text class="ov-value" style="color: #f39c12">{{ overview.pending_signals }}</text>
        <text class="ov-label">待处理信号</text>
      </view>
    </view>

    <!-- Tab 切换 -->
    <view class="tabs">
      <view class="tab-item" :class="{ active: activeTab === 'signals' }" @click="activeTab = 'signals'">
        <text>信号</text>
      </view>
      <view class="tab-item" :class="{ active: activeTab === 'portfolio' }" @click="activeTab = 'portfolio'">
        <text>持仓</text>
      </view>
      <view class="tab-item" :class="{ active: activeTab === 'trades' }" @click="activeTab = 'trades'">
        <text>交易日志</text>
      </view>
    </view>

    <!-- 信号列表 -->
    <view v-if="activeTab === 'signals'" class="signal-list">
      <view v-if="signals.length === 0" class="empty-tip">
        <text>暂无信号，点击右上角生成</text>
      </view>
      <view v-for="sig in signals" :key="sig.id" class="signal-card">
        <view class="sig-head">
          <view class="sig-stock">
            <text class="sig-symbol">{{ sig.symbol }}</text>
            <text class="sig-name">{{ sig.symbol_name }}</text>
          </view>
          <text :class="sig.action === 'buy' ? 'action-buy' : 'action-sell'">
            {{ sig.action === 'buy' ? '买入' : '卖出' }}
          </text>
        </view>
        <view class="sig-body">
          <view class="sig-item">
            <text class="sig-label">建议价</text>
            <text class="sig-val">¥{{ sig.price.toFixed(2) }}</text>
          </view>
          <view class="sig-item">
            <text class="sig-label">数量</text>
            <text class="sig-val">{{ sig.quantity }} 股</text>
          </view>
          <view class="sig-item">
            <text class="sig-label">置信度</text>
            <view class="conf-bar">
              <view class="conf-fill" :style="{ width: sig.confidence + '%' }"></view>
            </view>
            <text class="sig-val">{{ sig.confidence }}%</text>
          </view>
        </view>
        <view v-if="sig.reasoning" class="sig-reason">
          <text>{{ sig.reasoning }}</text>
        </view>
        <view v-if="sig.exec_status === 'pending' && managementMode === 'advisory'" class="sig-actions">
          <view class="btn-confirm" @click="handleConfirm(sig)">
            <text>确认</text>
          </view>
          <view class="btn-ignore" @click="handleIgnore(sig)">
            <text>忽略</text>
          </view>
        </view>
        <view v-else class="sig-status">
          <text :class="statusClass(sig.exec_status)">{{ statusText(sig.exec_status) }}</text>
        </view>
      </view>
    </view>

    <!-- 持仓列表 -->
    <view v-if="activeTab === 'portfolio'" class="portfolio-list">
      <view v-if="portfolios.length === 0" class="empty-tip">
        <text>暂无持仓</text>
      </view>
      <view v-for="pos in portfolios" :key="pos.id" class="portfolio-card">
        <view class="pos-head">
          <text class="pos-symbol">{{ pos.symbol }}</text>
          <text class="pos-name">{{ pos.symbol_name }}</text>
        </view>
        <view class="pos-grid">
          <view class="pos-item">
            <text class="pos-label">数量</text>
            <text class="pos-val">{{ pos.quantity }}</text>
          </view>
          <view class="pos-item">
            <text class="pos-label">成本</text>
            <text class="pos-val">¥{{ pos.avg_cost.toFixed(2) }}</text>
          </view>
          <view class="pos-item">
            <text class="pos-label">现价</text>
            <text class="pos-val">¥{{ (pos.current_price || 0).toFixed(2) }}</text>
          </view>
          <view class="pos-item">
            <text class="pos-label">市值</text>
            <text class="pos-val">¥{{ formatMoney(pos.market_value || 0) }}</text>
          </view>
          <view class="pos-item">
            <text class="pos-label">盈亏</text>
            <text class="pos-val" :class="(pos.unrealized_pnl || 0) >= 0 ? 'up' : 'down'">
              {{ formatPct(pos.unrealized_pnl || 0) }}
            </text>
          </view>
        </view>
      </view>
    </view>

    <!-- 交易日志 -->
    <view v-if="activeTab === 'trades'" class="trade-list">
      <view v-if="trades.length === 0" class="empty-tip">
        <text>暂无交易记录</text>
      </view>
      <view v-for="trade in trades" :key="trade.id" class="trade-card">
        <view class="trade-head">
          <text class="trade-symbol">{{ trade.symbol }} {{ trade.symbol_name }}</text>
          <text :class="trade.action === 'buy' ? 'action-buy' : 'action-sell'">
            {{ trade.action === 'buy' ? '买入' : '卖出' }}
          </text>
        </view>
        <view class="trade-body">
          <text class="trade-detail">¥{{ trade.price.toFixed(2) }} × {{ trade.quantity }}股</text>
          <text class="trade-time">{{ formatTime(trade.executed_at) }}</text>
        </view>
      </view>
    </view>

    <!-- 生成信号按钮 -->
    <view class="fab" @click="handleGenerate">
      <text class="fab-text">生成信号</text>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue"
import { onShow } from '@dcloudio/uni-app'
import {
  getConsoleOverview,
  getSignals,
  getAgentPortfolio,
  getAgentTrades,
  confirmSignal,
  ignoreSignal,
  switchMode,
  generateSignals,
  type ConsoleOverview,
  type ConsoleSignal,
  type ConsolePortfolio,
  type ConsoleTrade,
} from '@/api/agent'

const hireId = ref<number>(0)
const activeTab = ref<'signals' | 'portfolio' | 'trades'>('signals')

const overview = ref<ConsoleOverview>({
  hire_id: 0,
  trader_name: '',
  trader_tag: '',
  management_mode: 'advisory',
  status: 'active',
  total_assets: 0,
  unrealized_pnl: 0,
  today_signals: 0,
  pending_signals: 0,
  position_count: 0,
})

const traderName = ref('')
const traderTag = ref('')
const managementMode = ref('advisory')

const signals = ref<ConsoleSignal[]>([])
const portfolios = ref<ConsolePortfolio[]>([])
const trades = ref<ConsoleTrade[]>([])

onMounted(() => {
  const pages = getCurrentPages()
  const page = pages[pages.length - 1] as any
  hireId.value = parseInt(page.options?.hire_id || '0')
  loadAll()
})

onShow(() => {
  if (hireId.value) loadAll()
})

const loadAll = async () => {
  if (!hireId.value) return
  try {
    const ov = await getConsoleOverview(hireId.value)
    overview.value = ov
    traderName.value = ov.trader_name
    traderTag.value = ov.trader_tag
    managementMode.value = ov.management_mode
    await Promise.all([loadSignals(), loadPortfolio(), loadTrades()])
  } catch (e: any) {
    uni.showToast({ title: e?.message || '加载失败', icon: 'none' })
  }
}

const loadSignals = async () => {
  signals.value = await getSignals(hireId.value)
}

const loadPortfolio = async () => {
  portfolios.value = await getAgentPortfolio(hireId.value)
}

const loadTrades = async () => {
  trades.value = await getAgentTrades(hireId.value)
}

const toggleMode = async () => {
  const newMode = managementMode.value === 'full_managed' ? 'advisory' : 'full_managed'
  try {
    await switchMode(hireId.value, newMode)
    managementMode.value = newMode
    uni.showToast({ title: '已切换', icon: 'success' })
    await loadAll()
  } catch (e: any) {
    uni.showToast({ title: e?.message || '切换失败', icon: 'none' })
  }
}

const handleConfirm = async (sig: ConsoleSignal) => {
  try {
    await confirmSignal(sig.id)
    uni.showToast({ title: '已确认', icon: 'success' })
    await loadAll()
  } catch (e: any) {
    uni.showToast({ title: e?.message || '确认失败', icon: 'none' })
  }
}

const handleIgnore = async (sig: ConsoleSignal) => {
  try {
    await ignoreSignal(sig.id)
    uni.showToast({ title: '已忽略', icon: 'none' })
    await loadAll()
  } catch (e: any) {
    uni.showToast({ title: e?.message || '操作失败', icon: 'none' })
  }
}

const handleGenerate = async () => {
  try {
    uni.showLoading({ title: '生成中...' })
    await generateSignals(hireId.value)
    uni.hideLoading()
    uni.showToast({ title: '已生成信号', icon: 'success' })
    await loadAll()
  } catch (e: any) {
    uni.hideLoading()
    uni.showToast({ title: e?.message || '生成失败', icon: 'none' })
  }
}

const formatMoney = (v: number) => {
  if (v >= 10000) return (v / 10000).toFixed(2) + '万'
  return v.toFixed(0)
}

const formatPct = (v: number) => {
  if (v == null) return '--'
  return (v >= 0 ? '+' : '') + v.toFixed(2) + '%'
}

const formatTime = (t: string | null) => {
  if (!t) return ''
  return t.slice(0, 16).replace('T', ' ')
}

const statusText = (s: string) => {
  const map: Record<string, string> = {
    pending: '待处理',
    confirmed: '已确认',
    auto_executed: '已执行',
    ignored: '已忽略',
    expired: '已过期',
  }
  return map[s] || s
}

const statusClass = (s: string) => {
  if (s === 'confirmed' || s === 'auto_executed') return 'status-done'
  if (s === 'ignored' || s === 'expired') return 'status-cancel'
  return 'status-pending'
}
</script>

<style scoped lang="scss">
.console-page {
  min-height: 100vh;
  background: #0f0f1a;
  padding: 24rpx 24rpx 120rpx;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24rpx;

  .trader-info {
    display: flex;
    align-items: center;

    .trader-avatar {
      width: 72rpx;
      height: 72rpx;
      border-radius: 18rpx;
      background: linear-gradient(135deg, #4A90E2, #7B68EE);
      display: flex;
      align-items: center;
      justify-content: center;
      margin-right: 16rpx;

      .avatar-text {
        font-size: 32rpx;
        font-weight: 700;
        color: #fff;
      }
    }

    .trader-meta {
      .trader-name {
        font-size: 30rpx;
        font-weight: 700;
        color: #fff;
        display: block;
      }
      .trader-tag {
        font-size: 22rpx;
        color: #4A90E2;
      }
    }
  }

  .mode-switch {
    display: flex;
    align-items: center;
    gap: 12rpx;

    .mode-text {
      font-size: 24rpx;
      color: #667788;
    }

    .switch-track {
      width: 80rpx;
      height: 40rpx;
      border-radius: 20rpx;
      background: rgba(255, 255, 255, 0.1);
      position: relative;
      transition: background 0.3s;

      &.active {
        background: #4A90E2;
      }

      .switch-knob {
        position: absolute;
        top: 4rpx;
        left: 4rpx;
        width: 32rpx;
        height: 32rpx;
        border-radius: 50%;
        background: #fff;
        transition: transform 0.3s;

        .switch-track.active & {
          transform: translateX(40rpx);
        }
      }
    }
  }
}

.overview-row {
  display: flex;
  gap: 12rpx;
  margin-bottom: 24rpx;

  .ov-card {
    flex: 1;
    background: #1a1a2e;
    border-radius: 16rpx;
    padding: 20rpx 12rpx;
    display: flex;
    flex-direction: column;
    align-items: center;

    .ov-value {
      font-size: 26rpx;
      font-weight: 700;
      color: #fff;
      font-family: 'DIN Alternate', monospace;
    }
    .ov-label {
      font-size: 20rpx;
      color: #667788;
      margin-top: 6rpx;
    }
  }
}

.tabs {
  display: flex;
  background: #1a1a2e;
  border-radius: 16rpx;
  padding: 8rpx;
  margin-bottom: 24rpx;

  .tab-item {
    flex: 1;
    text-align: center;
    padding: 16rpx 0;
    font-size: 26rpx;
    color: #667788;
    border-radius: 12rpx;

    &.active {
      background: rgba(74, 144, 226, 0.15);
      color: #4A90E2;
      font-weight: 700;
    }
  }
}

.empty-tip {
  text-align: center;
  padding: 80rpx 0;
  color: #667788;
  font-size: 26rpx;
}

.signal-card {
  background: #1a1a2e;
  border-radius: 16rpx;
  padding: 24rpx;
  margin-bottom: 16rpx;

  .sig-head {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16rpx;

    .sig-stock {
      .sig-symbol {
        font-size: 28rpx;
        font-weight: 700;
        color: #fff;
        margin-right: 12rpx;
      }
      .sig-name {
        font-size: 24rpx;
        color: #667788;
      }
    }

    .action-buy {
      font-size: 24rpx;
      color: #e74c3c;
      background: rgba(231, 76, 60, 0.12);
      padding: 4rpx 16rpx;
      border-radius: 8rpx;
    }
    .action-sell {
      font-size: 24rpx;
      color: #27ae60;
      background: rgba(39, 174, 96, 0.12);
      padding: 4rpx 16rpx;
      border-radius: 8rpx;
    }
  }

  .sig-body {
    display: flex;
    flex-direction: column;
    gap: 12rpx;
    margin-bottom: 16rpx;

    .sig-item {
      display: flex;
      align-items: center;
      gap: 12rpx;

      .sig-label {
        font-size: 22rpx;
        color: #667788;
        width: 100rpx;
      }
      .sig-val {
        font-size: 24rpx;
        color: #fff;
      }
      .conf-bar {
        flex: 1;
        height: 12rpx;
        background: rgba(255, 255, 255, 0.08);
        border-radius: 6rpx;
        overflow: hidden;

        .conf-fill {
          height: 100%;
          background: linear-gradient(90deg, #4A90E2, #7B68EE);
          border-radius: 6rpx;
        }
      }
    }
  }

  .sig-reason {
    font-size: 22rpx;
    color: #8899aa;
    line-height: 1.5;
    margin-bottom: 16rpx;
    padding: 12rpx;
    background: rgba(255, 255, 255, 0.04);
    border-radius: 8rpx;
  }

  .sig-actions {
    display: flex;
    gap: 16rpx;

    .btn-confirm {
      flex: 1;
      text-align: center;
      padding: 16rpx 0;
      background: #4A90E2;
      border-radius: 12rpx;
      color: #fff;
      font-size: 26rpx;
    }
    .btn-ignore {
      flex: 1;
      text-align: center;
      padding: 16rpx 0;
      background: rgba(255, 255, 255, 0.08);
      border-radius: 12rpx;
      color: #8899aa;
      font-size: 26rpx;
    }
  }

  .sig-status {
    text-align: center;
    padding: 12rpx 0;

    .status-done {
      font-size: 24rpx;
      color: #27ae60;
    }
    .status-cancel {
      font-size: 24rpx;
      color: #667788;
    }
    .status-pending {
      font-size: 24rpx;
      color: #f39c12;
    }
  }
}

.portfolio-card {
  background: #1a1a2e;
  border-radius: 16rpx;
  padding: 24rpx;
  margin-bottom: 16rpx;

  .pos-head {
    margin-bottom: 16rpx;
    .pos-symbol {
      font-size: 28rpx;
      font-weight: 700;
      color: #fff;
      margin-right: 12rpx;
    }
    .pos-name {
      font-size: 24rpx;
      color: #667788;
    }
  }

  .pos-grid {
    display: flex;
    flex-wrap: wrap;
    gap: 16rpx;

    .pos-item {
      width: calc(33.33% - 12rpx);
      display: flex;
      flex-direction: column;

      .pos-label {
        font-size: 20rpx;
        color: #667788;
      }
      .pos-val {
        font-size: 24rpx;
        color: #fff;
        font-weight: 600;
        margin-top: 4rpx;
      }
    }
  }
}

.trade-card {
  background: #1a1a2e;
  border-radius: 16rpx;
  padding: 24rpx;
  margin-bottom: 16rpx;

  .trade-head {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12rpx;

    .trade-symbol {
      font-size: 26rpx;
      color: #fff;
      font-weight: 600;
    }
  }

  .trade-body {
    display: flex;
    justify-content: space-between;
    align-items: center;

    .trade-detail {
      font-size: 24rpx;
      color: #8899aa;
    }
    .trade-time {
      font-size: 20rpx;
      color: #667788;
    }
  }
}

.fab {
  position: fixed;
  right: 40rpx;
  bottom: 60rpx;
  background: linear-gradient(135deg, #4A90E2, #7B68EE);
  border-radius: 40rpx;
  padding: 20rpx 36rpx;
  box-shadow: 0 8rpx 24rpx rgba(74, 144, 226, 0.3);

  .fab-text {
    color: #fff;
    font-size: 26rpx;
    font-weight: 600;
  }
}

.up { color: #e74c3c; }
.down { color: #27ae60; }
</style>
