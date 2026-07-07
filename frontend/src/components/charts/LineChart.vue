<template>
  <view class="line-chart-wrapper">
    <view class="chart-header" v-if="periods && periods.length">
      <view class="period-tabs">
        <text
          v-for="p in periods"
          :key="p.value"
          class="period-tab"
          :class="{ active: modelValue === p.value }"
          @click="$emit('update:modelValue', p.value)"
        >{{ p.label }}</text>
      </view>
    </view>

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

    <view class="chart-legend" v-if="showLegend">
      <view class="legend-item">
        <view class="legend-dot" :style="{ background: lineColor }"></view>
        <text class="legend-label">{{ legendPrimary || '账户净值' }}</text>
      </view>
      <view class="legend-item" v-if="benchmarkData && benchmarkData.length">
        <view class="legend-dot" :style="{ background: benchmarkColor }"></view>
        <text class="legend-label">{{ legendSecondary || '基准' }}</text>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch, nextTick, computed } from 'vue'

// #ifdef H5
import * as echarts from 'echarts/core'
import { LineChart } from 'echarts/charts'
import {
  TitleComponent, TooltipComponent, GridComponent, LegendComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
echarts.use([LineChart, TitleComponent, TooltipComponent, GridComponent, LegendComponent, CanvasRenderer])
// #endif

import { getThemeState, onThemeChange } from '@/utils/theme'
import { getChartColors } from '@/utils/chart-theme'

const props = defineProps<{
  modelValue: string
  dates: string[]
  values: number[]
  benchmarkData?: number[]
  periods?: { label: string; value: string }[]
  height?: string
  showLegend?: boolean
  legendPrimary?: string
  legendSecondary?: string
  lineColor?: string
  areaColor?: string
  benchmarkColor?: string
  yAxisFormatter?: (v: number) => string
}>()

defineEmits<{
  'update:modelValue': [value: string]
}>()

const chartRef = ref<HTMLElement | null>(null)
const isDark = ref(getThemeState().isDark)
let chartInstance: any = null
let unsubscribeTheme: (() => void) | null = null

const lineColor = computed(() => props.lineColor || (isDark.value ? '#6DB3F8' : '#4A90E2'))
const benchmarkColor = computed(() => props.benchmarkColor || (isDark.value ? '#FFB340' : '#F5A623'))
const areaColorComp = computed(() => props.areaColor || (isDark.value ? 'rgba(109,179,248,0.15)' : 'rgba(74,144,226,0.1)'))

function buildOption() {
  const colors = getChartColors(isDark.value)

  const series: any[] = [
    {
      name: props.legendPrimary || '账户净值',
      type: 'line',
      data: props.values,
      smooth: true,
      symbol: 'none',
      lineStyle: { color: lineColor.value, width: 2 },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: areaColorComp.value },
          { offset: 1, color: 'rgba(74,144,226,0.02)' },
        ]),
      },
    },
  ]

  if (props.benchmarkData && props.benchmarkData.length) {
    series.push({
      name: props.legendSecondary || '基准',
      type: 'line',
      data: props.benchmarkData,
      smooth: true,
      symbol: 'none',
      lineStyle: { color: benchmarkColor.value, width: 1.5, type: 'dashed' },
    })
  }

  return {
    grid: { left: 12, right: 12, top: 12, bottom: 24 },
    xAxis: {
      type: 'category',
      data: props.dates,
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { fontSize: 10, color: colors.axisLabelColor },
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: colors.gridColor } },
      axisLabel: { fontSize: 10, color: colors.axisLabelColor, formatter: props.yAxisFormatter },
      scale: true,
    },
    tooltip: {
      trigger: 'axis',
      backgroundColor: colors.tooltipBg,
      borderColor: colors.tooltipBorder,
      textStyle: { fontSize: 11, color: colors.tooltipTextColor },
    },
    series,
  }
}

function initChart() {
  // #ifdef H5
  if (!chartRef.value) return
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
  () => [props.dates, props.values, props.benchmarkData],
  () => nextTick(() => updateChart()),
  { deep: true }
)
</script>

<style scoped lang="scss">
.line-chart-wrapper { width: 100%; }
.chart-header { display: flex; justify-content: flex-end; margin-bottom: 8rpx; }
.period-tabs { display: flex; gap: 8rpx; }
.period-tab {
  font-size: 22rpx; color: var(--text-hint, #999); padding: 6rpx 16rpx;
  border-radius: 20rpx; background: var(--bg-input, #f5f6fa); cursor: pointer;
  &.active { color: #fff; background: var(--color-primary, #4A90E2); }
}
.chart-canvas { width: 100%; }
.chart-legend { display: flex; justify-content: center; gap: 32rpx; padding: 12rpx 0 0; }
.legend-item { display: flex; align-items: center; gap: 8rpx; }
.legend-dot { width: 16rpx; height: 16rpx; border-radius: 50%; }
.legend-label { font-size: 22rpx; color: var(--text-secondary, #666); }
.chart-fallback { display: flex; align-items: center; justify-content: center; background: var(--bg-input, #f8f9fc); border-radius: 12rpx; }
.fallback-placeholder { text-align: center; }
.fallback-text { font-size: 24rpx; color: var(--text-hint, #ccc); }
</style>
