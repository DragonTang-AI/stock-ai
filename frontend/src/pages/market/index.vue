<template>
  <view class="market-page">
    <!-- 骨架屏 -->
    <LoadingSkeleton v-if="loading" scene="list" :rows="5" />

    <!-- 错误状态 -->
    <ErrorPage
      v-else-if="error"
      :message="error"
      @retry="fetchMarketData"
    />

    <!-- 主要内容 -->
    <view v-else class="market-content">
      <!-- 大盘指数 -->
      <view class="index-section">
        <view class="section-title">大盘指数</view>
        <view class="index-cards">
          <view
            v-for="item in indices"
            :key="item.code"
            class="index-card"
            @click="goDetail(item.code)"
          >
            <text class="index-name">{{ item.name }}</text>
            <text class="index-price">{{ item.price }}</text>
            <text
              class="index-change"
              :class="item.change >= 0 ? 'up' : 'down'"
            >
              {{ item.change >= 0 ? '+' : '' }}{{ item.change }}%
            </text>
          </view>
        </view>
      </view>

      <!-- 热门股票列表 -->
      <view class="hot-section">
        <view class="section-title">热门股票</view>
        <view class="stock-list">
          <view
            v-for="stock in hotStocks"
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

      <!-- 空状态 -->
      <EmptyState v-if="!loading && hotStocks.length === 0" message="暂无行情数据" />
    </view>

    <Disclaimer />
  </view>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import LoadingSkeleton from '@/components/common/LoadingSkeleton.vue'
import ErrorPage from '@/components/common/ErrorPage.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import Disclaimer from '@/components/compliance/Disclaimer.vue'

interface StockItem {
  code: string
  name: string
  price: string
  change: number
}

const loading = ref(true)
const error = ref('')
const indices = ref<StockItem[]>([])
const hotStocks = ref<StockItem[]>([])

async function fetchMarketData() {
  loading.value = true
  error.value = ''
  try {
    // TODO: 对接行情 API
    // 使用占位数据
    indices.value = [
      { code: '000001', name: '上证指数', price: '--', change: 0 },
      { code: '399001', name: '深证成指', price: '--', change: 0 },
      { code: '399006', name: '创业板指', price: '--', change: 0 },
    ]
    hotStocks.value = []
  } catch (e: any) {
    error.value = e?.message || '加载失败'
  } finally {
    loading.value = false
  }
}

function goDetail(code: string) {
  uni.navigateTo({ url: `/pages/detail/index?code=${code}` })
}

onMounted(() => {
  fetchMarketData()
})
</script>

<style scoped lang="scss">
.market-page {
  min-height: 100vh;
  background: var(--bg-page, #f5f5f7);
}

.market-content {
  padding-bottom: 24rpx;
}

.index-section,
.hot-section {
  background: #fff;
  margin: 24rpx;
  border-radius: 16rpx;
  padding: 24rpx;
}

.section-title {
  font-size: 32rpx;
  font-weight: 600;
  color: var(--text-primary, #333);
  margin-bottom: 24rpx;
}

.index-cards {
  display: flex;
  gap: 16rpx;
}

.index-card {
  flex: 1;
  text-align: center;
  padding: 24rpx 12rpx;
  background: var(--bg-card, #f8f9fa);
  border-radius: 12rpx;
}

.index-name {
  display: block;
  font-size: 22rpx;
  color: var(--text-hint, #999);
  margin-bottom: 8rpx;
}

.index-price {
  display: block;
  font-size: 36rpx;
  font-weight: 700;
  color: var(--text-primary, #333);
  margin-bottom: 4rpx;
}

.index-change {
  font-size: 24rpx;

  &.up { color: #f5222d; }
  &.down { color: #52c41a; }
}

.stock-list {
  display: flex;
  flex-direction: column;
}

.stock-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 24rpx 0;
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
