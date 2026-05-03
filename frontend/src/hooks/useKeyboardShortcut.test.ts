import { describe, it, expect, vi } from 'vitest'
import { renderHook } from '@testing-library/react'
import { useKeyboardShortcut } from './useKeyboardShortcut'

describe('useKeyboardShortcut', () => {
  it('觸發指定按鍵的 callback', () => {
    const cb = vi.fn()
    renderHook(() => useKeyboardShortcut('/', cb))
    window.dispatchEvent(new KeyboardEvent('keydown', { key: '/' }))
    expect(cb).toHaveBeenCalledTimes(1)
  })

  it('輸入框聚焦時不觸發', () => {
    const cb = vi.fn()
    renderHook(() => useKeyboardShortcut('/', cb))
    const input = document.createElement('input')
    document.body.appendChild(input)
    input.focus()
    input.dispatchEvent(new KeyboardEvent('keydown', { key: '/', bubbles: true }))
    expect(cb).not.toHaveBeenCalled()
    input.remove()
  })

  it('支援 modifier（Cmd/Ctrl + S）', () => {
    const cb = vi.fn()
    renderHook(() => useKeyboardShortcut('s', cb, { meta: true }))
    window.dispatchEvent(new KeyboardEvent('keydown', { key: 's', metaKey: true }))
    expect(cb).toHaveBeenCalledTimes(1)
  })
})
