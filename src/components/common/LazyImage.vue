<template>
  <image
    v-if="loaded || !lazy"
    :src="src"
    :mode="mode"
    :class="['lazy-image', { 'lazy-loaded': loaded }]"
    @error="handleError"
    @load="handleLoad"
  />
  <view v-else class="lazy-image-placeholder">
    <view class="skeleton-block skeleton-placeholder"></view>
  </view>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'

const props = withDefaults(defineProps<{
  src: string
  mode?: string
  lazy?: boolean
  placeholder?: string
}>(), {
  mode: 'aspectFill',
  lazy: true,
})

const loaded = ref(false)
const error = ref(false)

function handleLoad() {
  loaded.value = true
}

function handleError() {
  error.value = true
  loaded.value = true
}

onMounted(() => {
  if (!props.lazy) {
    loaded.value = true
    return
  }
  // 使用 IntersectionObserver 实现懒加载
  // #ifdef H5
  const observer = new IntersectionObserver(
    (entries) => {
      if (entries[0].isIntersecting) {
        loaded.value = true
        observer.disconnect()
      }
    },
    { rootMargin: '100px' }
  )
  // 由于 uni-app H5 中无法直接获取 dom 引用，使用 window 预加载
  const img = new Image()
  img.onload = () => { loaded.value = true }
  img.onerror = () => { loaded.value = true; error.value = true }
  img.src = props.src
  // #endif
  // #ifndef H5
  loaded.value = true
  // #endif
})
</script>

<style lang="scss" scoped>
.lazy-image {
  width: 100%;
  height: 100%;
  opacity: 0;
  transition: opacity 0.3s ease;

  &.lazy-loaded {
    opacity: 1;
  }
}

.lazy-image-placeholder {
  width: 100%;
  height: 100%;
}

.skeleton-placeholder {
  width: 100%;
  height: 100%;
}
</style>
