<template>
  <view class="watchlist-page">
    <!-- 骨架屏 -->
    <LoadingSkeleton v-if="loading" scene="list" :rows="4" />

    <!-- 列表 -->
    <view v-else class="watchlist-content">
      <!-- 空状态 -->
      <EmptyState
        v-if="stocks.length === 0"
        message="暂无自选股"
        hint="在行情页点击添加自选"
        @action="goMarket"
      />

      <!-- 自选列表 -->
      <view v-else class="stock-list">
        <view
          v-for="stock in stocks"
          :key="stock.code"
          class="stock-item"
          @click="goDetail(stock.code)"
        >
          <view class="stock-left">
            <text class="stock-name">{{ stock.name }}</text>
            <text class="stock-code">{{ stock.code }}</text>
          </view>
          <view class="stock-right">
            <text class="stock-price">{{ stock.price }}</text>
            <text
              class="stock-change"
              :class="stock.change >= 0 ? 'up' : 'down'"
            >
              {{ stock.change >= 0 ? '+' : '' }}{{ stock.change }}%
            </text>
          </view>
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

interface WatchStock {
  code: string
  name: string
  price: string
  change: number
}

const loading = ref(true)
const stocks = ref<WatchStock[]>([])

async function fetchWatchlist() {
  loading.value = true
  try {
    // TODO: 对接自选股 API
    stocks.value = []
  } catch {
    // 忽略错误
  } finally {
    loading.value = false
  }
}

function goDetail(code: string) {
  uni.navigateTo({ url: `/pages/detail/index?code=${code}` })
}

function goMarket() {
  uni.switchTab({ url: '/pages/market/index' })
}

onMounted(() => {
  fetchWatchlist()
})
</script>

<style scoped lang="scss">
.watchlist-page {
  min-height: 100vh;
  background: var(--bg-page, #f5f5f7);
}

.watchlist-content {
  padding: 24rpx;
}

.stock-list {
  background: #fff;
  border-radius: 16rpx;
  overflow: hidden;
}

.stock-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 28rpx 24rpx;
  border-bottom: 1rpx solid var(--border-color, #f0f0f0);

  &:last-child { border-bottom: none; }
}

.stock-left {
  display: flex;
  flex-direction: column;
}

.stock-name {
  font-size: 30rpx;
  font-weight: 500;
  color: var(--text-primary, #333);
}

.stock-code {
  font-size: 22rpx;
  color: var(--text-hint, #999);
  margin-top: 4rpx;
}

.stock-right {
  text-align: right;
}

.stock-price {
  font-size: 30rpx;
  font-weight: 600;
  color: var(--text-primary, #333);
  display: block;
}

.stock-change {
  font-size: 24rpx;
  margin-top: 4rpx;
  display: block;

  &.up { color: #f5222d; }
  &.down { color: #52c41a; }
}
</style>
