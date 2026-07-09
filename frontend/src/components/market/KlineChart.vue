<template>
  <view id="kline-chart-container" class="kline-chart">
    <view v-if="loading" class="chart-loading-overlay">
      <text class="chart-loading-text">加载中...</text>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
// #ifdef H5
import * as echarts from 'echarts/core'
import { CandlestickChart, BarChart, LineChart } from 'echarts/charts'
import {
  TitleComponent, TooltipComponent, GridComponent,
  DataZoomComponent, MarkLineComponent, LegendComponent,
} from 'echarts/components'
import { SVGRenderer } from 'echarts/renderers'
echarts.use([
  CandlestickChart, BarChart, LineChart,
  TitleComponent, TooltipComponent, GridComponent,
  DataZoomComponent, MarkLineComponent, LegendComponent,
  SVGRenderer,
])
// #endif

import type { KlinePoint } from '@/api/market'
import { throttle } from '@/utils/performance'
import { getThemeState, onThemeChange } from '@/utils/theme'
import { getChartColors } from '@/utils/chart-theme'

const props = defineProps<{
  points: KlinePoint[]
  loading?: boolean
  period?: string
}>()

const isDark = ref(getThemeState().isDark)
let chartInstance: any = null
let resizeObserver: any = null
let unsubscribeTheme: (() => void) | null = null

function toCandleData(points: KlinePoint[]) {
  return points.map(p => [p.open, p.close, p.low, p.high])
}

function toVolumeData(points: KlinePoint[], colors: ReturnType<typeof getChartColors>) {
  return points.map((p, i) => {
    const upColor = colors.klineUp
    const downColor = colors.klineDown
    const color = i > 0 ? (p.close >= points[i - 1].close ? upColor : downColor) : upColor
    return { value: p.volume, itemStyle: { color } }
  })
}

function toDates(points: KlinePoint[]) {
  return points.map(p => p.date)
}

function downsampleIfNeeded(points: KlinePoint[]): { sampled: KlinePoint[]; isSampled: boolean } {
  if (points.length <= 500) return { sampled: points, isSampled: false }
  const step = Math.ceil(points.length / 500)
  const sampled: KlinePoint[] = []
  for (let i = 0; i < points.length; i += step) {
    const slice = points.slice(i, Math.min(i + step, points.length))
    const aggregated: KlinePoint = {
      date: slice[0].date,
      open: slice[0].open,
      close: slice[slice.length - 1].close,
      high: Math.max(...slice.map(p => p.high)),
      low: Math.min(...slice.map(p => p.low)),
      volume: slice.reduce((sum, p) => sum + p.volume, 0),
      amount: slice.reduce((sum, p) => sum + p.amount, 0),
      change_pct: slice[slice.length - 1].change_pct,
    }
    sampled.push(aggregated)
  }
  return { sampled, isSampled: true }
}

function renderChart() {
  const nativeEl = document.getElementById("kline-chart-container")
  if (!nativeEl || !props.points?.length) return
  // #ifdef H5
  const colors = getChartColors(isDark.value)
  const { sampled } = downsampleIfNeeded(props.points)

  if (!chartInstance) {
    chartInstance = echarts.init(nativeEl, undefined, { renderer: 'svg' })
  }

  const dates = toDates(sampled)
  const candleData = toCandleData(sampled)
  const volData = toVolumeData(sampled, colors)

  chartInstance.setOption({
    animation: props.points.length > 200 ? false : true,
    animationDuration: props.points.length > 200 ? 0 : 300,
    progressive: props.points.length > 300 ? 200 : 0,
    progressiveThreshold: props.points.length > 300 ? 500 : 3000,
    grid: [
      { left: '3%', right: '3%', top: 8, height: '55%' },
      { left: '3%', right: '3%', top: '72%', height: '22%' },
    ],
    xAxis: [
      {
        type: 'category', data: dates, boundaryGap: true,
        axisLine: { onZero: false },
        axisLabel: { show: true, interval: Math.max(Math.floor(dates.length / 6), 1), fontSize: 10, color: colors.axisLabelColor },
        splitLine: { show: false },
        gridIndex: 0,
      },
      {
        type: 'category', data: dates, boundaryGap: true,
        axisLabel: { show: false },
        axisLine: { show: false }, axisTick: { show: false },
        splitLine: { show: false },
        gridIndex: 1,
      },
    ],
    yAxis: [
      {
        type: 'value', scale: true,
        splitLine: { lineStyle: { color: colors.gridColor, type: 'dashed' } },
        axisLabel: { fontSize: 10, color: colors.axisLabelColor },
        gridIndex: 0,
      },
      {
        type: 'value', scale: true,
        axisLabel: { show: false },
        splitLine: { show: false },
        gridIndex: 1,
      },
    ],
    series: [
      {
        name: 'K线', type: 'candlestick', data: candleData,
        xAxisIndex: 0, yAxisIndex: 0,
        itemStyle: {
          color: colors.klineUp,
          color0: colors.klineDown,
          borderColor: colors.klineUpBorder,
          borderColor0: colors.klineDownBorder,
        },
        large: props.points.length > 500,
        largeThreshold: 500,
      },
      {
        name: '成交量', type: 'bar', data: volData,
        xAxisIndex: 1, yAxisIndex: 1,
        barWidth: '60%',
        large: props.points.length > 500,
        largeThreshold: 500,
      },
    ],
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
      backgroundColor: colors.tooltipBg,
      borderColor: colors.tooltipBorder,
      textStyle: { color: colors.tooltipTextColor },
      formatter: (params: any[]) => {
        const kline = params.find((p: any) => p.seriesName === 'K线')
        const vol = params.find((p: any) => p.seriesName === '成交量')
        if (!kline) return ''
        const d = kline.data
        const date = kline.axisValue
        const volVal = vol ? (vol.data.value / 10000).toFixed(1) : ''
        return `${date}<br/>
          开: ${d[1]}  高: ${d[3]}<br/>
          收: ${d[2]}  低: ${d[4]}<br/>
          量: ${volVal}万手`
      },
    },
    dataZoom: [
      { type: 'inside', xAxisIndex: [0, 1], start: Math.max(0, dates.length > 50 ? 50 : 0), end: 100 },
    ],
  }, true)
  // #endif
}

const handleResize = throttle(() => { chartInstance?.resize() }, 150)

onMounted(() => {
  nextTick(() => {
    renderChart()
    // #ifdef H5
    const el = document.getElementById("kline-chart-container")
    if (el && (el as any).nodeType === 1 && typeof ResizeObserver !== 'undefined') {
      resizeObserver = new ResizeObserver(handleResize)
      resizeObserver.observe(el as Element)
    }
    // #endif
  })
  // #ifdef H5
  unsubscribeTheme = onThemeChange((dark: boolean) => { isDark.value = dark; nextTick(() => renderChart()) })
  // #endif
})

watch(() => props.points, () => { nextTick(() => renderChart()) }, { deep: true })

onBeforeUnmount(() => {
  // #ifdef H5
  unsubscribeTheme?.()
  // #endif
  resizeObserver?.disconnect()
  resizeObserver = null
  chartInstance?.dispose()
  chartInstance = null
})
</script>

<style lang="scss" scoped>
.kline-chart { width: 100%; position: relative; }
.chart-canvas { width: 100%; height: 600rpx; }
.chart-loading-overlay {
  position: absolute; top: 0; left: 0; right: 0; bottom: 0;
  display: flex; align-items: center; justify-content: center;
  background: var(--bg-mask, rgba(255, 255, 255, 0.6));
  z-index: 10;
}
.chart-loading-text { font-size: var(--font-size-sm, 24rpx); color: var(--text-hint, #999); }
</style>
