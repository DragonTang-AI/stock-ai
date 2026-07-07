<script setup lang="ts">
import { onLaunch, onShow, onHide, onError } from '@dcloudio/uni-app'
import { ref } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useComplianceStore } from '@/stores/compliance'
import AuditBadge from '@/components/compliance/AuditBadge.vue'
import { applyTheme } from '@/utils/theme'
import { initNetworkMonitor, isOnline, onNetworkChange } from '@/utils/network'
import { isOfflineMode, showOfflineToast } from '@/utils/offline'
import { initTracker, trackJsError, flushEvents } from '@/utils/tracker'

/** 全局离线状态（供各页面通过 provide/inject 使用） */
const globalOffline = ref(false)

onLaunch(() => {
  console.log('App Launch')

  // 初始化埋点
  initTracker()

  // 初始化深色模式
  applyTheme()

  // 初始化网络监听
  initNetworkMonitor()
  globalOffline.value = !isOnline()

  // 监听网络变化，更新全局状态
  onNetworkChange((info) => {
    globalOffline.value = !info.isConnected
    // 断网时提示（静默更新，App 级别提示一次）
    if (!info.isConnected) {
      showOfflineToast()
    }
  })

  // #ifdef MP-WEIXIN
  // 微信小程序版本更新检查
  const updateManager = wx.getUpdateManager()
  updateManager.onCheckForUpdate((res) => {
    if (res.hasUpdate) {
      updateManager.onUpdateReady(() => {
        wx.showModal({
          title: '更新提示',
          content: '新版本已就绪，是否重启应用以体验最新功能？',
          success(res) {
            if (res.confirm) {
              updateManager.applyUpdate()
            }
          }
        })
      })
      updateManager.onUpdateFailed(() => {
        wx.showModal({
          title: '更新提示',
          content: '新版本下载失败，请检查网络后重试',
          showCancel: false
        })
      })
    }
  })
  // #endif

  // 检查登录态
  const authStore = useAuthStore()
  authStore.checkAuth()

  // 检查合规审核模式
  const complianceStore = useComplianceStore()
  complianceStore.checkAuditMode()

  // 如果未登录，跳转到登录页
  if (!authStore.isLoggedIn) {
    uni.reLaunch({ url: '/pages/login/index' })
  }
})

onShow(() => {
  console.log('App Show')
  // 回前台时刷新网络状态
  globalOffline.value = !isOnline()
})

onHide(() => {
  console.log('App Hide')
  // 页面隐藏时刷新埋点队列
  flushEvents()
})

onError((err: string) => {
  // 全局 JS 错误捕获并上报
  trackJsError(err)
})

// 提供给子组件的全局离线状态
uni.$globalOffline = globalOffline
</script>

<template>
  <AuditBadge />
  <router-view />
</template>

<style lang="scss">
@import '@/styles/main.scss';
</style>
