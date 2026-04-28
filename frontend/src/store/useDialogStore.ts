import { create } from 'zustand'

type Resolver = (value: boolean | string | null) => void

export interface DialogEntry {
  id: string
  type: 'confirm' | 'prompt'
  message: string
  defaultValue?: string
  resolve: Resolver
}

interface DialogStore {
  dialogs: DialogEntry[]
  showConfirm: (message: string) => Promise<boolean>
  showPrompt: (message: string, defaultValue?: string) => Promise<string | null>
  _resolve: (id: string, value: boolean | string | null) => void
}

export const useDialogStore = create<DialogStore>((set, get) => ({
  dialogs: [],

  showConfirm: (message) =>
    new Promise<boolean>((resolve) => {
      const id = Math.random().toString(36).slice(2)
      set((s) => ({
        dialogs: [...s.dialogs, { id, type: 'confirm', message, resolve: resolve as Resolver }],
      }))
    }),

  showPrompt: (message, defaultValue = '') =>
    new Promise<string | null>((resolve) => {
      const id = Math.random().toString(36).slice(2)
      set((s) => ({
        dialogs: [
          ...s.dialogs,
          { id, type: 'prompt', message, defaultValue, resolve: resolve as Resolver },
        ],
      }))
    }),

  _resolve: (id, value) => {
    const entry = get().dialogs.find((d) => d.id === id)
    if (entry) entry.resolve(value)
    set((s) => ({ dialogs: s.dialogs.filter((d) => d.id !== id) }))
  },
}))
