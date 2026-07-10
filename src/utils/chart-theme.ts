/**
 * ECharts 主题颜色工具
 * 根据深色/浅色模式返回适配的图表配色
 */

export interface ChartThemeColors {
  /** 网格线颜色 */
  gridColor: string
  /** 轴标签颜色 */
  axisLabelColor: string
  /** 轴线条颜色 */
  axisLineColor: string
  /** Tooltip 背景色 */
  tooltipBg: string
  /** Tooltip 边框色 */
  tooltipBorder: string
  /** Tooltip 文字色 */
  tooltipTextColor: string
  /** 图表背景色 */
  backgroundColor: string
  /** 饼图边框色 */
  pieBorderColor: string
  /** 标签文字色 */
  labelColor: string
  /** K线 涨色 */
  klineUp: string
  /** K线 跌色 */
  klineDown: string
  /** K线 涨边框 */
  klineUpBorder: string
  /** K线 跌边框 */
  klineDownBorder: string
}

export function getChartColors(isDark: boolean): ChartThemeColors {
  if (isDark) {
    return {
      gridColor: '#2A2A3E',
      axisLabelColor: '#888888',
      axisLineColor: '#3A3A5C',
      tooltipBg: '#1E1E32',
      tooltipBorder: '#3A3A5C',
      tooltipTextColor: '#E0E0E0',
      backgroundColor: 'transparent',
      pieBorderColor: '#1A1A2E',
      labelColor: '#A0A0A0',
      klineUp: '#FF6961',
      klineDown: '#30D158',
      klineUpBorder: '#FF6961',
      klineDownBorder: '#30D158',
    }
  }
  return {
    gridColor: '#f0f0f0',
    axisLabelColor: '#ccc',
    axisLineColor: '#e0e0e0',
    tooltipBg: '#fff',
    tooltipBorder: '#e0e0e0',
    tooltipTextColor: '#333',
    backgroundColor: 'transparent',
    pieBorderColor: '#fff',
    labelColor: '#666',
    klineUp: '#EF5350',
    klineDown: '#26A69A',
    klineUpBorder: '#EF5350',
    klineDownBorder: '#26A69A',
  }
}
