<template>
  <view class="disclaimer">
    <view class="disclaimer-divider"></view>
    <text class="disclaimer-text">免责声明：本平台所有内容仅供学习交流，不构成任何投资建议。股市有风险，投资需谨慎。过往业绩不代表未来表现，模拟交易结果不代表实盘收益。</text>
  </view>
</template>

<script setup lang="ts">
// 合规免责声明组件 —— 所有交易/分析页面底部统一使用
</script>

<style scoped lang="scss">
.disclaimer {
  padding: 32rpx 48rpx 48rpx;
  text-align: center;
}

.disclaimer-divider {
  width: 80rpx;
  height: 2rpx;
  background: var(--border-color, #e0e0e0);
  margin: 0 auto 20rpx;
}

.disclaimer-text {
  font-size: 20rpx;
  color: var(--text-hint, #bbb);
  line-height: 1.6;
}
</style>
