<template>
  <view class="empty-state">
    <view class="empty-icon">{{ icon }}</view>
    <text class="empty-title">{{ title }}</text>
    <text v-if="description" class="empty-desc">{{ description }}</text>
    <slot />
  </view>
</template>

<script setup lang="ts">
defineProps<{
  icon?: string
  title: string
  description?: string
}>()
</script>

<style lang="scss" scoped>
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 120rpx 48rpx;
}

.empty-icon {
  font-size: 80rpx;
  margin-bottom: 24rpx;
}

.empty-title {
  font-size: $font-size-base;
  font-weight: 600;
  color: $text-primary;
  margin-bottom: 8rpx;
}

.empty-desc {
  font-size: $font-size-sm;
  color: $text-hint;
  text-align: center;
  line-height: 1.6;
}
</style>
