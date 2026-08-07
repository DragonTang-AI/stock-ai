<template>
  <view class="my-agents-page">
    <LoadingSkeleton v-if="loading" scene="default" fallbackType="card" :rows="3" />

    <template v-else>
      <!-- 空状态 -->
      <view v-if="myAgents.length === 0" class="empty-state">
        <text class="empty-icon">+_+</text>
        <text class="empty-text">还没有雇佣交易员</text>
        <view class="empty-btn" @click="goMarket">去市场看看</view>
      </view>

      <!-- 列表 -->
      <view v-else class="agent-list">
        <view v-for="item in myAgents" :key="item.id" class="agent-card">
          <view class="card-head" @click="goDetail(item.agent_id)">
            <view class="agent-avatar">
              <text class="avatar-text">{{ item.agent.code_name[0] }}</text>
            </view>
            <view class="agent-info">
              <text class="agent-name">{{ item.agent.code_name }}</text>
              <text class="agent-tag">{{ item.agent.tag }}</text>
            </view>
            <view class="status-group">
              <text v-if="isUnconfigured(item)" class="alert-icon">⚠</text>
              <text :class="statusClass(item)">
                {{ statusText(item) }}
              </text>
            </view>
          </view>

          <view class="card-metrics">
            <view class="m-item">
              <text class="m-value" :class="item.agent.annual_return && item.agent.annual_return > 0 ? 'up' : 'down'">
                {{ formatPct(item.agent.annual_return) }}
              </text>
              <text class="m-label">年化收益</text>
            </view>
            <view class="m-item">
              <text class="m-value" :class="(item.current_pnl || 0) >= 0 ? 'up' : 'down'">
                {{ formatPct(item.current_pnl) }}
              </text>
              <text class="m-label">浮动盈亏</text>
            </view>
            <view class="m-item">
              <text class="m-value" style="color: #4A90E2">{{ item.management_mode === 'full_managed' ? '托管' : '建议' }}</text>
              <text class="m-label">管理方式</text>
            </view>
          </view>

          <view v-if="isUnconfigured(item)" class="config-warning">
            <text class="warning-icon">⚠</text>
            <text class="warning-text">启动交易员前必须完成配置，否则无法启动</text>
          </view>

          <view class="card-footer">
            <view class="footer-row">
              <view class="ft-btn console-btn" @click="goConsole(item)">
                <text>进入控制台</text>
              </view>
              <view class="mode-row" @click="switchMode(item)">
                <text class="mode-label">切换模式</text>
                <text class="mode-arrow">&gt;</text>
              </view>
            </view>
            <view class="footer-row footer-actions">
              <!-- 未配置：仅显示去配置 + 终止 -->
              <template v-if="isUnconfigured(item)">
                <view class="ft-btn config-urgent-btn" @click="goConfig(item)">
                  <text>⚠ 去配置</text>
                </view>
                <view class="ft-btn terminate-btn" @click="handleTerminate(item)">
                  <text>终止</text>
                </view>
              </template>
              <!-- 已配置 -->
              <template v-else>
                <view v-if="item.status === 'active'" class="ft-btn pause-btn" @click="handlePause(item)">
                  <text>暂停</text>
                </view>
                <view v-if="item.status === 'paused'" class="ft-btn resume-btn" @click="handleResume(item)">
                  <text>恢复</text>
                </view>
                <view v-if="item.status === 'configuring'" class="ft-btn config-btn" @click="goConfig(item)">
                  <text>继续配置</text>
                </view>
                <view v-if="item.status === 'active' || item.status === 'paused'" class="ft-btn config-btn" @click="goConfig(item)">
                  <text>配置</text>
                </view>
                <view class="ft-btn terminate-btn" @click="handleTerminate(item)">
                  <text>终止</text>
                </view>
              </template>
            </view>
          </view>
        </view>
      </view>
    </template>
  </view>
</template>

<script setup lang="ts">
import { ref } from 'vue'; import { onPullDownRefresh, onShow } from '@dcloudio/uni-app'
import LoadingSkeleton from '@/components/common/LoadingSkeleton.vue'
import { getMyAgents, updateManagementMode, dismissAgent, pauseAgent, resumeAgent, terminateAgent, type UserAgent } from '@/api/agent'
import { formatPercent } from '@/utils/format'
import { useShowRefresh, touchRefreshKey } from '@/utils/refresh-cache'

const loading = ref(true)
const myAgents = ref<UserAgent[]>([])

const formatPct = (v: number | null | undefined) => {
  if (v == null) return '--'
  return formatPercent(v, 1)
}

const isUnconfigured = (item: UserAgent) => {
  return item.config_source === 'default' || (!item.config_source && item.status !== 'configuring')
}

const statusClass = (item: UserAgent) => {
  if (item.status === 'active') return 'status-active'
  if (item.status === 'configuring') return 'status-configuring'
  if (item.status === 'paused') {
    if (isUnconfigured(item)) return 'status-unconfigured'
    return 'status-paused'
  }
  return 'status-expired'
}

const statusText = (item: UserAgent) => {
  if (item.status === 'active') return '运行中'
  if (item.status === 'configuring') return '待配置'
  if (item.status === 'paused') {
    if (isUnconfigured(item)) return '未配置'
    return '已暂停'
  }
  return '已停用'
}

const loadData = async () => {
  loading.value = true
  try {
    myAgents.value = await getMyAgents()
  } catch (e) {
    console.error('加载失败', e)
  } finally {
    loading.value = false
  }
}


const goConsole = (item: UserAgent) => {
  uni.navigateTo({ url: `/pages/agent-console/index?hire_id=${item.id}` })
}

const goConfig = (item: UserAgent) => {
  uni.navigateTo({ url: `/pages/agent-config/index?hire_id=${item.id}` })
}

const handlePause = (item: UserAgent) => {
  uni.showModal({
    title: '暂停交易员',
      content: `确定暂停「${item.agent.code_name}」吗？暂停后不再生成新信号。`,
    success: async (res) => {
      if (res.confirm) {
        try {
          await pauseAgent(item.id)
          item.status = 'paused'
          uni.showToast({ title: '已暂停', icon: 'success' })
        } catch (e: any) {
          uni.showToast({ title: e?.message || '操作失败', icon: 'none' })
        }
      }
    },
  })
}

const handleResume = (item: UserAgent) => {
  uni.showModal({
    title: '恢复交易员',
      content: `确定恢复「${item.agent.code_name}」吗？`,
    success: async (res) => {
      if (res.confirm) {
        try {
          await resumeAgent(item.id)
          item.status = 'active'
          uni.showToast({ title: '已恢复', icon: 'success' })
        } catch (e: any) {
          uni.showToast({ title: e?.message || '操作失败', icon: 'none' })
        }
      }
    },
  })
}

const handleTerminate = (item: UserAgent) => {
  uni.showModal({
    title: '终止雇佣',
      content: `确定终止「${item.agent.code_name}」的雇佣关系吗？将清理所有持仓和信号，此操作不可撤销。`,
    success: async (res) => {
      if (res.confirm) {
        try {
          await terminateAgent(item.id)
          uni.showToast({ title: '已终止', icon: 'success' })
          loadData()
        } catch (e: any) {
          uni.showToast({ title: e?.message || '操作失败', icon: 'none' })
        }
      }
    },
  })
}

const goMarket = () => {
  uni.navigateBack()
}

const goDetail = (agentId: string) => {
  uni.navigateTo({ url: `/pages/agent-market/detail?id=${agentId}` })
}

const switchMode = (item: UserAgent) => {
  const modes = ['建议模式（AI推荐）', '完全托管（AI自动交易）']
  const current = item.management_mode === 'full_managed' ? 1 : 0
  uni.showActionSheet({
    itemList: modes,
    success: async (res) => {
      const mode = res.tapIndex === 1 ? 'full_managed' : 'advisory'
      if (mode === item.management_mode) return
      try {
        await updateManagementMode(item.id, mode)
        item.management_mode = mode
        uni.showToast({ title: '已切换', icon: 'success' })
      } catch (e: any) {
        uni.showToast({ title: e?.message || '切换失败', icon: 'none' })
      }
    },
  })
}

const handleDismiss = (item: UserAgent) => {
  uni.showModal({
    title: '确认解雇',
    content: `确定要解雇「${item.agent.code_name}·${item.agent.tag}」吗？`,
    success: async (res) => {
      if (res.confirm) {
        try {
          await dismissAgent(item.id)
          myAgents.value = myAgents.value.filter((a) => a.id !== item.id)
          uni.showToast({ title: '已解雇', icon: 'success' })
        } catch (e: any) {
          uni.showToast({ title: e?.message || '解雇失败', icon: 'none' })
        }
      }
    },
  })
}
onShow(() => {
  useShowRefresh('my-agents', () => loadData())
})

onPullDownRefresh(() => {
  uni.stopPullDownRefresh()
})
</script>

<style scoped lang="scss">
.my-agents-page {
  min-height: 100vh;
  background: #0f0f1a;
  padding: 24rpx 24rpx 60rpx;
}

.loading-box {
  display: flex;
  justify-content: center;
  padding: 100rpx;
  .loading-text { color: #667788; font-size: 28rpx; }
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding-top: 160rpx;

  .empty-icon {
    font-size: 80rpx;
    margin-bottom: 20rpx;
  }
  .empty-text {
    font-size: 30rpx;
    color: #667788;
    margin-bottom: 40rpx;
  }
  .empty-btn {
    background: linear-gradient(135deg, #4A90E2, #7B68EE);
    color: #fff;
    font-size: 30rpx;
    padding: 20rpx 48rpx;
    border-radius: 32rpx;
  }
}

.agent-card {
  background: #1a1a2e;
  border-radius: 20rpx;
  padding: 28rpx;
  margin-bottom: 24rpx;
  border: 1rpx solid rgba(255, 255, 255, 0.06);
}

.card-head {
  display: flex;
  align-items: center;
  margin-bottom: 20rpx;

  .agent-avatar {
    width: 72rpx;
    height: 72rpx;
    border-radius: 18rpx;
    background: linear-gradient(135deg, #4A90E2, #7B68EE);
    display: flex;
    align-items: center;
    justify-content: center;
    margin-right: 18rpx;

    .avatar-text {
      font-size: 32rpx;
      font-weight: 700;
      color: #fff;
    }
  }

  .agent-info {
    flex: 1;
    .agent-name {
      font-size: 30rpx;
      font-weight: 700;
      color: #fff;
      display: block;
    }
    .agent-tag {
      font-size: 22rpx;
      color: #4A90E2;
    }
  }

  .status-active {
    font-size: 22rpx;
    color: #27ae60;
    background: rgba(39, 174, 96, 0.12);
    padding: 6rpx 16rpx;
    border-radius: 12rpx;
  }
  .status-configuring {
    font-size: 22rpx;
    color: #f0c060;
    background: rgba(240, 192, 96, 0.12);
    padding: 6rpx 16rpx;
    border-radius: 12rpx;
  }
  .status-paused {
    font-size: 22rpx;
    color: #667788;
    background: rgba(255, 255, 255, 0.06);
    padding: 6rpx 16rpx;
    border-radius: 12rpx;
  }
  .status-unconfigured {
    font-size: 22rpx;
    color: #e74c3c;
    background: rgba(231, 76, 60, 0.12);
    padding: 6rpx 16rpx;
    border-radius: 12rpx;
  }
  .status-expired {
    font-size: 22rpx;
    color: #667788;
    background: rgba(255, 255, 255, 0.06);
    padding: 6rpx 16rpx;
    border-radius: 12rpx;
  }
  .status-group {
    display: flex;
    align-items: center;
    gap: 6rpx;
  }
  .alert-icon {
    font-size: 28rpx;
    color: #e74c3c;
  }
}

.card-metrics {
  display: flex;
  justify-content: space-between;
  padding: 20rpx;
  background: rgba(255, 255, 255, 0.04);
  border-radius: 12rpx;
  margin-bottom: 20rpx;

  .m-item {
    text-align: center;
    flex: 1;
    .m-value {
      font-size: 28rpx;
      font-weight: 700;
      font-family: 'DIN Alternate', monospace;
    }
    .m-label {
      font-size: 20rpx;
      color: #667788;
      display: block;
      margin-top: 4rpx;
    }
  }
}

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;

  .mode-row {
    display: flex;
    align-items: center;
    .mode-label {
      font-size: 26rpx;
      color: #4A90E2;
    }
    .mode-arrow {
      font-size: 24rpx;
      color: #4A90E2;
      margin-left: 4rpx;
    }
  }

  .dismiss-btn {
    .dismiss-text {
      font-size: 26rpx;
      color: #e74c3c;
    }
  }
}

.up { color: #e74c3c; }
.down { color: #27ae60; }

  .footer-row {
    display: flex;
    align-items: center;
    gap: 16rpx;
    margin-bottom: 12rpx;
  }
  .footer-actions {
    margin-bottom: 0;
  }
  .ft-btn {
    padding: 12rpx 24rpx;
    border-radius: 10rpx;
    font-size: 24rpx;
    font-weight: 600;
  }
  .console-btn {
    background: linear-gradient(135deg, #4A90E2, #7B68EE);
    color: #fff;
    flex: 1;
    text-align: center;
  }
  .pause-btn {
    background: rgba(243, 156, 18, 0.15);
    color: #f39c12;
  }
  .resume-btn {
    background: rgba(39, 174, 96, 0.15);
    color: #27ae60;
  }
  .config-btn {
    background: rgba(240, 192, 96, 0.15);
    color: #f0c060;
  }
  .config-urgent-btn {
    background: rgba(231, 76, 60, 0.15);
    color: #e74c3c;
    border: 1rpx solid rgba(231, 76, 60, 0.3);
    flex: 1;
    text-align: center;
  }
  .terminate-btn {
    background: rgba(231, 76, 60, 0.15);
    color: #e74c3c;
  }

  .config-warning {
    background: rgba(231, 76, 60, 0.08);
    border: 1rpx solid rgba(231, 76, 60, 0.2);
    border-radius: 10rpx;
    padding: 14rpx 20rpx;
    margin-bottom: 16rpx;
    display: flex;
    align-items: center;
    gap: 8rpx;
  }
  .warning-icon {
    font-size: 24rpx;
    color: #e74c3c;
  }
  .warning-text {
    font-size: 22rpx;
    color: #e74c3c;
  }

</style>
