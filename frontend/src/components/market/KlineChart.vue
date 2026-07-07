<template>
  <view class="kline-chart">
    <view ref="chartContainer" class="chart-canvas"></view>
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
import { CanvasRenderer } from 'echarts/renderers'

echarts.use([
  CandlestickChart, BarChart, LineChart,
  TitleComponent, TooltipComponent, GridComponent,
  DataZoomComponent, MarkLineComponent, LegendComponent,
  CanvasRenderer,
])
// #endif

import type { KlinePoint } from '@/api/market'

const props = defineProps<{
  points: KlinePoint[]
  loading?: boolean
  period?: string
}>()

const chartContainer = ref<HTMLElement | null>(null)
let chartInstance: any = null

/** OHLC 转 ECharts candlestick 格式 [open, close, low, high] */
function toCandleData(points: KlinePoint[]) {
  return points.map(p => [p.open, p.close, p.low, p.high])
}

function toVolumeData(points: KlinePoint[]) {
  return points.map((p, i) => {
    const color = i > 0
      ? (p.close >= points[i - 1].close ? '#EF5350' : '#26A69A')
      : '#EF5350'
    return {
      value: p.volume,
      itemStyle: { color },
    }
  })
}

function toDates(points: KlinePoint[]) {
  return points.map(p => p.date)
}

function renderChart() {
  if (!chartContainer.value || !props.points?.length) return
  // #ifdef H5
  if (!chartInstance) {
    chartInstance = echarts.init(chartContainer.value as any)
  }

  const dates = toDates(props.points)
  const candleData = toCandleData(props.points)
  const volData = toVolumeData(props.points)

  chartInstance.setOption({
    animation: false,
    grid: [
      { left: '3%', right: '3%', top: 8, height: '55%' },
      { left: '3%', right: '3%', top: '72%', height: '22%' },
    ],
    xAxis: [
      {
        type: 'category',
        data: dates,
        boundaryGap: true,
        axisLine: { onZero: false },
        axisLabel: {
          show: true,
          interval: Math.max(Math.floor(dates.length / 6), 1),
          fontSize: 10,
        },
        splitLine: { show: false },
        gridIndex: 0,
      },
      {
        type: 'category',
        data: dates,
        boundaryGap: true,
        axisLabel: { show: false },
        axisLine: { show: false },
        axisTick: { show: false },
        splitLine: { show: false },
        gridIndex: 1,
      },
    ],
    yAxis: [
      {
        type: 'value',
        scale: true,
        splitLine: { lineStyle: { color: '#E5E5E5', type: 'dashed' } },
        axisLabel: { fontSize: 10 },
        gridIndex: 0,
      },
      {
        type: 'value',
        scale: true,
        axisLabel: { show: false },
        splitLine: { show: false },
        gridIndex: 1,
      },
    ],
    series: [
      {
        name: 'K线',
        type: 'candlestick',
        data: candleData,
        xAxisIndex: 0,
        yAxisIndex: 0,
        itemStyle: {
          color: '#EF5350',
          color0: '#26A69A',
          borderColor: '#EF5350',
          borderColor0: '#26A69A',
        },
      },
      {
        name: '成交量',
        type: 'bar',
        data: volData,
        xAxisIndex: 1,
        yAxisIndex: 1,
        barWidth: '60%',
      },
    ],
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
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
      {
        type: 'inside',
        xAxisIndex: [0, 1],
        start: Math.max(0, dates.length > 50 ? 50 : 0),
        end: 100,
      },
    ],
  }, true)
  // #endif
}

onMounted(() => {
  nextTick(() => renderChart())
})

watch(() => props.points, () => {
  nextTick(() => renderChart())
}, { deep: true })

onBeforeUnmount(() => {
  chartInstance?.dispose()
  chartInstance = null
})
</script>

<style lang="scss" scoped>
.kline-chart {
  width: 100%;
}

.chart-canvas {
  width: 100%;
  height: 600rpx;
}
</style>
