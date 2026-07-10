<template>
  <view class="history-page">
    <!-- 骨架屏 -->
    <LoadingSkeleton v-if="loading" scene="list" :rows="4" />

    <!-- 内容 -->
    <view v-else class="history-content">
      <!-- 统计概览 -->
      <view class="summary-bar">
        <view class="summary-item">
          <text class="summary-value">{{ stats.totalTrades }}</text>
          <text class="summary-label">总交易笔数</text>
        </view>
        <view class="summary-item">
          <text class="summary-value">{{ stats.winRate }}%</text>
          <text class="summary-label">胜率</text>
        </view>
        <view class="summary-item">
          <text class="summary-value" :class="stats.totalPnl >= 0 ? 'up' : 'down'">
            {{ stats.totalPnl >= 0 ? '+' : '' }}{{ stats.totalPnl }}
          </text>
          <text class="summary-label">累计盈亏</text>
        </view>
      </view>

      <!-- 交易记录列表 -->
      <view v-if="records.length > 0" class="record-list">
        <view class="section-title">交易记录</view>
        <view
          v-for="record in records"
          :key="record.id"
          class="record-item"
        >
          <view class="record-info">
            <text class="record-name">{{ record.stockName }}</text>
            <text class="record-code">{{ record.stockCode }}</text>
          </view>
          <view class="record-meta">
            <text class="record-type" :class="record.type === 'buy' ? 'buy' : 'sell'">
              {{ record.type === 'buy' ? '买入' : '卖出' }}
            </text>
            <text class="record-amount">{{ record.quantity }}股 @ {{ record.price }}</text>
          </view>
          <view class="record-footer">
            <text class="record-time">{{ record.time }}</text>
            <text class="record-pnl" :class="(record.pnl || 0) >= 0 ? 'up' : 'down'">
              {{ (record.pnl || 0) >= 0 ? '+' : '' }}{{ record.pnl || 0 }}
            </text>
          </view>
        </view>
      </view>

      <!-- 空状态 -->
      <EmptyState
        v-if="!loading && records.length === 0"
        message="暂无交易记录"
        hint="完成一笔交易后，记录将在此处显示"
      />

      <!-- 对账区域 -->
      <view v-if="records.length > 0" class="reconciliation">
        <view class="section-title">持仓对账</view>
        <view class="recon-card">
          <text class="recon-text">对账功能开发中，敬请期待</text>
        </view>
      </view>
    </view>

    <Disclaimer />
  </view>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import LoadingSkeleton from '@/components/common/LoadingSkeleton.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import Disclaimer from '@/components/compliance/Disclaimer.vue'

interface TradeRecord {
  id: number
  stockName: string
  stockCode: string
  type: 'buy' | 'sell'
  quantity: number
  price: string
  time: string
  pnl?: number
}

const loading = ref(true)
const records = ref<TradeRecord[]>([])
const stats = ref({
  totalTrades: 0,
  winRate: 0,
  totalPnl: 0,
})

async function fetchHistory() {
  loading.value = true
  try {
    // TODO: 对接交易记录 API
    records.value = []
    stats.value = { totalTrades: 0, winRate: 0, totalPnl: 0 }
  } catch {
    // 忽略
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchHistory()
})
</script>

<style scoped lang="scss">
.history-page {
  min-height: 100vh;
  background: var(--bg-page, #f5f5f7);
}

.history-content {
  padding: 24rpx;
}

.summary-bar {
  display: flex;
  background: #fff;
  border-radius: 16rpx;
  padding: 32rpx;
  margin-bottom: 24rpx;
}

.summary-item {
  flex: 1;
  text-align: center;
}

.summary-value {
  display: block;
  font-size: 40rpx;
  font-weight: 700;
  color: var(--text-primary, #333);

  &.up { color: #f5222d; }
  &.down { color: #52c41a; }
}

.summary-label {
  display: block;
  font-size: 22rpx;
  color: var(--text-hint, #999);
  margin-top: 8rpx;
}

.section-title {
  font-size: 30rpx;
  font-weight: 600;
  color: var(--text-primary, #333);
  margin-bottom: 16rpx;
}

.record-list {
  background: #fff;
  border-radius: 16rpx;
  padding: 24rpx;
  margin-bottom: 24rpx;
}

.record-item {
  padding: 20rpx 0;
  border-bottom: 1rpx solid var(--border-color, #f0f0f0);

  &:last-child { border-bottom: none; }
}

.record-info {
  display: flex;
  align-items: baseline;
  gap: 12rpx;
  margin-bottom: 8rpx;
}

.record-name {
  font-size: 30rpx;
  font-weight: 500;
  color: var(--text-primary, #333);
}

.record-code {
  font-size: 22rpx;
  color: var(--text-hint, #999);
}

.record-meta {
  display: flex;
  gap: 16rpx;
  margin-bottom: 8rpx;
}

.record-type {
  font-size: 24rpx;
  padding: 2rpx 12rpx;
  border-radius: 4rpx;

  &.buy { background: rgba(245, 34, 45, 0.1); color: #f5222d; }
  &.sell { background: rgba(82, 196, 26, 0.1); color: #52c41a; }
}

.record-amount {
  font-size: 24rpx;
  color: var(--text-secondary, #666);
}

.record-footer {
  display: flex;
  justify-content: space-between;
}

.record-time {
  font-size: 22rpx;
  color: var(--text-hint, #999);
}

.record-pnl {
  font-size: 26rpx;
  font-weight: 600;

  &.up { color: #f5222d; }
  &.down { color: #52c41a; }
}

.reconciliation {
  margin-bottom: 24rpx;
}

.recon-card {
  background: #fff;
  border-radius: 16rpx;
  padding: 48rpx 24rpx;
  text-align: center;
}

.recon-text {
  font-size: 26rpx;
  color: var(--text-hint, #999);
}
</style>
