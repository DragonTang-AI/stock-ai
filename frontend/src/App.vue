<script setup lang="ts">
import { onLaunch, onShow, onHide } from '@dcloudio/uni-app'
import { useAuthStore } from '@/stores/auth'
import { useComplianceStore } from '@/stores/compliance'
import AuditBadge from '@/components/compliance/AuditBadge.vue'
import { applyTheme } from '@/utils/theme'

onLaunch(() => {
  console.log('App Launch')

  // 初始化深色模式
  applyTheme()

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
})

onHide(() => {
  console.log('App Hide')
})
</script>

<template>
  <AuditBadge />
  <router-view />
</template>

<style lang="scss">
@import '@/styles/main.scss';
</style>
