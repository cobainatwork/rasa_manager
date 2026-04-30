import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { Agent } from '@/api/types'

interface AgentContextState {
  current: Agent | null
  setCurrent: (a: Agent | null) => void
}

export const useAgentContext = create<AgentContextState>()(
  persist(
    (set) => ({
      current: null,
      setCurrent: (a) => set({ current: a }),
    }),
    { name: 'rasa-kb-current-agent' }
  )
)
