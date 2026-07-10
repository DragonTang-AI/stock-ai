/**
 * 交易错误码中文映射
 * 参照招商证券掌上交易等成熟 App 的交互设计
 */
const ERROR_MAP: Record<string, string> = {
  INSUFFICIENT_BALANCE: '可用资金不足，请充值或调整买入数量',
  NO_POSITION: '未持有该股票，无法卖出',
  INSUFFICIENT_AVAILABLE: '可卖数量不足，请检查持仓',
  INVALID_PRICE: '委托价格无效，请重新输入',
  ORDER_NOT_FOUND: '订单不存在或已失效',
  ORDER_NOT_CANCELLABLE: '该订单状态无法撤单（市价单已即时成交）',
  SYMBOL_NOT_FOUND: '未找到该股票行情，请稍后重试',
  QUOTE_FAILED: '行情获取失败，请检查网络后重试',
  VALIDATION_FAILED: '参数校验失败，请检查输入',
}

/**
 * 根据错误对象获取中文提示
 * @param err 错误对象（HttpError 或普通 Error）
 * @returns 中文错误提示
 */
export function getTradeErrorMessage(err: any): string {
  const code = err?.errorCode || ''
  if (code && ERROR_MAP[code]) {
    return ERROR_MAP[code]
  }
  // 兜底：后端 message 或通用提示
  return err?.message || err?.detail || '交易失败，请稍后重试'
}
