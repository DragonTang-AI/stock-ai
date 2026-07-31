/**
 * 数字格式化工具函数
 * 统一项目中所有数字格式化，消除 toFixed 散乱调用
 */

/**
 * 格式化金额/数值，默认保留2位小数
 * 空值返回 '--'
 */
export function formatMoney(value: number | string | null | undefined, decimals = 2): string {
  if (value === null || value === undefined || value === '' || isNaN(Number(value))) return '--';
  return Number(value).toFixed(decimals);
}

/**
 * 格式化百分比，默认保留2位小数，带%号
 * 正数自动添加 + 号前缀，负数自带 - 号
 */
export function formatPercent(value: number | string | null | undefined, decimals = 2): string {
  if (value === null || value === undefined || value === '' || isNaN(Number(value))) return '--%';
  const num = Number(value);
  const sign = num >= 0 ? '+' : '';
  return sign + num.toFixed(decimals) + '%';
}

/**
 * 带符号的数值格式化（不含 % 后缀）
 * 如 +12.34 / -5.67，用于涨跌幅显示
 */
export function formatSigned(value: number | string | null | undefined, decimals = 2): string {
  if (value === null || value === undefined || value === '' || isNaN(Number(value))) return '--';
  const num = Number(value);
  const sign = num >= 0 ? '+' : '';
  return sign + num.toFixed(decimals);
}
