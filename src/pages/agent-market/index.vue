<template>
  <view class="agent-market-page">
    <!-- 顶部积分条 -->
    <view class="points-bar">
      <view class="points-info">
        <text class="points-label">我的积分</text>
        <text class="points-value">{{ pointsBalance }}</text>
      </view>
      <view class="points-actions">
        <text class="checkin-btn" @click="handleCheckin">签到+分</text>
      </view>
    </view>

    <!-- 交易员市场标题 -->
    <view class="section-header">
      <text class="section-title">交易员市场</text>
      <text class="section-hint">雇佣AI交易员，为你自动操盘</text>
    </view>

    <!-- 交易员卡片列表 -->
    <view class="agent-list">
      <view
        v-for="agent in agents"
        :key="agent.id"
        class="agent-card"
        :class="{ hired: hiredIds.has(agent.id) }"
        @click="goDetail(agent.id)"
      >
        <!-- 卡片头部 -->
        <view class="card-head">
          <view class="agent-avatar">
            <text class="avatar-text">{{ agent.code_name[0] }}</text>
          </view>
          <view class="agent-info">
            <text class="agent-name">{{ agent.code_name }}</text>
            <text class="agent-tag">{{ agent.tag }}</text>
          </view>
          <view v-if="hiredIds.has(agent.id)" class="hired-badge">已雇佣</view>
        </view>

        <!-- 师承 -->
        <text class="agent-masters">{{ agent.masters }}</text>

        <!-- 业绩指标 -->
        <view class="card-metrics">
          <view class="metric-item">
            <text class="metric-value" :class="(agent.annual_return || 0) > 0 ? 'val-up' : 'val-down'">
              {{ formatPct(agent.annual_return) }}
            </text>
            <text class="metric-label">年化收益</text>
          </view>
          <view class="metric-item">
            <text class="metric-value val-down">
              {{ formatPct(agent.max_drawdown) }}
            </text>
            <text class="metric-label">最大回撤</text>
          </view>
          <view class="metric-item">
            <text class="metric-value">{{ agent.sharpe_ratio }}</text>
            <text class="metric-label">夏普比率</text>
          </view>
          <view class="metric-item">
            <text class="metric-value">{{ formatPct(agent.win_rate) }}</text>
            <text class="metric-label">胜率</text>
          </view>
        </view>

        <!-- 简介 -->
        <text class="agent-desc">{{ truncate(agent.description, 60) }}</text>

        <!-- 底部操作 -->
        <view class="card-footer">
          <view class="price-row">
            <text class="price-value">{{ agent.hire_price_points }}</text>
            <text class="price-unit">积分/30天</text>
          </view>
          <view v-if="!hiredIds.has(agent.id)" class="hire-btn">立即雇佣</view>
          <view v-else class="hire-btn-disabled">已雇佣</view>
        </view>
      </view>
    </view>

    <!-- 底部导航：我的交易员 -->
    <view class="my-agents-link" @click="goMyAgents">
      <text>我的交易员</text>
      <text class="arrow">&gt;</text>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref } from 'vue'; import { onShow } from '@dcloudio/uni-app'
import { getAgentMarket, getMyAgents, type AgentTrader } from '@/api/agent'
import { getPointsBalance, dailyCheckin } from '@/api/points'

const agents = ref<AgentTrader[]>([])
const pointsBalance = ref(0)
const hiredIds = ref(new Set<string>())

const formatPct = (v: number | null | undefined) => {
  if (v == null) return '--'
  return (v > 0 ? '+' : '') + v.toFixed(1) + '%'
}

const truncate = (s: string, len: number) => {
  if (!s) return ''
  return s.length > len ? s.slice(0, len) + '...' : s
}

const loadData = async () => {
  try {
    const [marketRes, myAgentsRes] = await Promise.all([
      getAgentMarket(),
      getMyAgents().catch(() => []),
    ])
    agents.value = marketRes.items
    hiredIds.value = new Set(
      (Array.isArray(myAgentsRes) ? myAgentsRes : []).map((ua: any) => ua.agent_id)
    )
  } catch (e) {
    console.error('加载交易员市场失败', e)
  }
  try {
    const bal = await getPointsBalance()
    pointsBalance.value = bal.balance
  } catch (e) {
    // ignore
  }
}

const handleCheckin = async () => {
  try {
    const res = await dailyCheckin()
    if (res.success) {
      pointsBalance.value = res.balance
      uni.showToast({ title: `签到成功 +${res.points_earned}分`, icon: 'success' })
    } else {
      uni.showToast({ title: '今日已签到', icon: 'none' })
    }
  } catch (e: any) {
    uni.showToast({ title: e?.message || '签到失败', icon: 'none' })
  }
}

const goDetail = (id: string) => {
  uni.navigateTo({ url: `/pages/agent-market/detail?id=${id}` })
}

const goMyAgents = () => {
  uni.navigateTo({ url: '/pages/agent-market/my-agents' })
}

onShow(() => {
  loadData()
})
</script>

<style scoped lang="scss">
.agent-market-page {
  min-height: 100vh;
  background: #0f0f1a;
  padding: 20rpx 24rpx 200rpx;
}

.points-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: linear-gradient(135deg, #1a1a3e 0%, #16213e 100%);
  border-radius: 16rpx;
  padding: 28rpx 32rpx;
  margin-bottom: 32rpx;
  border: 1rpx solid rgba(74, 144, 226, 0.2);

  .points-info {
    .points-label {
      font-size: 24rpx;
      color: #8899aa;
    }
    .points-value {
      display: block;
      font-size: 48rpx;
      font-weight: 700;
      color: #4A90E2;
      font-family: 'DIN Alternate', monospace;
    }
  }

  .checkin-btn {
    background: linear-gradient(135deg, #4A90E2, #357ABD);
    color: #fff;
    font-size: 26rpx;
    padding: 14rpx 28rpx;
    border-radius: 24rpx;
  }
}

.section-header {
  margin-bottom: 28rpx;

  .section-title {
    font-size: 36rpx;
    font-weight: 700;
    color: #ffffff;
    display: block;
  }
  .section-hint {
    font-size: 24rpx;
    color: #667788;
    margin-top: 6rpx;
  }
}

.agent-list {
  display: flex;
  flex-direction: column;
  gap: 24rpx;
}

.agent-card {
  background: #1a1a2e;
  border-radius: 20rpx;
  padding: 28rpx;
  border: 1rpx solid rgba(255, 255, 255, 0.06);

  &.hired {
    border-color: rgba(74, 144, 226, 0.3);
  }
}

.card-head {
  display: flex;
  align-items: center;
  margin-bottom: 16rpx;

  .agent-avatar {
    width: 80rpx;
    height: 80rpx;
    border-radius: 20rpx;
    background: linear-gradient(135deg, #4A90E2, #7B68EE);
    display: flex;
    align-items: center;
    justify-content: center;
    margin-right: 20rpx;

    .avatar-text {
      font-size: 36rpx;
      font-weight: 700;
      color: #fff;
    }
  }

  .agent-info {
    flex: 1;

    .agent-name {
      font-size: 34rpx;
      font-weight: 700;
      color: #ffffff;
      display: block;
    }
    .agent-tag {
      font-size: 24rpx;
      color: #4A90E2;
    }
  }

  .hired-badge {
    font-size: 22rpx;
    color: #27ae60;
    background: rgba(39, 174, 96, 0.12);
    padding: 6rpx 16rpx;
    border-radius: 12rpx;
  }
}

.agent-masters {
  font-size: 22rpx;
  color: #667788;
  margin-bottom: 20rpx;
  display: block;
}

.card-metrics {
  display: flex;
  justify-content: space-between;
  padding: 20rpx;
  background: rgba(255, 255, 255, 0.04);
  border-radius: 12rpx;
  margin-bottom: 16rpx;

  .metric-item {
    text-align: center;

    .metric-value {
      font-size: 28rpx;
      font-weight: 700;
      font-family: 'DIN Alternate', monospace;
    }
    .metric-label {
      font-size: 20rpx;
      color: #667788;
      display: block;
      margin-top: 4rpx;
    }
  }
}

.agent-desc {
  font-size: 24rpx;
  color: #99aabb;
  line-height: 1.5;
  display: block;
  margin-bottom: 20rpx;
}

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;

  .price-row {
    display: flex;
    align-items: baseline;

    .price-value {
      font-size: 36rpx;
      font-weight: 700;
      color: #f0c060;
      font-family: 'DIN Alternate', monospace;
    }
    .price-unit {
      font-size: 22rpx;
      color: #667788;
      margin-left: 6rpx;
    }
  }

  .hire-btn {
    background: linear-gradient(135deg, #4A90E2, #7B68EE);
    color: #fff;
    font-size: 26rpx;
    padding: 16rpx 36rpx;
    border-radius: 28rpx;
    font-weight: 500;
  }
  .hire-btn-disabled {
    background: rgba(255, 255, 255, 0.08);
    color: #556677;
    font-size: 26rpx;
    padding: 16rpx 36rpx;
    border-radius: 28rpx;
  }
}

.my-agents-link {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 32rpx;
  background: linear-gradient(transparent, #0f0f1a 40%);
  color: #4A90E2;
  font-size: 30rpx;
  font-weight: 500;

  .arrow {
    margin-left: 8rpx;
  }
}

.val-up { color: #e74c3c; }
.val-down { color: #27ae60; }
</style>
