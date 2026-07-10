<template>
  <view v-if="isAuditMode" class="audit-badge" @click="onTap">
    <text class="audit-badge-text">审核模式</text>
  </view>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useComplianceStore } from '@/stores/compliance'

const complianceStore = useComplianceStore()
const isAuditMode = computed(() => complianceStore.isAuditMode)

function onTap() {
  uni.showToast({
    title: '当前为审核模式，部分功能受限',
    icon: 'none',
    duration: 2000,
  })
}
</script>

<style scoped lang="scss">
.audit-badge {
  position: fixed;
  top: 0;
  right: 0;
  z-index: 9999;
  background: #ff9500;
  padding: 4rpx 16rpx;
  border-bottom-left-radius: 12rpx;
}

.audit-badge-text {
  font-size: 20rpx;
  color: #fff;
  font-weight: 500;
}
</style>
