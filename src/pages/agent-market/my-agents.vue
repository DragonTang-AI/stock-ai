<template>
  <view class="my-agents-page">
    <view v-if="loading" class="loading-box">
      <text class="loading-text">加载中...</text>
    </view>

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
            <text :class="item.status === 'active' ? 'status-active' : 'status-expired'">
              {{ item.status === 'active' ? '运行中' : '已停用' }}
            </text>
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
              <view v-if="item.status === 'active'" class="ft-btn pause-btn" @click="handlePause(item)">
                <text>暂停</text>
              </view>
              <view v-if="item.status === 'paused'" class="ft-btn resume-btn" @click="handleResume(item)">
                <text>恢复</text>
              </view>
              <view class="ft-btn terminate-btn" @click="handleTerminate(item)">
                <text>终止</text>
              </view>
            </view>
          </view>
        </view>
      </view>
    </template>
  </view>
</template>

<script setup lang="ts">
import { ref } from 'vue'; import { onShow } from '@dcloudio/uni-app'
import { getMyAgents, updateManagementMode, dismissAgent, pauseAgent, resumeAgent, terminateAgent, type UserAgent } from '@/api/agent'

const loading = ref(true)
const myAgents = ref<UserAgent[]>([])

const formatPct = (v: number | null | undefined) => {
  if (v == null) return '--'
  return (v >= 0 ? '+' : '') + v.toFixed(1) + '%'
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
  loadData()
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
  .status-expired {
    font-size: 22rpx;
    color: #667788;
    background: rgba(255, 255, 255, 0.06);
    padding: 6rpx 16rpx;
    border-radius: 12rpx;
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
  .terminate-btn {
    background: rgba(231, 76, 60, 0.15);
    color: #e74c3c;
  }

</style>
