/**
 * 全局类型扩展声明
 */

/// <reference types="@dcloudio/types" />

declare module 'uni-app' {
  interface Uni {
    /** 全局离线状态 ref（由 App.vue 注入） */
    $globalOffline: import('vue').Ref<boolean>
  }
}

export {}
