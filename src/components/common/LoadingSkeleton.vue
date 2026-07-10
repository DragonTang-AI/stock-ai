<template>
  <!-- 通用加载骨架屏包装器，根据场景自动选择合适的骨架类型 -->
  <view class="loading-skeleton" :class="{ 'skeleton-exit': !loading && animated }">
    <!-- 行情页骨架 -->
    <template v-if="scene === 'market'">
      <view class="market-skeleton">
        <view class="skeleton-index-bar">
          <view class="skeleton-index-item" v-for="i in 3" :key="'idx'+i">
            <view class="sk-block sk-text-sm"></view>
            <view class="sk-block sk-text-lg"></view>
          </view>
        </view>
        <view class="skeleton-list">
          <view v-for="i in rows" :key="'row'+i" class="skeleton-stock-row">
            <view class="sk-block sk-avatar-sm"></view>
            <view class="skeleton-row-content">
              <view class="skeleton-row-top">
                <view class="sk-block sk-text" style="width:40%"></view>
                <view class="sk-block sk-text-sm" style="width:20%"></view>
              </view>
              <view class="skeleton-row-bottom">
                <view class="sk-block sk-text-sm" style="width:25%"></view>
                <view class="sk-block sk-text-sm" style="width:18%"></view>
              </view>
            </view>
          </view>
        </view>
      </view>
    </template>

    <!-- 持仓页骨架 -->
    <template v-else-if="scene === 'portfolio'">
      <view class="portfolio-skeleton">
        <view class="sk-block sk-card" style="height:180rpx"></view>
        <view class="sk-block sk-card" style="height:140rpx; margin-top:24rpx"></view>
        <SkeletonScreen type="list" :count="rows" />
      </view>
    </template>

    <!-- 选股页骨架 -->
    <template v-else-if="scene === 'selection'">
      <view class="selection-skeleton">
        <view v-for="i in 3" :key="'card'+i" class="sk-selection-card">
          <view class="sk-selection-header">
            <view>
              <view class="sk-block sk-text" style="width:120rpx"></view>
              <view class="sk-block sk-text-sm" style="width:80rpx"></view>
            </view>
            <view class="sk-block sk-badge"></view>
          </view>
          <view class="sk-block sk-text-m" style="width:90%; margin-top:16rpx"></view>
          <view class="sk-signal-row" v-for="j in 2" :key="'sig'+j">
            <view class="sk-block sk-text-sm" style="width:60rpx"></view>
            <view class="sk-block sk-text-sm" style="width:120rpx"></view>
          </view>
        </view>
      </view>
    </template>

    <!-- 看板页骨架 -->
    <template v-else-if="scene === 'dashboard'">
      <view class="dashboard-skeleton">
        <view class="skeleton-summary-grid">
          <view class="sk-block sk-summary-item" v-for="i in 4" :key="'sum'+i">
            <view class="sk-block sk-text-lg"></view>
            <view class="sk-block sk-text-sm" style="width:60%"></view>
          </view>
        </view>
        <view class="sk-block sk-card" style="height:300rpx; margin-top:24rpx"></view>
        <view class="sk-block sk-card" style="height:240rpx; margin-top:24rpx"></view>
        <SkeletonScreen type="table" :count="rows" />
      </view>
    </template>

    <!-- AI托管页骨架 -->
    <template v-else-if="scene === 'hosted'">
      <view class="hosted-skeleton">
        <view class="sk-block sk-card" style="height:200rpx"></view>
        <view class="sk-block sk-card" style="height:160rpx; margin-top:24rpx"></view>
        <SkeletonScreen type="card" :count="2" />
      </view>
    </template>

    <!-- 默认骨架 -->
    <template v-else>
      <SkeletonScreen :type="fallbackType" :count="rows" />
    </template>
  </view>
</template>

<script setup lang="ts">
import SkeletonScreen from './SkeletonScreen.vue'

withDefaults(defineProps<{
  loading?: boolean
  scene?: 'market' | 'portfolio' | 'selection' | 'dashboard' | 'hosted' | 'default'
  rows?: number
  animated?: boolean
  fallbackType?: 'list' | 'card' | 'detail' | 'table'
}>(), {
  loading: true,
  scene: 'default',
  rows: 4,
  animated: true,
  fallbackType: 'list',
})
</script>

<style lang="scss">
.loading-skeleton {
  padding: 24rpx;
}

.skeleton-exit {
  animation: sk-fade-out 0.25s ease-out both;
}

@keyframes sk-fade-out {
  to { opacity: 0; transform: translateY(-8rpx); }
}

.sk-block {
  background: linear-gradient(90deg, rgba(0,0,0,0.06) 25%, rgba(0,0,0,0.10) 50%, rgba(0,0,0,0.06) 75%);
  background-size: 200% 100%;
  animation: sk-shimmer 1.5s ease-in-out infinite;
  border-radius: 8rpx;
}

@keyframes sk-shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

.sk-text-sm { height: 22rpx; margin-bottom: 12rpx; }
.sk-text { height: 28rpx; margin-bottom: 14rpx; }
.sk-text-m { height: 36rpx; margin-bottom: 16rpx; }
.sk-text-lg { height: 48rpx; margin-bottom: 18rpx; }
.sk-card { border-radius: 16rpx; }
.sk-avatar-sm { width: 72rpx; height: 72rpx; border-radius: 50%; flex-shrink: 0; }
.sk-badge { width: 80rpx; height: 32rpx; border-radius: 16rpx; }
.sk-summary-item { padding: 28rpx; border-radius: 16rpx; text-align: center; }

.skeleton-index-bar {
  display: flex; gap: 16rpx; padding: 20rpx 0; margin-bottom: 24rpx;
}
.skeleton-index-item {
  flex: 1; padding: 20rpx; border-radius: 12rpx; text-align: center;
}
.skeleton-stock-row {
  display: flex; align-items: center; padding: 24rpx 0; gap: 20rpx;
  border-bottom: 1rpx solid rgba(0,0,0,0.04);
}
.skeleton-row-content { flex: 1; min-width: 0; }
.skeleton-row-top, .skeleton-row-bottom {
  display: flex; justify-content: space-between; align-items: center;
}
.skeleton-row-bottom { margin-top: 8rpx; }

.sk-selection-card {
  padding: 28rpx; background: var(--bg-card, #fff); border-radius: 16rpx;
  margin-bottom: 20rpx; box-shadow: var(--shadow-card, 0 2rpx 16rpx rgba(0,0,0,0.06));
}
.sk-selection-header { display: flex; justify-content: space-between; align-items: flex-start; }
.sk-signal-row { display: flex; gap: 16rpx; margin-top: 14rpx; align-items: center; }

.skeleton-summary-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16rpx; }
</style>
