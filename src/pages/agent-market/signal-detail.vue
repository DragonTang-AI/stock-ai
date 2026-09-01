<template>
  <view class="signal-detail-page">
    <view v-if="isLoading" class="detail-loading">
      <text>加载中...</text>
    </view>

    <view v-else-if="signal" class="detail-content">
      <!-- 顶部操作卡片 -->
      <view class="action-hero" :class="signal.action === 'buy' ? 'hero-buy' : 'hero-sell'">
        <view class="hero-side">
          <view class="action-badge">{{ signal.action === 'buy' ? '买入' : '卖出' }}</view>
          <text class="hero-symbol">{{ signal.symbol_name || signal.symbol }}</text>
          <text class="hero-code">{{ signal.symbol }} · {{ signal.market === 'HK' ? '港股' : 'A股' }}</text>
        </view>
        <view class="hero-trader">
          <text class="hero-trader-label">交易员</text>
          <text class="hero-trader-name">{{ signal.trader_id }}</text>
        </view>
      </view>

      <!-- 交易参数 -->
      <view class="panel">
        <view class="panel-title">交易参数</view>
        <view class="param-grid">
          <view class="param-item">
            <text class="param-label">成交价</text>
            <text class="param-value">{{ signal.price }}</text>
          </view>
          <view class="param-item">
            <text class="param-label">数量</text>
            <text class="param-value">{{ signal.quantity }} 股</text>
          </view>
          <view class="param-item">
            <text class="param-label">信心指数</text>
            <text class="param-value" :class="confidenceClass(signal.confidence)">{{ signal.confidence }}%</text>
          </view>
          <view class="param-item">
            <text class="param-label">执行状态</text>
            <text class="param-value" :class="'st-' + signal.exec_status">{{ execText(signal.exec_status) }}</text>
          </view>
        </view>
      </view>

      <!-- 决策理由 -->
      <view class="panel">
        <view class="panel-title">为什么这样选择</view>
        <view class="reason-box">
          <text class="reason-text">{{ signal.reasoning || '暂无决策理由说明' }}</text>
        </view>
      </view>

      <!-- 时间信息 -->
      <view class="panel time-panel">
        <view class="time-row">
          <text class="time-label">信号时间</text>
          <text class="time-value">{{ formatFull(signal.created_at) }}</text>
        </view>
        <view class="time-row" v-if="signal.updated_at">
          <text class="time-label">更新时间</text>
          <text class="time-value">{{ formatFull(signal.updated_at) }}</text>
        </view>
        <view class="time-row">
          <text class="time-label">信号 ID</text>
          <text class="time-value">#{{ signal.id }}</text>
        </view>
      </view>

      <!-- 底部操作 -->
      <view class="bottom-actions" v-if="signal.exec_status === 'pending'">
        <view class="confirm-btn" @click="handleConfirm">确认执行</view>
        <view class="ignore-btn" @click="handleIgnore">忽略信号</view>
      </view>
    </view>

    <view v-else class="detail-empty">
      <text class="empty-text">信号不存在或已删除</text>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { getSignalDetail, confirmSignal, ignoreSignal, type ConsoleSignal } from '@/api/agent'

const signal = ref<ConsoleSignal | null>(null)
const isLoading = ref(true)
let signalId = 0

const loadDetail = async () => {
  if (!signalId) return
  try {
    signal.value = await getSignalDetail(signalId)
  } catch (e: any) {
    uni.showToast({ title: e?.message || '加载失败', icon: 'none' })
  } finally {
    isLoading.value = false
  }
}

const execText = (s: string) => {
  if (s === 'auto_executed') return '已自动成交'
  if (s === 'confirmed') return '已确认成交'
  if (s === 'pending') return '待确认'
  if (s === 'ignored') return '已忽略'
  return s || '--'
}
const confidenceClass = (c: number) => {
  if (c >= 70) return 'conf-high'
  if (c >= 50) return 'conf-mid'
  return 'conf-low'
}
const formatFull = (iso: string) => {
  if (!iso) return '--'
  const d = new Date(iso)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

const handleConfirm = async () => {
  try {
    await confirmSignal(signalId)
    uni.showToast({ title: '已确认执行', icon: 'success' })
    loadDetail()
  } catch (e: any) {
    uni.showToast({ title: e?.message || '确认失败', icon: 'none' })
  }
}
const handleIgnore = async () => {
  try {
    await ignoreSignal(signalId)
    uni.showToast({ title: '已忽略', icon: 'success' })
    loadDetail()
  } catch (e: any) {
    uni.showToast({ title: e?.message || '操作失败', icon: 'none' })
  }
}

onLoad((options: any) => {
  signalId = Number(options.id)
  loadDetail()
})
onMounted(loadDetail)
</script>

<style scoped lang="scss">
.signal-detail-page {
  min-height: 100vh;
  background: #0f0f1a;
  padding: 20rpx 24rpx 120rpx;
}

.action-hero {
  border-radius: 20rpx;
  padding: 40rpx 32rpx;
  margin-bottom: 24rpx;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border: 1rpx solid rgba(255, 255, 255, 0.08);

  &.hero-buy {
    background: linear-gradient(135deg, rgba(231, 76, 60, 0.25), rgba(231, 76, 60, 0.08));
  }
  &.hero-sell {
    background: linear-gradient(135deg, rgba(46, 204, 113, 0.25), rgba(46, 204, 113, 0.08));
  }

  .hero-side {
    .action-badge {
      font-size: 28rpx;
      font-weight: 700;
      color: #fff;
      background: rgba(255, 255, 255, 0.15);
      border-radius: 12rpx;
      padding: 8rpx 24rpx;
      display: inline-block;
      margin-bottom: 12rpx;
    }
    .hero-symbol {
      display: block;
      font-size: 44rpx;
      font-weight: 700;
      color: #fff;
    }
    .hero-code {
      font-size: 22rpx;
      color: rgba(255, 255, 255, 0.6);
    }
  }
  .hero-trader {
    text-align: right;
    .hero-trader-label {
      font-size: 20rpx;
      color: rgba(255, 255, 255, 0.6);
      display: block;
    }
    .hero-trader-name {
      font-size: 30rpx;
      font-weight: 600;
      color: #fff;
    }
  }
}

.panel {
  background: #16162a;
  border-radius: 16rpx;
  padding: 28rpx;
  margin-bottom: 24rpx;
  border: 1rpx solid rgba(74, 144, 226, 0.12);

  .panel-title {
    font-size: 28rpx;
    font-weight: 600;
    color: #ffffff;
    margin-bottom: 20rpx;
  }
}

.param-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 24rpx;

  .param-item {
    width: calc(50% - 12rpx);
    .param-label {
      font-size: 20rpx;
      color: #556677;
      display: block;
    }
    .param-value {
      font-size: 30rpx;
      color: #c8d6e5;
      font-weight: 600;
      &.conf-high { color: #2ecc71; }
      &.conf-mid { color: #f1c40f; }
      &.conf-low { color: #e67e22; }
      &.st-auto_executed { color: #2ecc71; }
      &.st-confirmed { color: #4A90E2; }
      &.st-pending { color: #e67e22; }
    }
  }
}

.reason-box {
  background: rgba(74, 144, 226, 0.08);
  border-radius: 12rpx;
  padding: 24rpx;
  .reason-text {
    font-size: 26rpx;
    color: #aabbcc;
    line-height: 1.7;
  }
}

.time-panel {
  .time-row {
    display: flex;
    justify-content: space-between;
    padding: 10rpx 0;
    .time-label {
      font-size: 24rpx;
      color: #556677;
    }
    .time-value {
      font-size: 24rpx;
      color: #aabbcc;
    }
  }
}

.bottom-actions {
  display: flex;
  gap: 20rpx;
  margin-top: 12rpx;

  .confirm-btn {
    flex: 1;
    text-align: center;
    background: linear-gradient(135deg, #4A90E2, #357ABD);
    color: #fff;
    font-size: 30rpx;
    font-weight: 600;
    padding: 24rpx 0;
    border-radius: 14rpx;
  }
  .ignore-btn {
    flex: 1;
    text-align: center;
    background: rgba(149, 165, 166, 0.15);
    color: #95a5a6;
    font-size: 30rpx;
    padding: 24rpx 0;
    border-radius: 14rpx;
  }
}

.detail-loading, .detail-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 160rpx 0;
  color: #667788;
  font-size: 26rpx;
}
</style>
