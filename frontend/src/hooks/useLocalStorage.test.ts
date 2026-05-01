import { describe, it, expect, beforeEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useLocalStorage } from './useLocalStorage'

describe('useLocalStorage', () => {
  beforeEach(() => localStorage.clear())

  it('初始值來自 localStorage 或預設', () => {
    const { result } = renderHook(() => useLocalStorage('k', 'default'))
    expect(result.current[0]).toBe('default')
  })

  it('setter 同步寫入 localStorage', () => {
    const { result } = renderHook(() => useLocalStorage('k', 'a'))
    act(() => result.current[1]('b'))
    expect(result.current[0]).toBe('b')
    expect(localStorage.getItem('k')).toBe('"b"')
  })

  it('已存在的 localStorage 值優先', () => {
    localStorage.setItem('k', '"saved"')
    const { result } = renderHook(() => useLocalStorage('k', 'default'))
    expect(result.current[0]).toBe('saved')
  })

  it('functional updater 支援（I10）', () => {
    const { result } = renderHook(() => useLocalStorage<number>('counter', 0))
    act(() => result.current[1]((prev) => prev + 1))
    act(() => result.current[1]((prev) => prev + 2))
    expect(result.current[0]).toBe(3)
    expect(localStorage.getItem('counter')).toBe('3')
  })
})
