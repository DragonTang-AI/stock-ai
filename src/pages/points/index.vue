<template>
  <view class="points-page">
    <!-- 顶栏余额卡片 -->
    <view class="balance-card">
      <text class="balance-label">可用积分</text>
      <text class="balance-value">{{ balance }}</text>
      <text class="balance-sub">雇佣交易员将消耗积分</text>
    </view>

    <!-- 筛选Tab -->
    <view class="filter-tabs">
      <view
        v-for="tab in tabs"
        :key="tab.value"
        :class="['tab-item', activeTab === tab.value ? 'tab-active' : '']"
        @click="activeTab = tab.value"
      >
        {{ tab.label }}
      </view>
    </view>

    <!-- 积分明细列表 -->
    <view class="transaction-list" v-if="filteredList.length > 0">
      <view
        v-for="tx in filteredList"
        :key="tx.id"
        class="tx-item"
      >
        <view class="tx-left">
          <view :class="['tx-icon', tx.amount > 0 ? 'icon-in' : 'icon-out']">
            {{ tx.amount > 0 ? '↓' : '↑' }}
          </view>
        </view>
        <view class="tx-center">
          <text class="tx-desc">{{ getTxLabel(tx) }}</text>
          <text class="tx-time">{{ formatTime(tx.created_at) }}</text>
        </view>
        <view class="tx-right">
          <text :class="['tx-amount', tx.amount > 0 ? 'amount-plus' : 'amount-minus']">
            {{ tx.amount > 0 ? '+' : '' }}{{ tx.amount }}
          </text>
          <text class="tx-balance">余额 {{ tx.balance_after }}</text>
        </view>
      </view>
    </view>

    <!-- 空状态 -->
    <view class="empty-state" v-else>
      <text class="empty-text">暂无积分记录</text>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { getPointsBalance, getPointsHistory } from '@/api/points'

interface Transaction {
  id: number
  user_id: number
  amount: number
  balance_after: number
  tx_type: string
  reference_id: string | null
  description: string
  created_at: string
}

const tabs = [
  { label: '全部', value: 'all' },
  { label: '收入', value: 'income' },
  { label: '支出', value: 'expense' },
]

const balance = ref(0)
const transactions = ref<Transaction[]>([])
const activeTab = ref('all')

const filteredList = computed(() => {
  if (activeTab.value === 'all') return transactions.value
  if (activeTab.value === 'income') return transactions.value.filter(t => t.amount > 0)
  return transactions.value.filter(t => t.amount < 0)
})

const getTxLabel = (tx: Transaction) => {
  const map: Record<string, string> = {
    initial: '注册赠送',
    hire_agent: '雇佣交易员',
    sign_in: '每日签到',
    invite: '邀请好友',
  }
  return map[tx.tx_type] || tx.description || tx.tx_type
}

const formatTime = (t: string) => {
  if (!t) return ''
  const d = new Date(t)
  const pad = (n: number) => n.toString().padStart(2, '0')
  return 
}

const loadData = async () => {
  try {
    const balRes = await getPointsBalance()
    balance.value = balRes.data?.balance ?? 0

    const txRes = await getPointsHistory({ limit: 50 })
    transactions.value = txRes.data?.items ?? txRes.data ?? []
  } catch (e) {
    console.error('load points error', e)
  }
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.points-page {
  min-height: 100vh;
  background: #0f0f1a;
  padding-bottom: 40rpx;
}

.balance-card {
  margin: 24rpx;
  padding: 40rpx 32rpx;
  background: linear-gradient(135deg, #1a5a3a 0%, #0d3d2e 100%);
  border-radius: 20rpx;
  display: flex;
  flex-direction: column;
  align-items: center;
  border: 1rpx solid rgba(74, 222, 128, 0.25);
}

.balance-label {
  font-size: 26rpx;
  color: rgba(255,255,255,0.6);
  margin-bottom: 12rpx;
}

.balance-value {
  font-size: 64rpx;
  font-weight: 800;
  color: #4ade80;
  font-variant-numeric: tabular-nums;
}

.balance-sub {
  font-size: 22rpx;
  color: rgba(255,255,255,0.4);
  margin-top: 12rpx;
}

.filter-tabs {
  display: flex;
  margin: 0 24rpx 16rpx;
  border-bottom: 1rpx solid rgba(255,255,255,0.08);
}

.tab-item {
  flex: 1;
  text-align: center;
  padding: 20rpx 0;
  font-size: 28rpx;
  color: rgba(255,255,255,0.45);
  position: relative;
}

.tab-active {
  color: #aaddff;
  font-weight: 600;
}

.tab-active::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 48rpx;
  height: 4rpx;
  background: #4a90e2;
  border-radius: 2rpx;
}

.transaction-list {
  margin: 0 24rpx;
}

.tx-item {
  display: flex;
  align-items: center;
  padding: 24rpx 0;
  border-bottom: 1rpx solid rgba(255,255,255,0.06);
}

.tx-left {
  width: 56rpx;
  height: 56rpx;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 20rpx;
}

.tx-icon {
  width: 48rpx;
  height: 48rpx;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28rpx;
  font-weight: 700;
}

.icon-in {
  background: rgba(74,222,128,0.12);
  color: #4ade80;
}

.icon-out {
  background: rgba(239,68,68,0.12);
  color: #ef4444;
}

.tx-center {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.tx-desc {
  font-size: 28rpx;
  color: #ddd;
  margin-bottom: 6rpx;
}

.tx-time {
  font-size: 22rpx;
  color: rgba(255,255,255,0.35);
}

.tx-right {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

.tx-amount {
  font-size: 30rpx;
  font-weight: 700;
}

.amount-plus {
  color: #4ade80;
}

.amount-minus {
  color: #ef4444;
}

.tx-balance {
  font-size: 22rpx;
  color: rgba(255,255,255,0.35);
  margin-top: 6rpx;
}

.empty-state {
  padding: 120rpx 0;
  text-align: center;
}

.empty-text {
  font-size: 28rpx;
  color: rgba(255,255,255,0.3);
}
</style>
