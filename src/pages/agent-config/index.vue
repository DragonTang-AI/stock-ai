<template>
  <view class="agent-config-page">
    <!-- 步骤指示器 -->
    <view class="steps-bar">
      <view class="steps-track">
        <view
          v-for="(step, idx) in steps"
          :key="idx"
          :class="['step-dot', currentStep >= idx ? 'active' : '', currentStep > idx ? 'done' : '']"
        >
          <text class="step-num">{{ idx + 1 }}</text>
        </view>
        <view class="steps-line">
          <view class="steps-line-fill" :style="{ width: (currentStep / (steps.length - 1)) * 100 + '%' }"></view>
        </view>
      </view>
      <text class="steps-label">{{ steps[currentStep].title }}</text>
    </view>

    <!-- 加载态 -->
    <view v-if="loading" class="loading-box">
      <text class="loading-text">加载配置中...</text>
    </view>

    <!-- 配置表单区 -->
    <view v-else class="form-body">
      <!-- Step 0: 选择市场 -->
      <view v-show="currentStep === 0" class="step-section">
        <text class="step-desc">选择交易员参与的市场</text>
        <view class="market-grid">
          <view
            v-for="m in marketOptions"
            :key="m.value"
            :class="['market-card', config.markets.includes(m.value) ? 'selected' : '']"
            @click="toggleMarket(m.value)"
          >
            <text class="market-flag">{{ m.flag }}</text>
            <text class="market-name">{{ m.label }}</text>
          </view>
        </view>
      </view>

      <!-- Step 1: 分配资金 -->
      <view v-show="currentStep === 1" class="step-section">
        <text class="step-desc">设置分配给该交易员的初始资金</text>
        <view class="input-group">
          <text class="input-label">分配金额 (元)</text>
          <view class="input-wrapper">
            <text class="input-prefix">&yen;</text>
            <input
              class="input-field"
              type="digit"
              v-model="capitalInput"
              placeholder="请输入金额"
              @confirm="syncCapital"
            />
          </view>
          <view class="quick-amounts">
            <view
              v-for="amt in quickAmounts"
              :key="amt"
              :class="['quick-tag', config.allocated_capital === amt ? 'active' : '']"
              @click="config.allocated_capital = amt; capitalInput = String(amt)"
            >
              <text>{{ formatAmount(amt) }}</text>
            </view>
          </view>
        </view>
      </view>

      <!-- Step 2: 仓位控制 -->
      <view v-show="currentStep === 2" class="step-section">
        <text class="step-desc">控制单笔仓位风险</text>
        <view class="input-group">
          <text class="input-label">单股最大仓位 (%)</text>
          <view class="input-wrapper">
            <input
              class="input-field"
              type="digit"
              v-model.number="config.max_position_pct"
              placeholder="如 20"
            />
            <text class="input-suffix">%</text>
          </view>
        </view>
        <view class="input-group">
          <text class="input-label">最大持仓数量</text>
          <view class="input-wrapper">
            <input
              class="input-field"
              type="number"
              v-model.number="config.max_position_count"
              placeholder="如 5"
            />
            <text class="input-suffix">只</text>
          </view>
        </view>
      </view>

      <!-- Step 3: 风控设置 -->
      <view v-show="currentStep === 3" class="step-section">
        <text class="step-desc">设置风险控制参数</text>
        <view class="input-group">
          <text class="input-label">止损比例 (%)</text>
          <view class="input-wrapper">
            <input
              class="input-field"
              type="digit"
              v-model.number="config.loss_stop_pct"
              placeholder="如 5"
            />
            <text class="input-suffix">%</text>
          </view>
        </view>
        <view class="input-group">
          <text class="input-label">止损金额 (元)</text>
          <view class="input-wrapper">
            <text class="input-prefix">&yen;</text>
            <input
              class="input-field"
              type="digit"
              v-model.number="config.loss_stop_amount"
              placeholder="如 5000"
            />
          </view>
        </view>
        <view class="toggle-row">
          <text class="toggle-label">启用 T+1 保护</text>
          <switch
            :checked="config.t1_enabled"
            color="#4A90E2"
            @change="(e: any) => config.t1_enabled = e.detail.value"
          />
        </view>
      </view>

      <!-- Step 4: 自动执行 -->
      <view v-show="currentStep === 4" class="step-section">
        <text class="step-desc">配置自动执行参数</text>
        <view class="input-group">
          <text class="input-label">自动执行置信度阈值</text>
          <view class="slider-group">
            <text class="slider-val">{{ (config.auto_exec_confidence * 100).toFixed(0) }}%</text>
            <slider
              :value="config.auto_exec_confidence * 100"
              min="50"
              max="95"
              step="5"
              activeColor="#4A90E2"
              backgroundColor="rgba(255,255,255,0.08)"
              block-size="18"
              @change="(e: any) => config.auto_exec_confidence = e.detail.value / 100"
            />
          </view>
        </view>
        <view class="input-group">
          <text class="input-label">每轮最大自动执行次数</text>
          <view class="input-wrapper">
            <input
              class="input-field"
              type="number"
              v-model.number="config.max_auto_exec_per_round"
              placeholder="如 3"
            />
            <text class="input-suffix">次</text>
          </view>
        </view>
        <view class="input-group">
          <text class="input-label">信号间隔 (分钟)</text>
          <view class="input-wrapper">
            <input
              class="input-field"
              type="number"
              v-model.number="config.signal_interval_min"
              placeholder="如 30"
            />
            <text class="input-suffix">分钟</text>
          </view>
        </view>
      </view>

      <!-- Step 5: 交易风格 -->
      <view v-show="currentStep === 5" class="step-section">
        <text class="step-desc">选择交易风格偏好</text>
        <view class="style-list">
          <view
            v-for="style in tradingStyles"
            :key="style.value"
            :class="['style-card', config.trading_style === style.value ? 'selected' : '']"
            @click="config.trading_style = style.value"
          >
            <text class="style-icon">{{ style.icon }}</text>
            <view class="style-info">
              <text class="style-name">{{ style.label }}</text>
              <text class="style-detail">{{ style.desc }}</text>
            </view>
            <view v-if="config.trading_style === style.value" class="style-check">
              <text>&#x2713;</text>
            </view>
          </view>
        </view>
      </view>

      <!-- Step 6: 确认启用 -->
      <view v-show="currentStep === 6" class="step-section">
        <text class="step-desc">确认以下配置后启用交易员</text>
        <view class="summary-card">
          <view class="summary-row">
            <text class="summary-label">市场</text>
            <text class="summary-val">{{ config.markets.map(m => marketOptions.find(o => o.value === m)?.label).join('、') || '-' }}</text>
          </view>
          <view class="summary-row">
            <text class="summary-label">分配资金</text>
            <text class="summary-val">&yen;{{ (config.allocated_capital || 0).toLocaleString() }}</text>
          </view>
          <view class="summary-row">
            <text class="summary-label">单股最大仓位</text>
            <text class="summary-val">{{ config.max_position_pct ?? '-' }}%</text>
          </view>
          <view class="summary-row">
            <text class="summary-label">最大持仓数</text>
            <text class="summary-val">{{ config.max_position_count ?? '-' }}只</text>
          </view>
          <view class="summary-row">
            <text class="summary-label">止损比例</text>
            <text class="summary-val">{{ config.loss_stop_pct ?? '-' }}%</text>
          </view>
          <view class="summary-row">
            <text class="summary-label">止损金额</text>
            <text class="summary-val">&yen;{{ (config.loss_stop_amount || 0).toLocaleString() }}</text>
          </view>
          <view class="summary-row">
            <text class="summary-label">T+1 保护</text>
            <text class="summary-val">{{ config.t1_enabled ? '已启用' : '未启用' }}</text>
          </view>
          <view class="summary-row">
            <text class="summary-label">自动执行阈值</text>
            <text class="summary-val">{{ ((config.auto_exec_confidence || 0) * 100).toFixed(0) }}%</text>
          </view>
          <view class="summary-row">
            <text class="summary-label">每轮最大执行</text>
            <text class="summary-val">{{ config.max_auto_exec_per_round ?? '-' }}次</text>
          </view>
          <view class="summary-row">
            <text class="summary-label">信号间隔</text>
            <text class="summary-val">{{ config.signal_interval_min ?? '-' }}分钟</text>
          </view>
          <view class="summary-row">
            <text class="summary-label">交易风格</text>
            <text class="summary-val">{{ tradingStyles.find(s => s.value === config.trading_style)?.label || '-' }}</text>
          </view>
        </view>
      </view>
    </view>

    <!-- 底部导航 -->
    <view class="bottom-nav">
      <view v-if="currentStep > 0" class="nav-btn prev" @click="prevStep">
        <text>上一步</text>
      </view>
      <view
        :class="['nav-btn', currentStep === steps.length - 1 ? 'submit' : 'next']"
        @click="nextStep"
      >
        <text>{{ currentStep === steps.length - 1 ? (submitting ? '提交中...' : '确认启用') : '下一步' }}</text>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive } from 'vue'
import { getAgentConfig, updateAgentConfig, activateAgent, resumeAgent } from '@/api/agent'

interface Step {
  title: string
}

const steps: Step[] = [
  { title: '选择市场' },
  { title: '分配资金' },
  { title: '仓位控制' },
  { title: '风控设置' },
  { title: '自动执行' },
  { title: '交易风格' },
  { title: '确认启用' },
]

const marketOptions = [
  { value: 'a_stock', label: 'A股', flag: '沪/深' },
  { value: 'hk_stock', label: '港股', flag: '港' },
  { value: 'us_stock', label: '美股', flag: '美' },
  { value: 'crypto', label: '加密货币', flag: 'B' },
]

const quickAmounts = [10000, 50000, 100000, 200000, 500000]

const tradingStyles = [
  { value: 'scalping', label: '超短线', icon: '⚡', desc: '持仓数分钟到数小时' },
  { value: 'day_trading', label: '日内交易', icon: '☀️', desc: '当日开仓平仓' },
  { value: 'swing', label: '波段交易', icon: '📈', desc: '持仓数天到数周' },
  { value: 'trend', label: '趋势跟踪', icon: '🎯', desc: '顺大势中长期持有' },
  { value: 'balanced', label: '混合均衡', icon: '⚖️', desc: '多策略组合灵活切换' },
]

const currentStep = ref(0)
const loading = ref(true)
const submitting = ref(false)
const hireId = ref<number>(0)
const capitalInput = ref('')

const config = reactive({
  markets: [] as string[],
  allocated_capital: 0,
  max_position_pct: null as number | null,
  max_position_count: null as number | null,
  loss_stop_pct: null as number | null,
  loss_stop_amount: null as number | null,
  t1_enabled: false,
  auto_exec_confidence: 0.8,
  max_auto_exec_per_round: null as number | null,
  signal_interval_min: null as number | null,
  trading_style: 'swing' as string,
})

const toggleMarket = (val: string) => {
  const idx = config.markets.indexOf(val)
  if (idx >= 0) {
    config.markets.splice(idx, 1)
  } else {
    config.markets.push(val)
  }
}

const syncCapital = () => {
  const v = parseFloat(capitalInput.value)
  config.allocated_capital = isNaN(v) ? 0 : v
}

const formatAmount = (v: number) => {
  if (v >= 10000) return (v / 10000).toFixed(v % 10000 === 0 ? 0 : 1) + '万'
  return String(v)
}

const prevStep = () => {
  if (currentStep.value > 0) currentStep.value--
}

const nextStep = () => {
  if (currentStep.value < steps.length - 1) {
    currentStep.value++
  } else {
    handleSubmit()
  }
}

const loadConfig = async () => {
  try {
    const res = await getAgentConfig(hireId.value)
    const data = (res as any).data || res
    if (data) {
      config.markets = data.markets ?? []
      config.allocated_capital = data.allocated_capital ?? 0
      capitalInput.value = String(config.allocated_capital)
      config.max_position_pct = data.max_position_pct ?? null
      config.max_position_count = data.max_position_count ?? null
      config.loss_stop_pct = data.loss_stop_pct ?? null
      config.loss_stop_amount = data.loss_stop_amount ?? null
      config.t1_enabled = data.t1_enabled ?? false
      config.auto_exec_confidence = data.auto_exec_confidence ?? 0.8
      config.max_auto_exec_per_round = data.max_auto_exec_per_round ?? null
      config.signal_interval_min = data.signal_interval_min ?? null
      config.trading_style = data.trading_style ?? 'swing'
    }
  } catch (_e) {
    // 无已有配置则使用默认值
  } finally {
    loading.value = false
  }
}

const handleSubmit = async () => {
  submitting.value = true
  try {
    await updateAgentConfig(hireId.value, {
      markets: config.markets,
      allocated_capital: config.allocated_capital,
      max_position_pct: config.max_position_pct,
      max_position_count: config.max_position_count,
      loss_stop_pct: config.loss_stop_pct,
      loss_stop_amount: config.loss_stop_amount,
      t1_enabled: config.t1_enabled,
      auto_exec_confidence: config.auto_exec_confidence,
      max_auto_exec_per_round: config.max_auto_exec_per_round,
      signal_interval_min: config.signal_interval_min,
      trading_style: config.trading_style,
    })
    // P3: paused 状态走 resume，configuring/dormant 走 activate
    try {
      await activateAgent(hireId.value)
    } catch (e: any) {
      const detail = e?.response?.data?.detail || e?.message || ''
      if (detail.includes('不可激活') || detail.includes('paused')) {
        await resumeAgent(hireId.value)
      } else {
        throw e
      }
    }
    uni.showToast({ title: '配置成功，交易员已启用', icon: 'success' })
    setTimeout(() => uni.navigateBack(), 1200)
  } catch (e: any) {
    const msg = e?.response?.data?.detail || e?.message || '提交失败'
    uni.showToast({ title: msg, icon: 'none' })
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  const pages = getCurrentPages()
  const page = pages[pages.length - 1]
  const options = (page as any)?.options || {}
  if (options.hire_id) {
    hireId.value = Number(options.hire_id)
  }
  if (hireId.value) {
    loadConfig()
  } else {
    loading.value = false
  }
})
</script>

<style scoped lang="scss">
.agent-config-page {
  min-height: 100vh;
  background: #0f0f1a;
  padding-bottom: 140rpx;
}

.steps-bar {
  padding: 32rpx 32rpx 24rpx;
  background: #1a1a2e;
  position: sticky;
  top: 0;
  z-index: 10;
}

.steps-track {
  display: flex;
  align-items: center;
  justify-content: space-between;
  position: relative;
  margin-bottom: 20rpx;
}

.steps-line {
  position: absolute;
  left: 24rpx;
  right: 24rpx;
  top: 50%;
  height: 2rpx;
  background: rgba(255, 255, 255, 0.08);
  transform: translateY(-50%);
  z-index: 0;
}

.steps-line-fill {
  height: 100%;
  background: #4A90E2;
  transition: width 0.3s;
}

.step-dot {
  width: 48rpx;
  height: 48rpx;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.08);
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  z-index: 1;
  transition: all 0.3s;

  .step-num {
    font-size: 22rpx;
    font-weight: 700;
    color: #667788;
  }

  &.active {
    background: linear-gradient(135deg, #4A90E2, #7B68EE);
    box-shadow: 0 0 12rpx rgba(74, 144, 226, 0.4);
    .step-num { color: #fff; }
  }

  &.done {
    background: #27ae60;
    .step-num { color: #fff; }
  }
}

.steps-label {
  font-size: 30rpx;
  font-weight: 700;
  color: #4A90E2;
  display: block;
  text-align: center;
}

.loading-box {
  display: flex;
  justify-content: center;
  padding: 200rpx 0;

  .loading-text {
    font-size: 28rpx;
    color: #667788;
  }
}

.form-body {
  padding: 32rpx 24rpx;
}

.step-section {
  animation: fadeIn 0.25s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(12rpx); }
  to { opacity: 1; transform: translateY(0); }
}

.step-desc {
  font-size: 26rpx;
  color: #667788;
  display: block;
  margin-bottom: 32rpx;
}

/* 市场选择 */
.market-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20rpx;
}

.market-card {
  background: rgba(255, 255, 255, 0.04);
  border-radius: 16rpx;
  padding: 32rpx 20rpx;
  text-align: center;
  border: 2rpx solid transparent;
  transition: all 0.2s;

  .market-flag {
    font-size: 24rpx;
    color: #667788;
    display: block;
    margin-bottom: 8rpx;
  }

  .market-name {
    font-size: 28rpx;
    font-weight: 600;
    color: #ddd;
  }

  &.selected {
    border-color: #4A90E2;
    background: rgba(74, 144, 226, 0.1);
    .market-name { color: #4A90E2; }
    .market-flag { color: #4A90E2; }
  }
}

/* 输入组 */
.input-group {
  margin-bottom: 32rpx;

  .input-label {
    font-size: 26rpx;
    color: #8899aa;
    display: block;
    margin-bottom: 14rpx;
  }
}

.input-wrapper {
  display: flex;
  align-items: center;
  background: rgba(255, 255, 255, 0.06);
  border-radius: 12rpx;
  padding: 20rpx 24rpx;
  border: 1rpx solid rgba(255, 255, 255, 0.08);

  .input-prefix,
  .input-suffix {
    font-size: 28rpx;
    color: #667788;
    font-weight: 600;
  }

  .input-prefix {
    margin-right: 12rpx;
  }

  .input-suffix {
    margin-left: 12rpx;
  }

  .input-field {
    flex: 1;
    font-size: 28rpx;
    color: #fff;
    background: transparent;
  }
}

.quick-amounts {
  display: flex;
  flex-wrap: wrap;
  gap: 16rpx;
  margin-top: 20rpx;

  .quick-tag {
    padding: 14rpx 24rpx;
    background: rgba(255, 255, 255, 0.06);
    border-radius: 10rpx;
    font-size: 24rpx;
    color: #667788;

    &.active {
      background: rgba(74, 144, 226, 0.15);
      color: #4A90E2;
      border: 1rpx solid rgba(74, 144, 226, 0.3);
    }
  }
}

/* 风控 switch */
.toggle-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: rgba(255, 255, 255, 0.04);
  border-radius: 12rpx;
  padding: 24rpx;
  margin-bottom: 32rpx;

  .toggle-label {
    font-size: 26rpx;
    color: #ccc;
  }
}

/* 滑块 */
.slider-group {
  .slider-val {
    font-size: 32rpx;
    font-weight: 700;
    color: #4A90E2;
    display: block;
    margin-bottom: 16rpx;
  }
}

/* 交易风格 */
.style-list {
  .style-card {
    display: flex;
    align-items: center;
    background: rgba(255, 255, 255, 0.04);
    border-radius: 16rpx;
    padding: 28rpx 24rpx;
    margin-bottom: 16rpx;
    border: 2rpx solid transparent;
    transition: all 0.2s;

    .style-icon {
      font-size: 40rpx;
      margin-right: 20rpx;
      width: 56rpx;
      text-align: center;
    }

    .style-info {
      flex: 1;

      .style-name {
        font-size: 28rpx;
        font-weight: 600;
        color: #ddd;
        display: block;
      }

      .style-detail {
        font-size: 22rpx;
        color: #667788;
        margin-top: 4rpx;
      }
    }

    .style-check {
      width: 40rpx;
      height: 40rpx;
      border-radius: 50%;
      background: #4A90E2;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 24rpx;
      color: #fff;
      font-weight: 700;
    }

    &.selected {
      border-color: #4A90E2;
      background: rgba(74, 144, 226, 0.08);
    }
  }
}

/* 确认汇总 */
.summary-card {
  background: rgba(255, 255, 255, 0.04);
  border-radius: 16rpx;
  padding: 8rpx 20rpx;
}

.summary-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20rpx 0;
  border-bottom: 1rpx solid rgba(255, 255, 255, 0.04);

  &:last-child {
    border-bottom: none;
  }

  .summary-label {
    font-size: 26rpx;
    color: #667788;
  }

  .summary-val {
    font-size: 26rpx;
    font-weight: 600;
    color: #e0e0e0;
  }
}

/* 底部导航 */
.bottom-nav {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 20rpx 32rpx;
  padding-bottom: calc(20rpx + env(safe-area-inset-bottom));
  background: #1a1a2e;
  border-top: 1rpx solid rgba(255, 255, 255, 0.06);
  display: flex;
  gap: 16rpx;
  z-index: 100;
}

.nav-btn {
  flex: 1;
  text-align: center;
  padding: 24rpx 0;
  border-radius: 16rpx;
  font-size: 28rpx;
  font-weight: 600;

  &.prev {
    background: rgba(255, 255, 255, 0.08);
    color: #8899aa;
  }

  &.next {
    background: linear-gradient(135deg, #4A90E2, #7B68EE);
    color: #fff;
  }

  &.submit {
    background: linear-gradient(135deg, #27ae60, #4A90E2);
    color: #fff;
  }
}
</style>
