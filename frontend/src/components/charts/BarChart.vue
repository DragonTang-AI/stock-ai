<template>
  <view class="bar-chart-wrapper">
    <!-- #ifdef H5 -->
    <view ref="chartRef" class="chart-canvas" :style="{ height: height }"></view>
    <!-- #endif -->
    <!-- #ifndef H5 -->
    <view class="chart-fallback" :style="{ height: height }">
      <view class="fallback-placeholder">
        <text class="fallback-text">图表需在 H5 环境下查看</text>
      </view>
    </view>
    <!-- #endif -->
  </view>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'

// #ifdef H5
import * as echarts from 'echarts/core'
import { BarChart } from 'echarts/charts'
import { TooltipComponent, GridComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
echarts.use([BarChart, TooltipComponent, GridComponent, CanvasRenderer])
// #endif

import { getThemeState, onThemeChange } from '@/utils/theme'
import { getChartColors } from '@/utils/chart-theme'

export interface BarDataItem {
  label: string
  value: number
  percentage?: number
  color?: string
}

const props = withDefaults(defineProps<{
  data: BarDataItem[]
  height?: string
  positiveColor?: string
  negativeColor?: string
  horizontal?: boolean
  labelMaxWidth?: number
}>(), {
  height: '400rpx',
  positiveColor: '#34C759',
  negativeColor: '#E25C5C',
  horizontal: true,
  labelMaxWidth: 120,
})

const chartRef = ref<HTMLElement | null>(null)
const isDark = ref(getThemeState().isDark)
let chartInstance: any = null
let unsubscribeTheme: (() => void) | null = null

function buildOption() {
  const colors = getChartColors(isDark.value)
  const labels = props.data.map(d => d.label)
  const values = props.data.map(d => d.value)
  const barColors = props.data.map(d => {
    if (d.color) return d.color
    return d.value >= 0 ? props.positiveColor : props.negativeColor
  })

  const isHorizontal = props.horizontal

  const baseOption: any = {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      backgroundColor: colors.tooltipBg,
      borderColor: colors.tooltipBorder,
      textStyle: { fontSize: 11, color: colors.tooltipTextColor },
      formatter(params: any) {
        const p = Array.isArray(params) ? params[0] : params
        const item = props.data[p.dataIndex]
        const pct = item?.percentage !== undefined ? ` (${item.percentage > 0 ? '+' : ''}${item.percentage.toFixed(2)}%)` : ''
        return `${p.name}: ${p.value > 0 ? '+' : ''}${p.value.toLocaleString()}${pct}`
      },
    },
    grid: isHorizontal
      ? { left: props.labelMaxWidth, right: 60, top: 8, bottom: 8 }
      : { left: 12, right: 12, top: 24, bottom: props.labelMaxWidth },
    series: [
      {
        type: 'bar',
        data: values.map((v, i) => ({
          value: v,
          itemStyle: { color: barColors[i], borderRadius: [0, 4, 4, 0] },
        })),
        barWidth: '60%',
        label: {
          show: true,
          position: isHorizontal ? 'right' : 'top',
          fontSize: 10,
          color: colors.labelColor,
          formatter(params: any) {
            const item = props.data[params.dataIndex]
            return item?.percentage !== undefined
              ? `${item.percentage > 0 ? '+' : ''}${item.percentage.toFixed(2)}%`
              : `${params.value > 0 ? '+' : ''}${params.value.toLocaleString()}`
          },
        },
      },
    ],
  }

  if (isHorizontal) {
    baseOption.xAxis = {
      type: 'value',
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { lineStyle: { color: colors.gridColor } },
      axisLabel: { fontSize: 10, color: colors.axisLabelColor },
    }
    baseOption.yAxis = {
      type: 'category',
      data: labels,
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: {
        fontSize: 11,
        color: colors.tooltipTextColor,
        width: props.labelMaxWidth,
        overflow: 'truncate',
      },
      inverse: true,
    }
  } else {
    baseOption.xAxis = {
      type: 'category',
      data: labels,
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: {
        fontSize: 10,
        color: colors.tooltipTextColor,
        rotate: labels.length > 5 ? 30 : 0,
      },
    }
    baseOption.yAxis = {
      type: 'value',
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { lineStyle: { color: colors.gridColor } },
      axisLabel: { fontSize: 10, color: colors.axisLabelColor },
    }
  }

  return baseOption
}

function initChart() {
  // #ifdef H5
  if (!chartRef.value || !props.data.length) return
  if (chartInstance) chartInstance.dispose()
  chartInstance = echarts.init(chartRef.value)
  chartInstance.setOption(buildOption())
  const handleResize = () => chartInstance?.resize()
  window.addEventListener('resize', handleResize)
  ;(chartInstance as any).__resizeHandler = handleResize
  // #endif
}

function updateChart() {
  // #ifdef H5
  if (!chartInstance) { initChart(); return }
  chartInstance.setOption(buildOption(), true)
  // #endif
}

onMounted(() => {
  nextTick(() => initChart())
  // #ifdef H5
  unsubscribeTheme = onThemeChange((dark: boolean) => { isDark.value = dark; nextTick(() => updateChart()) })
  // #endif
})

onBeforeUnmount(() => {
  // #ifdef H5
  unsubscribeTheme?.()
  if (chartInstance) {
    const handler = (chartInstance as any).__resizeHandler
    if (handler) window.removeEventListener('resize', handler)
    chartInstance.dispose()
    chartInstance = null
  }
  // #endif
})

watch(
  () => props.data,
  () => nextTick(() => updateChart()),
  { deep: true }
)
</script>

<style scoped lang="scss">
.bar-chart-wrapper { width: 100%; }
.chart-canvas { width: 100%; }
.chart-fallback { display: flex; align-items: center; justify-content: center; background: var(--bg-input, #f8f9fc); border-radius: 12rpx; }
.fallback-placeholder { text-align: center; }
.fallback-text { font-size: 24rpx; color: var(--text-hint, #ccc); }
</style>
