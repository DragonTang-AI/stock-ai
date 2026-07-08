<template>
  <view class="advisor-page">
    <!-- 骨架屏 -->
    <LoadingSkeleton v-if="loading" scene="chat" :rows="4" />

    <!-- 聊天区域 -->
    <scroll-view
      v-else
      class="chat-scroll"
      scroll-y
      :scroll-into-view="scrollToId"
    >
      <view class="chat-list">
        <!-- 空状态 -->
        <view v-if="messages.length === 0" class="empty-chat">
          <text class="empty-title">AI 投资助手</text>
          <text class="empty-desc">我可以帮您分析持仓、诊断风险、回答投资问题</text>
          <view class="quick-questions">
            <view
              v-for="q in quickQuestions"
              :key="q"
              class="quick-item"
              @click="sendMessage(q)"
            >
              <text>{{ q }}</text>
            </view>
          </view>
        </view>

        <!-- 消息列表 -->
        <view
          v-for="(msg, idx) in messages"
          :key="idx"
          :id="`msg-${idx}`"
          class="chat-item"
          :class="msg.role === 'user' ? 'user' : 'ai'"
        >
          <view class="chat-avatar">
            <text>{{ msg.role === 'user' ? '我' : 'AI' }}</text>
          </view>
          <view class="chat-bubble">
            <text>{{ msg.content }}</text>
          </view>
        </view>
      </view>
    </scroll-view>

    <!-- 输入区域 -->
    <view class="input-area">
      <input
        v-model="inputText"
        class="chat-input"
        placeholder="输入您的问题..."
        placeholder-style="color:#bbb"
        :disabled="sending"
        @confirm="sendMessage(inputText)"
      />
      <button
        class="btn-send"
        :disabled="!inputText.trim() || sending"
        @click="sendMessage(inputText)"
      >
        {{ sending ? '发送中' : '发送' }}
      </button>
    </view>

    <Disclaimer />
  </view>
</template>

<script setup lang="ts">
import { ref, nextTick } from 'vue'
import { getChatContext } from '@/api/advisor'
import LoadingSkeleton from '@/components/common/LoadingSkeleton.vue'
import Disclaimer from '@/components/compliance/Disclaimer.vue'

interface ChatMessage {
  role: 'user' | 'ai'
  content: string
}

const loading = ref(false)
const sending = ref(false)
const inputText = ref('')
const messages = ref<ChatMessage[]>([])
const scrollToId = ref('')

const quickQuestions = [
  '帮我分析一下当前持仓',
  '今天适合买入吗？',
  '有没有推荐的股票？',
  '解释一下PE和PB的区别',
]

async function sendMessage(text: string) {
  const content = text?.trim()
  if (!content || sending.value) return

  messages.value.push({ role: 'user', content })
  inputText.value = ''
  sending.value = true

  await nextTick()
  scrollToId.value = `msg-${messages.value.length - 1}`

  try {
    const res = await getChatContext(content)
    const reply = extractReply(res)
    messages.value.push({ role: 'ai', content: reply })
  } catch {
    messages.value.push({
      role: 'ai',
      content: '抱歉，AI 服务暂时不可用，请稍后重试。',
    })
  } finally {
    sending.value = false
    await nextTick()
    scrollToId.value = `msg-${messages.value.length - 1}`
  }
}

function extractReply(data: any): string {
  if (typeof data === 'string') return data
  if (data?.reply) return data.reply
  if (data?.content) return data.content
  if (data?.data?.reply) return data.data.reply
  if (data?.data?.content) return data.data.content
  return JSON.stringify(data)
}
</script>

<style scoped lang="scss">
.advisor-page {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: var(--bg-page, #f5f5f7);
}

.chat-scroll {
  flex: 1;
  padding: 24rpx;
}

.chat-list {
  display: flex;
  flex-direction: column;
  gap: 24rpx;
}

.empty-chat {
  text-align: center;
  padding: 120rpx 48rpx 0;
}

.empty-title {
  display: block;
  font-size: 40rpx;
  font-weight: 700;
  color: var(--text-primary, #333);
  margin-bottom: 16rpx;
}

.empty-desc {
  display: block;
  font-size: 26rpx;
  color: var(--text-hint, #999);
  margin-bottom: 40rpx;
}

.quick-questions {
  display: flex;
  flex-wrap: wrap;
  gap: 16rpx;
  justify-content: center;
}

.quick-item {
  padding: 16rpx 28rpx;
  background: var(--bg-card, #fff);
  border: 1rpx solid var(--border-color, #e0e0e0);
  border-radius: 40rpx;
  font-size: 26rpx;
  color: #4A90E2;
}

.chat-item {
  display: flex;
  gap: 16rpx;
  max-width: 85%;

  &.user {
    align-self: flex-end;
    flex-direction: row-reverse;
  }

  &.ai {
    align-self: flex-start;
  }
}

.chat-avatar {
  width: 64rpx;
  height: 64rpx;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24rpx;
  font-weight: 600;
  color: #fff;
  flex-shrink: 0;
}

.chat-item.user .chat-avatar { background: #4A90E2; }
.chat-item.ai .chat-avatar { background: #52c41a; }

.chat-bubble {
  padding: 20rpx 24rpx;
  border-radius: 16rpx;
  font-size: 28rpx;
  line-height: 1.6;
  color: var(--text-primary, #333);
  word-break: break-all;
}

.chat-item.user .chat-bubble {
  background: #4A90E2;
  color: #fff;
}

.chat-item.ai .chat-bubble {
  background: #fff;
  box-shadow: 0 2rpx 12rpx rgba(0, 0, 0, 0.06);
}

.input-area {
  display: flex;
  align-items: center;
  gap: 16rpx;
  padding: 16rpx 24rpx env(safe-area-inset-bottom);
  background: #fff;
  border-top: 1rpx solid var(--border-color, #f0f0f0);
}

.chat-input {
  flex: 1;
  height: 72rpx;
  padding: 0 24rpx;
  background: var(--bg-card, #f8f9fa);
  border-radius: 36rpx;
  font-size: 28rpx;
  color: var(--text-primary, #333);
}

.btn-send {
  width: 120rpx;
  height: 72rpx;
  line-height: 72rpx;
  text-align: center;
  font-size: 28rpx;
  color: #fff;
  background: #4A90E2;
  border-radius: 36rpx;
  border: none;

  &[disabled] {
    opacity: 0.5;
  }
}
</style>
