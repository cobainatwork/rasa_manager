import { create } from 'zustand'
import { apiClient } from '@/api/client'
import type { User, Agent } from '@/api/types'

interface AuthState {
  user: User | null
  currentAgent: Agent | null
  isLoading: boolean
  isInitialized: boolean

  login: (username: string, password: string) => Promise<void>
  logout: () => Promise<void>
  fetchMe: () => Promise<void>
  setCurrentAgent: (agent: Agent | null) => void
  initialize: () => Promise<void>
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  currentAgent: null,
  isLoading: false,
  isInitialized: false,

  login: async (username, password) => {
    set({ isLoading: true })
    try {
      const resp = await apiClient.post('/api/v1/auth/login', { username, password })
      const data = resp.data?.data
      if (data) {
        // 取得完整 user 資訊（含 created_at 等）
        await get().fetchMe()
      }
    } finally {
      set({ isLoading: false })
    }
  },

  logout: async () => {
    try {
      await apiClient.post('/api/v1/auth/logout')
    } catch {
      // 即使後端失敗也清除本地狀態
    }
    set({ user: null, currentAgent: null })
  },

  fetchMe: async () => {
    const resp = await apiClient.get('/api/v1/auth/me')
    set({ user: resp.data?.data ?? null })
  },

  setCurrentAgent: (agent) => set({ currentAgent: agent }),

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
