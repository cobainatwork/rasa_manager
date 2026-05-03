import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { Agent } from '@/api/types'

interface AgentContextState {
  current: Agent | null
  setCurrent: (a: Agent | null) => void
}

// 唯一管理 currentAgent 的 store（B1 修正：useAuthStore 已不再保留 currentAgent）
export const useAgentContext = create<AgentContextState>()(
  persist(
    (set) => ({
      current: null,
      setCurrent: (a) => set({ current: a }),
    }),
    { name: 'rasa-kb-current-agent', version: 1 }
  )
)
