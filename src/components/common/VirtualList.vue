<template>
  <scroll-view
    class="virtual-list"
    scroll-y
    :style="{ height: containerHeight + 'px' }"
    @scroll="handleScroll"
    :enhanced="true"
    :show-scrollbar="showScrollbar"
    :bounces="false"
    :scroll-with-animation="false"
    :enable-back-to-top="true"
    :lower-threshold="lowerThreshold"
    @scrolltolower="handleScrollToLower"
  >
    <!-- 占位撑开总高度 -->
    <view class="virtual-placeholder" :style="{ height: totalHeight + 'px' }">
      <!-- 可视区域列表项 -->
      <view
        class="virtual-visible"
        :style="{ transform: `translateY(${offsetY}px)` }"
      >
        <view
          v-for="(item, idx) in visibleItems"
          :key="getItemKey(item, startIndex + idx)"
        >
          <slot name="item" :item="item" :index="startIndex + idx" />
        </view>
      </view>
    </view>

    <!-- 空状态 -->
    <view v-if="!items || items.length === 0" class="virtual-empty">
      <slot name="empty">
        <text class="virtual-empty-text">暂无数据</text>
      </slot>
    </view>

    <!-- 加载更多指示器 -->
    <view v-if="loadingMore" class="virtual-loading">
      <text class="virtual-loading-text">加载中...</text>
    </view>
    <view v-else-if="hasMore === false && items && items.length > 0" class="virtual-loading">
      <text class="virtual-loading-text dim">已加载全部</text>
    </view>
  </scroll-view>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { throttle } from '@/utils/performance'

const props = withDefaults(defineProps<{
  /** 完整数据列表 */
  items: any[]
  /** 每项高度（px），必须固定 */
  itemHeight: number
  /** 容器高度（px），不传则自动计算占满剩余空间 */
  containerHeight?: number
  /** 上下缓冲区项数 */
  buffer?: number
  /** 是否还有更多数据 */
  hasMore?: boolean | null
  /** 是否正在加载更多 */
  loadingMore?: boolean
  /** 获取唯一 key 的函数 */
  getItemKey?: (item: any, index: number) => string | number
  /** 是否显示滚动条 */
  showScrollbar?: boolean
  /** 触发加载更多的距离阈值 */
  lowerThreshold?: number
}>(), {
  containerHeight: 0,
  buffer: 5,
  hasMore: null,
  loadingMore: false,
  getItemKey: (_item: any, index: number) => index,
  showScrollbar: false,
  lowerThreshold: 100,
})

const emit = defineEmits<{
  (e: 'scroll-to-lower'): void
}>()

const scrollTop = ref(0)
const viewportHeight = ref(props.containerHeight || 600)

// 可视范围
const startIndex = computed(() => {
  return Math.max(0, Math.floor(scrollTop.value / props.itemHeight) - props.buffer)
})

const endIndex = computed(() => {
  const visibleCount = Math.ceil(viewportHeight.value / props.itemHeight)
  return Math.min(props.items.length, startIndex.value + visibleCount + props.buffer * 2)
})

// 可见项
const visibleItems = computed(() => {
  return props.items.slice(startIndex.value, endIndex.value)
})

// 总高度
const totalHeight = computed(() => {
  return props.items.length * props.itemHeight
})

// 偏移量
const offsetY = computed(() => {
  return startIndex.value * props.itemHeight
})

const handleScroll = throttle((e: any) => {
  scrollTop.value = e.detail?.scrollTop ?? 0
}, 16) // ~60fps

const handleScrollToLower = () => {
  if (props.hasMore && !props.loadingMore) {
    emit('scroll-to-lower')
  }
}

// 自动计算容器高度
onMounted(() => {
  if (!props.containerHeight) {
    // #ifdef H5
    viewportHeight.value = window.innerHeight - 44 // 减去 navbar 高度
    // #endif
    // #ifndef H5
    const systemInfo = uni.getSystemInfoSync()
    viewportHeight.value = (systemInfo.windowHeight || 600) - 44
    // #endif
  }
})
</script>

<style lang="scss" scoped>
.virtual-list {
  width: 100%;
  position: relative;
}

.virtual-placeholder {
  position: relative;
  width: 100%;
}

.virtual-visible {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
}

.virtual-empty {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
}

.virtual-empty-text {
  font-size: $font-size-base;
  color: $text-hint;
}

.virtual-loading {
  display: flex;
  justify-content: center;
  padding: 24rpx 0;
}

.virtual-loading-text {
  font-size: $font-size-xs;
  color: $text-hint;

  &.dim {
    opacity: 0.4;
  }
}
</style>
