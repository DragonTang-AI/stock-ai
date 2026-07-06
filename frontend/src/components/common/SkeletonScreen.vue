<template>
  <!-- 列表骨架屏 -->
  <view v-if="type === 'list'" class="skeleton-list">
    <view v-for="i in count" :key="i" class="skeleton-list-item">
      <view class="skeleton-block skeleton-avatar-sm"></view>
      <view class="skeleton-list-content">
        <view class="skeleton-block skeleton-text" style="width: 70%"></view>
        <view class="skeleton-block skeleton-text" style="width: 40%"></view>
      </view>
    </view>
  </view>

  <!-- 卡片骨架屏 -->
  <view v-else-if="type === 'card'" class="skeleton-card-wrap">
    <view v-for="i in count" :key="i" class="skeleton-block skeleton-card">
      <view class="skeleton-card-inner">
        <view class="skeleton-block skeleton-text" style="width: 50%"></view>
        <view class="skeleton-block skeleton-text" style="width: 30%"></view>
        <view class="skeleton-block skeleton-text-m" style="width: 80%; margin-top: 24rpx"></view>
      </view>
    </view>
  </view>

  <!-- 详情骨架屏 -->
  <view v-else-if="type === 'detail'" class="skeleton-detail">
    <view class="skeleton-block skeleton-text" style="width: 60%"></view>
    <view class="skeleton-block skeleton-text" style="width: 80%"></view>
    <view class="skeleton-block skeleton-text" style="width: 40%"></view>
    <view class="skeleton-block skeleton-text-m" style="width: 100%; margin-top: 32rpx"></view>
    <view class="skeleton-block skeleton-text" style="width: 90%"></view>
    <view class="skeleton-block skeleton-text" style="width: 70%"></view>
    <view class="skeleton-block skeleton-text" style="width: 50%"></view>
  </view>

  <!-- 表格骨架屏 -->
  <view v-else-if="type === 'table'" class="skeleton-table">
    <view v-for="i in count" :key="i" class="skeleton-table-row">
      <view class="skeleton-block skeleton-text" style="width: 25%"></view>
      <view class="skeleton-block skeleton-text" style="width: 20%"></view>
      <view class="skeleton-block skeleton-text" style="width: 20%"></view>
      <view class="skeleton-block skeleton-text" style="width: 15%"></view>
    </view>
  </view>
</template>

<script setup lang="ts">
withDefaults(defineProps<{
  type?: 'list' | 'card' | 'detail' | 'table'
  count?: number
}>(), {
  type: 'list',
  count: 3,
})
</script>

<style lang="scss" scoped>
.skeleton-list-item {
  display: flex;
  align-items: center;
  padding: 28rpx 32rpx;
  gap: 24rpx;
}

.skeleton-avatar-sm {
  width: 72rpx;
  height: 72rpx;
  border-radius: 50%;
  @include skeleton;
  flex-shrink: 0;
}

.skeleton-list-content {
  flex: 1;
  min-width: 0;
}

.skeleton-card-wrap {
  padding: 24rpx;
  display: flex;
  flex-direction: column;
  gap: 24rpx;
}

.skeleton-card-inner {
  padding: 28rpx;
}

.skeleton-text-m {
  height: 40rpx;
}

.skeleton-detail {
  padding: 32rpx;
}

.skeleton-table-row {
  display: flex;
  gap: 16rpx;
  padding: 24rpx 32rpx;
}
</style>
