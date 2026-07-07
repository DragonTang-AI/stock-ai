<template>
  <view v-if="visible" class="confirm-overlay" @click.self="handleCancel">
    <view class="confirm-dialog slide-up">
      <!-- 标题 -->
      <view class="dialog-header">
        <text class="dialog-title">订单确认</text>
        <text class="dialog-close" @click="handleCancel">✕</text>
      </view>

      <!-- 订单摘要 -->
      <view class="order-summary">
        <view class="summary-row">
          <text class="summary-label">标的</text>
          <text class="summary-value bold">{{ order.name }}（{{ order.symbol }}）</text>
        </view>
        <view class="summary-row">
          <text class="summary-label">方向</text>
          <view class="side-tag" :class="order.side === 'buy' ? 'buy' : 'sell'">
            {{ order.side === 'buy' ? '买入' : '卖出' }}
          </view>
        </view>
        <view class="summary-row">
          <text class="summary-label">数量</text>
          <text class="summary-value">{{ order.qty }} 股</text>
        </view>
        <view class="summary-row">
          <text class="summary-label">委托价</text>
          <text class="summary-value">¥ {{ formatPrice(order.price) }}</text>
        </view>
        <view class="summary-row">
          <text class="summary-label">成交金额</text>
          <text class="summary-value bold">¥ {{ formatAmount(order.amount) }}</text>
        </view>
        <view class="divider"></view>
        <view class="summary-row">
          <text class="summary-label">佣金</text>
          <text class="summary-value">¥ {{ formatAmount(order.commission) }}</text>
        </view>
        <view v-if="order.side === 'sell'" class="summary-row">
          <text class="summary-label">印花税</text>
          <text class="summary-value">¥ {{ formatAmount(order.stamp_tax) }}</text>
        </view>
        <view class="summary-row">
          <text class="summary-label">其他费用</text>
          <text class="summary-value">¥ {{ formatAmount(order.other_fees) }}</text>
        </view>
        <view class="summary-row total">
          <text class="summary-label">总费用</text>
          <text class="summary-value bold">¥ {{ formatAmount(order.totalFee) }}</text>
        </view>
        <view class="summary-row">
          <text class="summary-label">实际{{ order.side === 'buy' ? '支付' : '到账' }}</text>
          <text class="summary-value bold" :class="order.side === 'buy' ? 'pay' : 'recv'">
            ¥ {{ formatAmount(netAmount) }}
          </text>
        </view>
      </view>

      <!-- T+1 规则提示 -->
      <view v-if="isT1Market" class="rule-alert">
        <text class="rule-icon">⏱</text>
        <text class="rule-text">当前为 A 股市场，实行 T+1 结算规则：当日买入的股票次日方可卖出。</text>
      </view>

      <!-- 大额交易二次确认 -->
      <view v-if="isLargeOrder" class="large-warn">
        <text class="large-icon">⚠️</text>
        <text class="large-text">本次交易金额超过 ¥5,000，请确认后提交。</text>
      </view>

      <!-- 操作按钮 -->
      <view class="dialog-actions">
        <button class="btn-cancel" @click="handleCancel">取消</button>
        <button
          class="btn-submit"
          :class="{ buy: order.side === 'buy', sell: order.side === 'sell' }"
          @click="handleSubmit"
        >确认{{ order.side === 'buy' ? '买入' : '卖出' }}</button>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  visible: boolean
  order: {
    symbol: string
    name: string
    side: 'buy' | 'sell'
    qty: number
    price: number
    amount: number
    totalFee: number
    commission: number
    stamp_tax: number
    other_fees: number
    market: string
  }
  accountCash?: number
  availableQty?: number
}>()

const emit = defineEmits<{
  (e: 'confirm'): void
  (e: 'cancel'): void
}>()

const isT1Market = computed(() => {
  return props.order.market === 'A'
})

const isLargeOrder = computed(() => {
  return props.order.amount > 5000
})

const netAmount = computed(() => {
  if (props.order.side === 'buy') {
    return Math.round((props.order.amount + props.order.totalFee) * 100) / 100
  }
  return Math.round((props.order.amount - props.order.totalFee) * 100) / 100
})

function formatPrice(v: number): string {
  if (isNaN(v)) return '0.00'
  return v.toFixed(2)
}

function formatAmount(v: number): string {
  if (isNaN(v)) return '0.00'
  return v.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ',')
}

function handleSubmit() {
  emit('confirm')
}

function handleCancel() {
  emit('cancel')
}
</script>

<style lang="scss" scoped>
.confirm-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: flex-end;
  justify-content: center;
  z-index: 1000;
}

.confirm-dialog {
  width: 100%;
  max-width: 750rpx;
  background: $bg-card;
  border-radius: 24rpx 24rpx 0 0;
  padding: 32rpx 32rpx calc(env(safe-area-inset-bottom) + 24rpx);
  max-height: 85vh;
  overflow-y: auto;
}

.slide-up {
  animation: slideUp 0.25s ease-out both;
}

@keyframes slideUp {
  from { transform: translateY(100%); }
  to { transform: translateY(0); }
}

// ─── 标题 ───
.dialog-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 28rpx;
}

.dialog-title {
  font-size: $font-size-lg;
  font-weight: 700;
  color: $text-primary;
}

.dialog-close {
  font-size: 36rpx;
  color: $text-hint;
  padding: 8rpx 16rpx;
}

// ─── 订单摘要 ───
.order-summary {
  margin-bottom: 24rpx;
}

.summary-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12rpx 0;
}

.summary-label {
  font-size: $font-size-sm;
  color: $text-hint;
}

.summary-value {
  font-size: $font-size-sm;
  color: $text-primary;

  &.bold {
    font-weight: 700;
  }
  &.pay {
    color: #EF5350;
  }
  &.recv {
    color: #26A69A;
  }
}

.side-tag {
  padding: 4rpx 16rpx;
  border-radius: 6rpx;
  font-size: $font-size-xs;
  font-weight: 700;

  &.buy {
    background: rgba(239, 83, 80, 0.1);
    color: #EF5350;
  }
  &.sell {
    background: rgba(38, 166, 154, 0.1);
    color: #26A69A;
  }
}

.divider {
  height: 1rpx;
  background: $border-color;
  margin: 8rpx 0;
}

.summary-row.total {
  .summary-label,
  .summary-value {
    font-size: $font-size-base;
    color: $text-primary;
  }
}

// ─── T+1 提示 ───
.rule-alert {
  display: flex;
  align-items: flex-start;
  gap: 12rpx;
  background: rgba(255, 193, 7, 0.1);
  border-radius: 8rpx;
  padding: 16rpx 20rpx;
  margin-bottom: 20rpx;
}

.rule-icon {
  font-size: 32rpx;
  flex-shrink: 0;
  margin-top: 2rpx;
}

.rule-text {
  font-size: $font-size-sm;
  color: #F57F17;
  line-height: 1.6;
}

// ─── 大额提示 ───
.large-warn {
  display: flex;
  align-items: flex-start;
  gap: 12rpx;
  background: rgba(244, 67, 54, 0.08);
  border-radius: 8rpx;
  padding: 16rpx 20rpx;
  margin-bottom: 20rpx;
}

.large-icon {
  font-size: 32rpx;
  flex-shrink: 0;
}

.large-text {
  font-size: $font-size-sm;
  color: $color-danger;
  line-height: 1.6;
}

// ─── 操作按钮 ───
.dialog-actions {
  display: flex;
  gap: 20rpx;
  margin-top: 8rpx;
}

.btn-cancel {
  flex: 1;
  padding: 22rpx 0;
  font-size: $font-size-base;
  color: $text-secondary;
  background: rgba(0, 0, 0, 0.04);
  border-radius: 12rpx;
  border: none;
  text-align: center;

  &::after { border: none; }
}

.btn-submit {
  flex: 1.5;
  padding: 22rpx 0;
  font-size: $font-size-base;
  font-weight: 700;
  color: #fff;
  border-radius: 12rpx;
  border: none;
  text-align: center;

  &.buy {
    background: linear-gradient(135deg, #EF5350, #E53935);
  }
  &.sell {
    background: linear-gradient(135deg, #26A69A, #00897B);
  }

  &::after { border: none; }
}
</style>
