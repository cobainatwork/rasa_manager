import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useToastStore } from './useToastStore'

beforeEach(() => {
  useToastStore.setState({ toasts: [] })
  vi.useFakeTimers()
})

describe('useToastStore', () => {
  it('addToast 新增一則 toast', () => {
    useToastStore.getState().addToast('測試訊息')
    expect(useToastStore.getState().toasts).toHaveLength(1)
    expect(useToastStore.getState().toasts[0].message).toBe('測試訊息')
  })

  it('addToast 預設 type 為 info', () => {
    useToastStore.getState().addToast('hello')
    expect(useToastStore.getState().toasts[0].type).toBe('info')
  })

  it('addToast 可指定 type', () => {
    useToastStore.getState().addToast('錯誤', 'error')
    expect(useToastStore.getState().toasts[0].type).toBe('error')
  })

  it('4 秒後自動移除', () => {
    useToastStore.getState().addToast('自動消失')
    expect(useToastStore.getState().toasts).toHaveLength(1)
    vi.advanceTimersByTime(4000)
    expect(useToastStore.getState().toasts).toHaveLength(0)
  })

  it('removeToast 手動移除指定 id', () => {
    useToastStore.getState().addToast('訊息 A')
    useToastStore.getState().addToast('訊息 B')
    const id = useToastStore.getState().toasts[0].id
    useToastStore.getState().removeToast(id)
    expect(useToastStore.getState().toasts).toHaveLength(1)
    expect(useToastStore.getState().toasts[0].message).toBe('訊息 B')
  })

  it('多則 toast 可同時存在', () => {
    useToastStore.getState().addToast('A')
    useToastStore.getState().addToast('B')
    useToastStore.getState().addToast('C')
    expect(useToastStore.getState().toasts).toHaveLength(3)
  })

  it('每則 toast id 唯一', () => {
    useToastStore.getState().addToast('A')
    useToastStore.getState().addToast('B')
    const ids = useToastStore.getState().toasts.map((t) => t.id)
    expect(new Set(ids).size).toBe(ids.length)
  })
})
