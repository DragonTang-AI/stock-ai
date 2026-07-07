/**
 * 认证状态管理（Pinia Store）
 * 管理 JWT Token、登录态、用户信息
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useAuthStore = defineStore('auth', () => {
  // ─── 状态 ───
  const accessToken = ref<string>('')
  const refreshToken = ref<string>('')
  const userInfo = ref<{
    id?: number
    username?: string
    nickname?: string
    avatar?: string
  } | null>(null)

  // ─── 计算属性 ───
  const isLoggedIn = computed(() => !!accessToken.value)

  // ─── 方法 ───
  /** 检查本地登录态 */
  function checkAuth(): boolean {
    try {
      const token = uni.getStorageSync('accessToken')
      const refresh = uni.getStorageSync('refreshToken')
      if (token) {
        accessToken.value = token
        refreshToken.value = refresh || ''
        return true
      }
    } catch {
      // Storage 读取失败
    }
    return false
  }

  /** 设置登录凭证 */
  function setAuth(access: string, refresh: string) {
    accessToken.value = access
    refreshToken.value = refresh
    try {
      uni.setStorageSync('accessToken', access)
      uni.setStorageSync('refreshToken', refresh)
    } catch {
      // Storage 写入失败
    }
  }

  /** 设置用户信息 */
  function setUserInfo(info: typeof userInfo.value) {
    userInfo.value = info
  }

  /** 退出登录 */
  function logout() {
    accessToken.value = ''
    refreshToken.value = ''
    userInfo.value = null
    try {
      uni.removeStorageSync('accessToken')
      uni.removeStorageSync('refreshToken')
    } catch {
      // 忽略
    }
  }

  /** 刷新 Token */
  async function refreshAccessToken(): Promise<boolean> {
    if (!refreshToken.value) return false
    try {
      // 由 request.ts 拦截器统一处理，这里仅做状态更新
      return true
    } catch {
      logout()
      return false
    }
  }

  return {
    accessToken,
    refreshToken,
    userInfo,
    isLoggedIn,
    checkAuth,
    setAuth,
    setUserInfo,
    logout,
    refreshAccessToken,
  }
})
