import { describe, it, expect, beforeEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import React from 'react'
import { useFaqFilter } from './useFaqFilter'

function wrapper({ children }: { children: React.ReactNode }) {
  return React.createElement(MemoryRouter, null, children)
}

beforeEach(() => {
  localStorage.clear()
})

describe('useFaqFilter — 初始狀態', () => {
  it('URL 無參數時回傳空預設值', () => {
    const { result } = renderHook(() => useFaqFilter('a1'), { wrapper })
    expect(result.current.filters).toEqual({
      status: '',
      category_id: '',
      q: '',
      page: 1,
    })
  })
})

describe('useFaqFilter — setFilter', () => {
  it('setFilter 更新單一欄位', () => {
    const { result } = renderHook(() => useFaqFilter('a1'), { wrapper })

    act(() => {
      result.current.setFilter({ status: 'pending' })
    })

    expect(result.current.filters.status).toBe('pending')
  })

  it('setFilter 切換 status 時 page 重設為 1', () => {
    const { result } = renderHook(() => useFaqFilter('a1'), { wrapper })

    act(() => {
      result.current.setFilter({ page: 3 })
    })
    expect(result.current.filters.page).toBe(3)

    act(() => {
      result.current.setFilter({ status: 'approved' })
    })
    expect(result.current.filters.page).toBe(1)
  })

  it('setFilter 空字串值會從 URL 移除', () => {
    const { result } = renderHook(() => useFaqFilter('a1'), { wrapper })

    act(() => {
      result.current.setFilter({ status: 'pending' })
    })
    expect(result.current.filters.status).toBe('pending')

    act(() => {
      result.current.setFilter({ status: '' })
    })
    expect(result.current.filters.status).toBe('')
  })
})

describe('useFaqFilter — clearAll', () => {
  it('clearAll 清除所有篩選', () => {
    const { result } = renderHook(() => useFaqFilter('a1'), { wrapper })

    act(() => {
      result.current.setFilter({ status: 'pending', q: 'hello', page: 2 })
    })

    act(() => {
      result.current.clearAll()
    })

    expect(result.current.filters).toEqual({
      status: '',
      category_id: '',
      q: '',
      page: 1,
    })
  })

  it('clearAll 同時清除 localStorage', () => {
    localStorage.setItem('kb_filters_a1', JSON.stringify({ status: 'pending' }))
    const { result } = renderHook(() => useFaqFilter('a1'), { wrapper })

    act(() => {
      result.current.clearAll()
    })

    expect(localStorage.getItem('kb_filters_a1')).toBeNull()
  })
})

describe('useFaqFilter — localStorage 持久化', () => {
  it('有篩選條件時儲存至 localStorage', () => {
    const { result } = renderHook(() => useFaqFilter('a1'), { wrapper })

    act(() => {
      result.current.setFilter({ status: 'approved' })
    })

    const saved = JSON.parse(localStorage.getItem('kb_filters_a1') ?? '{}')
    expect(saved.status).toBe('approved')
  })

  it('所有條件為預設值時移除 localStorage', () => {
    localStorage.setItem('kb_filters_a1', JSON.stringify({ status: 'pending' }))
    const { result } = renderHook(() => useFaqFilter('a1'), { wrapper })

    act(() => {
      result.current.setFilter({ status: '' })
    })

    expect(localStorage.getItem('kb_filters_a1')).toBeNull()
  })
})
