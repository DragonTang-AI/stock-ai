<template>
  <text class="number-rolling" :class="colorClass" :style="{ fontFamily: fontFamily }">
    {{ displayValue }}
  </text>
</template>

<script setup lang="ts">
import { ref, watch, computed, onMounted } from 'vue'

const props = withDefaults(defineProps<{
  /** 目标值 */
  value: number
  /** 动画时长 ms */
  duration?: number
  /** 小数位 */
  precision?: number
  /** 千分位 */
  thousandth?: boolean
  /** 前缀 */
  prefix?: string
  /** 后缀 */
  suffix?: string
  /** 颜色规则：auto=根据正负自动着色, up=涨色, down=跌色, none=无 */
  colorRule?: 'auto' | 'up' | 'down' | 'none'
  /** 自定义字体 */
  fontFamily?: string
  /** 初始值（跳过动画） */
  immediate?: boolean
}>(), {
  value: 0,
  duration: 600,
  precision: 2,
  thousandth: false,
  prefix: '',
  suffix: '',
  colorRule: 'none',
  fontFamily: '',
  immediate: false,
})

const displayValue = ref('')

const colorClass = computed(() => {
  if (props.colorRule === 'none') return ''
  if (props.colorRule === 'up') return 'color-up'
  if (props.colorRule === 'down') return 'color-down'
  // auto
  if (props.value > 0) return 'color-up'
  if (props.value < 0) return 'color-down'
  return ''
})

function formatNumber(val: number): string {
  const fixed = val.toFixed(props.precision)
  if (!props.thousandth) return fixed

  const parts = fixed.split('.')
  const intPart = parts[0].replace(/^-?(\d+)/, (_, d) =>
    d.replace(/\B(?=(\d{3})+(?!\d))/g, ',')
  )
  return parts.length > 1 ? `${intPart}.${parts[1]}` : intPart
}

function buildDisplay(val: number): string {
  return `${props.prefix}${formatNumber(val)}${props.suffix}`
}

function animate(from: number, to: number) {
  if (from === to) {
    displayValue.value = buildDisplay(to)
    return
  }

  const startTime = performance.now()
  const diff = to - from

  function step(now: number) {
    const elapsed = now - startTime
    const progress = Math.min(elapsed / props.duration, 1)
    // easeOutCubic
    const eased = 1 - Math.pow(1 - progress, 3)
    const current = from + diff * eased
    displayValue.value = buildDisplay(current)

    if (progress < 1) {
      requestAnimationFrame(step)
    }
  }

  requestAnimationFrame(step)
}

let prevValue = props.value

watch(
  () => props.value,
  (newVal) => {
    animate(prevValue, newVal)
    prevValue = newVal
  }
)

onMounted(() => {
  if (props.immediate) {
    displayValue.value = buildDisplay(props.value)
    prevValue = props.value
  } else {
    animate(0, props.value)
  }
})
</script>

<style lang="scss" scoped>
.number-rolling {
  font-variant-numeric: tabular-nums;
  font-feature-settings: "tnum";
  letter-spacing: 0.02em;

  &.color-up {
    color: var(--color-up, #E25C5C);
  }

  &.color-down {
    color: var(--color-down, #34C759);
  }
}
</style>
