import { create } from 'zustand'
import { apiClient } from '@/api/client'
import type { User } from '@/api/types'

interface AuthState {
  user: User | null
  isLoading: boolean
  isInitialized: boolean

  login: (username: string, password: string) => Promise<void>
  logout: () => Promise<void>
  fetchMe: () => Promise<void>
  initialize: () => Promise<void>
}

// 注意：currentAgent 由 useAgentContext 統一管理（B1 修正）。
// 此 store 僅負責「身分驗證」相關狀態，不再保留 agent 欄位以避免雙 source of truth。
export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  isLoading: false,
  isInitialized: false,

  login: async (username, password) => {
    set({ isLoading: true })
    try {
      await apiClient.post('/api/v1/auth/login', { username, password })
      // 登入成功後立即抓完整 user 資料；失敗會 rethrow 讓呼叫端取得錯誤訊息
      await get().fetchMe()
    } finally {
      set({ isLoading: false })
    }
  },

  logout: async () => {
    try {
      await apiClient.post('/api/v1/auth/logout')
    } catch (e) {
      // 即使後端失敗也清除本地狀態，但記錄警告以利診斷
      console.warn('[auth] logout backend call failed', e)
    }
    set({ user: null })
  },

  fetchMe: async () => {
    const resp = await apiClient.get('/api/v1/auth/me')
    set({ user: resp.data?.data ?? null })
  },

  initialize: async () => {
    if (get().isInitialized) return
    try {
      await get().fetchMe()
    } catch {
      // 未登入 → user 維持 null
    } finally {
      set({ isInitialized: true })
    }
  },
}))
