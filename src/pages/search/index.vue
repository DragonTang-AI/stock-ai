<template>
  <view class="search-page" @touchmove.prevent>
    <!-- 搜索栏 -->
    <view class="search-header">
      <view class="search-header-inner">
        <view class="search-input-box" :class="{ focused: isFocused }">
          <text class="search-input-icon">🔍</text>
          <input
            ref="inputRef"
            class="search-input"
            v-model="query"
            placeholder="搜索股票代码、名称或拼音"
            @input="onInput"
            @focus="isFocused = true"
            @confirm="onConfirm"
            :adjust-position="false"
            :focus="true"
          />
          <text v-if="query" class="search-clear-btn" @click="clearQuery">✕</text>
        </view>
        <text class="search-cancel" @click="goBack">取消</text>
      </view>
    </view>

    <!-- 默认状态：搜索历史 + 热门搜索 -->
    <view v-if="!query" class="search-default">
      <!-- 搜索历史 -->
      <view v-if="history.length > 0" class="section">
        <view class="section-header">
          <text class="section-title">搜索历史</text>
          <text class="section-action" @click="clearHistory">清空</text>
        </view>
        <view class="history-tags">
          <text
            v-for="(item, idx) in history"
            :key="idx"
            class="history-tag"
            @click="searchHistoryItem(item)"
          >{{ item }}</text>
        </view>
      </view>

      <!-- 热门搜索 -->
      <view class="section">
        <view class="section-header">
          <text class="section-title">热门搜索</text>
        </view>
        <view class="hot-list">
          <view
            v-for="(item, idx) in hotStocks"
            :key="item.symbol"
            class="hot-item"
            @click="selectStock(item)"
          >
            <text class="hot-rank" :class="idx < 3 ? 'hot' : ''">{{ idx + 1 }}</text>
            <view class="hot-info">
              <text class="hot-name">{{ item.name }}</text>
              <text class="hot-code">{{ item.code }}</text>
            </view>
            <text class="hot-price">{{ formatMoney(item.price, 2) }}</text>
            <text
              v-if="item.change_pct != null"
              class="hot-change"
              :class="item.change_pct >= 0 ? 'up' : 'down'"
            >{{ formatPercent(item.change_pct, 2) }}</text>
          </view>
        </view>
      </view>
    </view>

    <!-- 搜索中状态 -->
    <view v-if="query" class="search-results">
      <!-- 加载中 -->
      <view v-if="loading" class="result-state">
        <text class="result-state-text">搜索中...</text>
      </view>

      <!-- 有结果 -->
      <view v-else-if="results.length > 0" class="result-list">
        <view
          v-for="(item, idx) in results"
          :key="item.symbol"
          class="result-item"
          hover-class="result-item--hover"
          @click="selectStock(item)"
        >
          <view class="result-item-left">
            <text class="result-name">
              <template v-for="(seg, si) in highlightMatch(item.name, query)" :key="si">
                <text v-if="seg.highlight" class="result-highlight">{{ seg.text }}</text>
                <text v-else>{{ seg.text }}</text>
              </template>
            </text>
            <text class="result-code">{{ item.code }}</text>
          </view>
          <view class="result-item-right">
            <text class="result-price">{{ formatMoney(item.price, 2) }}</text>
            <text
              v-if="item.change_pct != null"
              class="result-change"
              :class="item.change_pct >= 0 ? 'up' : 'down'"
            >{{ formatPercent(item.change_pct, 2) }}</text>
          </view>
        </view>
      </view>

      <!-- 无结果 -->
      <view v-else-if="!loading && touched" class="result-state">
        <text class="result-state-text">未找到匹配结果</text>
        <text class="result-state-hint">试试其他关键词</text>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { searchStocks, type SearchResult } from '@/api/market'
import { fetchQuotes } from '@/api/market'
import { formatMoney, formatPercent } from '@/utils/format'

const HISTORY_KEY = 'ai-stock:search-history'
const MAX_HISTORY = 10

const query = ref('')
const isFocused = ref(true)
const loading = ref(false)
const touched = ref(false)
const results = ref<SearchResult[]>([])
const history = ref<string[]>([])
const hotStocks = ref<SearchResult[]>([])
const inputRef = ref<any>(null)
let searchTimer: ReturnType<typeof setTimeout> | null = null

// 加载搜索历史
function loadHistory() {
  try {
    const raw = uni.getStorageSync(HISTORY_KEY)
    if (raw) {
      const arr = typeof raw === 'string' ? JSON.parse(raw) : raw
      history.value = Array.isArray(arr) ? arr.slice(0, MAX_HISTORY) : []
    }
  } catch {
    history.value = []
  }
}

// 保存搜索历史
function saveHistory(keyword: string) {
  if (!keyword.trim()) return
  const arr = [keyword, ...history.value.filter(h => h !== keyword)].slice(0, MAX_HISTORY)
  history.value = arr
  uni.setStorageSync(HISTORY_KEY, JSON.stringify(arr))
}

// 清空搜索历史
function clearHistory() {
  history.value = []
  uni.removeStorageSync(HISTORY_KEY)
}

// 点击历史标签
function searchHistoryItem(keyword: string) {
  query.value = keyword
  touched.value = true
  doSearch(keyword)
}

// 输入事件
function onInput(e: any) {
  const val = e.detail?.value || e.target?.value || query.value || ''
  query.value = val
  touched.value = false
  if (searchTimer) clearTimeout(searchTimer)
  if (!val.trim()) {
    results.value = []
    loading.value = false
    return
  }
  loading.value = true
  searchTimer = setTimeout(() => doSearch(val.trim()), 300)
}

// 确认搜索
function onConfirm() {
  const val = query.value.trim()
  if (!val) return
  if (results.value.length > 0) {
    selectStock(results.value[0])
  } else {
    doSearch(val)
  }
}

// 执行搜索
async function doSearch(keyword: string) {
  if (!keyword.trim()) return
  loading.value = true
  touched.value = true
  try {
    results.value = await searchStocks(keyword, 20)
  } catch {
    results.value = []
  } finally {
    loading.value = false
  }
}

// 清空输入
function clearQuery() {
  query.value = ''
  results.value = []
  touched.value = false
  if (searchTimer) clearTimeout(searchTimer)
}

// 选中股票
function selectStock(item: SearchResult) {
  saveHistory(query.value || item.name)
  uni.navigateTo({ url: `/pages/detail/index?code=${item.symbol}` })
}

// 返回
function goBack() {
  uni.navigateBack()
}

// 高亮匹配
function highlightMatch(text: string, q: string): { text: string; highlight: boolean }[] {
  if (!q || !text) return [{ text: text || '', highlight: false }]
  const idx = text.toLowerCase().indexOf(q.toLowerCase())
  if (idx < 0) return [{ text, highlight: false }]
  return [
    { text: text.slice(0, idx), highlight: false },
    { text: text.slice(idx, idx + q.length), highlight: true },
    { text: text.slice(idx + q.length), highlight: false },
  ]
}

onMounted(async () => {
  loadHistory()
  // 加载热门股票（热门搜索）
  try {
    const quotes = await fetchQuotes()
    hotStocks.value = quotes.slice(0, 10).map(q => ({
      symbol: q.symbol,
      name: q.name,
      code: q.symbol,
      price: q.price,
      change_pct: q.change_pct,
    }))
  } catch {
    hotStocks.value = []
  }
})
</script>

<style scoped lang="scss">
.search-page {
  min-height: 100vh;
  background: var(--bg-page, #F5F5F7);
  display: flex;
  flex-direction: column;
}

/* ===== 搜索栏 ===== */
.search-header {
  padding: 16rpx 24rpx calc(16rpx + env(safe-area-inset-top));
  background: var(--bg-card, #FFFFFF);
  border-bottom: 1rpx solid var(--border-color, #E5E5EA);
  position: sticky;
  top: 0;
  z-index: 100;
}

.search-header-inner {
  display: flex;
  align-items: center;
  gap: 16rpx;
}

.search-input-box {
  flex: 1;
  display: flex;
  align-items: center;
  height: 72rpx;
  background: var(--bg-input, #F0F0F5);
  border-radius: 36rpx;
  padding: 0 28rpx;
  border: 2rpx solid transparent;
  transition: all 0.2s ease;

  &.focused {
    border-color: var(--color-primary, #4A90E2);
    background: var(--bg-card, #FFFFFF);
  }
}

.search-input-icon {
  font-size: 28rpx;
  margin-right: 12rpx;
  flex-shrink: 0;
  opacity: 0.6;
}

.search-input {
  flex: 1;
  font-size: 28rpx;
  color: var(--text-primary, #1F1F1F);
  height: 100%;
}

.search-clear-btn {
  font-size: 32rpx;
  color: var(--text-hint, #999);
  padding: 10rpx;
  flex-shrink: 0;
}

.search-cancel {
  font-size: 28rpx;
  color: var(--color-primary, #4A90E2);
  font-weight: 500;
  flex-shrink: 0;
  padding: 10rpx 0;
}

/* ===== 默认状态 ===== */
.search-default {
  flex: 1;
  overflow-y: auto;
  padding-bottom: 40rpx;
}

.section {
  padding: 28rpx 24rpx 0;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20rpx;
}

.section-title {
  font-size: 28rpx;
  font-weight: 700;
  color: var(--text-primary, #1F1F1F);
}

.section-action {
  font-size: 24rpx;
  color: var(--text-hint, #999);
  padding: 8rpx 16rpx;
  border-radius: 8rpx;
}

/* 历史标签 */
.history-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 16rpx;
}

.history-tag {
  padding: 12rpx 24rpx;
  font-size: 24rpx;
  color: var(--text-secondary, #666);
  background: var(--bg-input, #F0F0F5);
  border-radius: 8rpx;
  line-height: 1.4;
  transition: background 0.15s;
}

.history-tag:active {
  background: var(--border-color, #E5E5EA);
}

/* 热门搜索 */
.hot-list {
  display: flex;
  flex-direction: column;
}

.hot-item {
  display: flex;
  align-items: center;
  padding: 22rpx 0;
  border-bottom: 1rpx solid var(--border-color, #E5E5EA);
  min-height: 88rpx;
}

.hot-item:last-child {
  border-bottom: none;
}

.hot-rank {
  width: 44rpx;
  font-size: 26rpx;
  font-weight: 700;
  color: var(--text-hint, #999);
  text-align: center;
  flex-shrink: 0;

  &.hot {
    color: var(--color-primary, #4A90E2);
  }
}

.hot-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  margin-left: 16rpx;
  min-width: 0;
}

.hot-name {
  font-size: 28rpx;
  font-weight: 600;
  color: var(--text-primary, #1F1F1F);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.hot-code {
  font-size: 22rpx;
  color: var(--text-hint, #999);
  margin-top: 4rpx;
}

.hot-price {
  font-size: 28rpx;
  font-weight: 700;
  color: var(--text-primary, #1F1F1F);
  min-width: 120rpx;
  text-align: right;
  flex-shrink: 0;
}

.hot-change {
  font-size: 26rpx;
  font-weight: 700;
  min-width: 110rpx;
  text-align: right;
  margin-left: 16rpx;
  flex-shrink: 0;

  &.up   { color: var(--color-up, #E25C5C); }
  &.down { color: var(--color-down, #34C759); }
}

/* ===== 搜索结果 ===== */
.search-results {
  flex: 1;
  overflow-y: auto;
  padding: 0 24rpx;
}

.result-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 160rpx 0;
  gap: 12rpx;
}

.result-state-text {
  font-size: 28rpx;
  color: var(--text-hint, #999);
}

.result-state-hint {
  font-size: 24rpx;
  color: var(--text-hint, #999);
  opacity: 0.6;
}

.result-list {
  padding: 8rpx 0 40rpx;
}

.result-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 24rpx 0;
  border-bottom: 1rpx solid var(--border-color, #E5E5EA);
  transition: background 0.1s;
}

.result-item--hover {
  background: var(--bg-hover, rgba(0, 0, 0, 0.03));
}

.result-item-left {
  display: flex;
  flex-direction: column;
  gap: 4rpx;
  min-width: 0;
  flex: 1;
}

.result-name {
  font-size: 30rpx;
  font-weight: 600;
  color: var(--text-primary, #1F1F1F);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.result-highlight {
  color: var(--color-primary, #4A90E2);
  font-weight: 700;
}

.result-code {
  font-size: 22rpx;
  color: var(--text-hint, #999);
}

.result-item-right {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4rpx;
  flex-shrink: 0;
  margin-left: 24rpx;
}

.result-price {
  font-size: 30rpx;
  font-weight: 700;
  color: var(--text-primary, #1F1F1F);
}

.result-change {
  font-size: 26rpx;
  font-weight: 600;

  &.up   { color: var(--color-up, #E25C5C); }
  &.down { color: var(--color-down, #34C759); }
}
</style>