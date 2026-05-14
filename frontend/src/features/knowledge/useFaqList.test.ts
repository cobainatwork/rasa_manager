import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import { useFaqList } from './useFaqList'
import type { FaqListResponse } from '@/api/types'

vi.mock('@/api/endpoints/faqs', () => ({
  listFaqs: vi.fn(),
}))

import * as faqsApi from '@/api/endpoints/faqs'
const mockListFaqs = faqsApi.listFaqs as ReturnType<typeof vi.fn>

const EMPTY_FILTERS = { status: '', category_id: '', q: '', page: 1 }

const FAKE_RESP: FaqListResponse = {
  items: [
    {
      id: 'f1', agent_id: 'a1', category_id: 'c1',
      question: 'Q', answer: 'A', tags: [], status: 'draft',
      version: 1, locked_by: null, locked_by_username: null, locked_at: null,
      created_by: 'u1', created_at: null, updated_at: null,
    },
  ],
  total: 1,
  page: 1,
  per_page: 20,
}

beforeEach(() => { vi.clearAllMocks() })

describe('useFaqList', () => {
  it('agentId 為 undefined 時不呼叫 API', () => {
    renderHook(() => useFaqList(undefined, EMPTY_FILTERS))
    expect(mockListFaqs).not.toHaveBeenCalled()
  })

  it('agentId 存在時呼叫 listFaqs 並更新 data', async () => {
    mockListFaqs.mockResolvedValueOnce(FAKE_RESP)
    const { result } = renderHook(() => useFaqList('a1', EMPTY_FILTERS))

    await waitFor(() => expect(result.current.loading).toBe(false))

    expect(result.current.data).toEqual(FAKE_RESP)
    expect(result.current.error).toBeNull()
  })

  it('API 失敗時設定 error 並清除 loading', async () => {
    mockListFaqs.mockRejectedValueOnce(new Error('500'))
    const { result } = renderHook(() => useFaqList('a1', EMPTY_FILTERS))

    await waitFor(() => expect(result.current.loading).toBe(false))

    expect(result.current.error).toBeTruthy()
    expect(result.current.data).toBeNull()
  })

  it('totalPages 最小為 1', async () => {
    mockListFaqs.mockResolvedValueOnce({ ...FAKE_RESP, total: 0 })
    const { result } = renderHook(() => useFaqList('a1', EMPTY_FILTERS))

    await waitFor(() => expect(result.current.loading).toBe(false))

    expect(result.current.totalPages).toBe(1)
  })

  it('totalPages 根據 total 正確計算（21 筆 / 20 = 2 頁）', async () => {
    mockListFaqs.mockResolvedValueOnce({ ...FAKE_RESP, total: 21 })
    const { result } = renderHook(() => useFaqList('a1', EMPTY_FILTERS))

    await waitFor(() => expect(result.current.loading).toBe(false))

    expect(result.current.totalPages).toBe(2)
  })

  it('filters.status 改變會重新 fetch', async () => {
    mockListFaqs.mockResolvedValue(FAKE_RESP)
    const { rerender } = renderHook(
      ({ filters }) => useFaqList('a1', filters),
      { initialProps: { filters: EMPTY_FILTERS } },
    )
    await waitFor(() => expect(mockListFaqs).toHaveBeenCalledTimes(1))

    rerender({ filters: { ...EMPTY_FILTERS, status: 'pending' } })
    await waitFor(() => expect(mockListFaqs).toHaveBeenCalledTimes(2))

    const secondCall = mockListFaqs.mock.calls[1]
    expect(secondCall[1]).toMatchObject({ status: 'pending' })
  })

  it('q 改變後等 debounce 300ms 才 fetch', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    try {
      mockListFaqs.mockResolvedValue(FAKE_RESP)
      const { rerender } = renderHook(
        ({ filters }) => useFaqList('a1', filters),
        { initialProps: { filters: EMPTY_FILTERS } },
      )
      // 等初始 fetch 完成（q = '' 無需 debounce）
      await act(async () => { vi.runAllTimers() })
      await waitFor(() => expect(mockListFaqs).toHaveBeenCalledTimes(1))

      rerender({ filters: { ...EMPTY_FILTERS, q: 'hello' } })
      // 尚未到 300ms，不應觸發第二次 fetch
      expect(mockListFaqs).toHaveBeenCalledTimes(1)

      // 推進 300ms 讓 debounce 觸發
      await act(async () => { vi.advanceTimersByTime(300) })
      await waitFor(() => expect(mockListFaqs).toHaveBeenCalledTimes(2))
    } finally {
      vi.useRealTimers()
    }
  })
})
