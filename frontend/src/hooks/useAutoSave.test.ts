import { describe, it, expect, vi } from 'vitest'
import { renderHook, act, waitFor } from '@testing-library/react'
import { useAutoSave } from './useAutoSave'

describe('useAutoSave', () => {
  it('debounce 300ms 後呼叫 saveFn，完成後 status 變 saved', async () => {
    vi.useFakeTimers()
    const saveFn = vi.fn().mockResolvedValue(undefined)
    const { result, rerender } = renderHook(
      ({ value }) => useAutoSave(value, saveFn, { debounceMs: 300 }),
      { initialProps: { value: 'a' } }
    )
    rerender({ value: 'b' })
    expect(saveFn).not.toHaveBeenCalled()
    await act(async () => { vi.advanceTimersByTime(300) })
    expect(saveFn).toHaveBeenCalledWith('b')
    expect(result.current.status).toBe('saved')
    vi.useRealTimers()
  })

  it('saveFn 失敗時 status 變 error', async () => {
    vi.useFakeTimers()
    const saveFn = vi.fn().mockRejectedValue(new Error('fail'))
    const { result, rerender } = renderHook(
      ({ value }) => useAutoSave(value, saveFn, { debounceMs: 0 }),
      { initialProps: { value: 'a' } }
    )
    rerender({ value: 'b' })
    await act(async () => {
      vi.advanceTimersByTime(0)
      await Promise.resolve()
    })
    expect(result.current.status).toBe('error')
    vi.useRealTimers()
  })
})
