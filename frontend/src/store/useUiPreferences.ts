import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface UiPreferences {
  sidebarCollapsed: boolean
  toggleSidebar: () => void
  knowledgeRightPaneWidth: number
  setKnowledgeRightPaneWidth: (n: number) => void
}

export const useUiPreferences = create<UiPreferences>()(
  persist(
    (set) => ({
      sidebarCollapsed: false,
      toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
      knowledgeRightPaneWidth: 480,
      setKnowledgeRightPaneWidth: (n) => set({ knowledgeRightPaneWidth: n }),
    }),
    { name: 'rasa-kb-ui-prefs', version: 1 }
  )
)
