// 市场标签映射：独立模块，避免 uni-app 模板编译器对字符串字面量的池化提取
export function decorateMarket(list: any[]): any[] {
  if (!Array.isArray(list)) return list
  return list.map(function (item: any) {
    const isHk = item.market === "HK"
    item.marketLabel = isHk ? "港股" : "A股"
    item.marketTag = isHk ? "tag-hk" : "tag-a"
    return item
  })
}
