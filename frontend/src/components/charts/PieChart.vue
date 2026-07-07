<template>
  <view class="pie-chart-wrapper">
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
    <view class="pie-legend" v-if="data.length">
      <view class="legend-row" v-for="(item, idx) in data" :key="item.name">
        <view class="legend-marker" :style="{ background: colorPalette[idx % colorPalette.length] }"></view>
        <text class="legend-name">{{ item.name }}</text>
        <text class="legend-value">{{ item.value }}</text>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'

// #ifdef H5
import * as echarts from 'echarts/core'
import { PieChart } from 'echarts/charts'
import { TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
echarts.use([PieChart, TooltipComponent, LegendComponent, CanvasRenderer])
// #endif

import { getThemeState, onThemeChange } from '@/utils/theme'
import { getChartColors } from '@/utils/chart-theme'

export interface PieDataItem {
  name: string
  value: number
}

const props = withDefaults(defineProps<{
  data: PieDataItem[]
  height?: string
  showPercent?: boolean
  title?: string
}>(), {
  height: '360rpx',
  showPercent: true,
})

const colorPalette = [
  '#4A90E2', '#F5A623', '#34C759', '#E25C5C', '#8B5CF6',
  '#EC4899', '#06B6D4', '#F97316', '#84CC16', '#6366F1',
]

const chartRef = ref<HTMLElement | null>(null)
const isDark = ref(getThemeState().isDark)
let chartInstance: any = null
let unsubscribeTheme: (() => void) | null = null

function buildOption() {
  const colors = getChartColors(isDark.value)
  const pieData = props.data.map((d, i) => ({
    name: d.name,
    value: d.value,
    itemStyle: { color: colorPalette[i % colorPalette.length] },
  }))

  return {
    tooltip: {
      trigger: 'item',
      formatter: props.showPercent ? '{b}: {c} ({d}%)' : '{b}: {c}',
      backgroundColor: colors.tooltipBg,
      borderColor: colors.tooltipBorder,
      textStyle: { fontSize: 11, color: colors.tooltipTextColor },
    },
    legend: { show: false },
    series: [
      {
        type: 'pie',
        radius: ['50%', '78%'],
        center: ['50%', '48%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 4,
          borderColor: colors.pieBorderColor,
          borderWidth: 2,
        },
        label: {
          show: true,
          position: 'outside',
          formatter: props.showPercent ? '{b}\n{d}%' : '{b}',
          fontSize: 10,
          color: colors.labelColor,
        },
        emphasis: {
          label: { fontSize: 14, fontWeight: 'bold' },
          scaleSize: 8,
        },
        data: pieData,
      },
    ],
  }
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
.pie-chart-wrapper { width: 100%; }
.chart-canvas { width: 100%; }
.pie-legend { display: flex; flex-wrap: wrap; gap: 12rpx; padding: 16rpx 0 0; justify-content: center; }
.legend-row { display: flex; align-items: center; gap: 6rpx; }
.legend-marker { width: 16rpx; height: 16rpx; border-radius: 4rpx; flex-shrink: 0; }
.legend-name { font-size: 22rpx; color: var(--text-secondary, #666); }
.legend-value { font-size: 22rpx; color: var(--text-primary, #333); font-weight: 600; }
.chart-fallback { display: flex; align-items: center; justify-content: center; background: var(--bg-input, #f8f9fc); border-radius: 12rpx; }
.fallback-placeholder { text-align: center; }
.fallback-text { font-size: 24rpx; color: var(--text-hint, #ccc); }
</style>
