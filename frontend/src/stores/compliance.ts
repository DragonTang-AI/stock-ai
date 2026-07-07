/**
 * 合规审核模式状态管理（Pinia Store）
 * 管理审核模式开关、免责声明状态
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useComplianceStore = defineStore('compliance', () => {
  // ─── 状态 ───
  const isAuditMode = ref<boolean>(false)
  const auditChecked = ref<boolean>(false)

  // ─── 计算属性 ───
  /** 是否为审核模式（隐藏敏感功能） */
  const auditActive = computed(() => isAuditMode.value)
  /** 是否已完成审核检查 */
  const auditReady = computed(() => auditChecked.value)

  // ─── 方法 ───
  /** 检查审核模式状态 */
  function checkAuditMode(): void {
    try {
      // 优先从 Storage 读取（后台下发的标记）
      const auditFlag = uni.getStorageSync('auditMode')
      if (auditFlag !== undefined && auditFlag !== null && auditFlag !== '') {
        isAuditMode.value = String(auditFlag) === 'true'
      }
    } catch {
      // Storage 读取失败，默认非审核模式
    }
    auditChecked.value = true
  }

  /** 设置审核模式 */
  function setAuditMode(enabled: boolean): void {
    isAuditMode.value = enabled
    try {
      uni.setStorageSync('auditMode', String(enabled))
    } catch {
      // 忽略
    }
  }

  return {
    isAuditMode,
    auditChecked,
    auditActive,
    auditReady,
    checkAuditMode,
    setAuditMode,
  }
})
