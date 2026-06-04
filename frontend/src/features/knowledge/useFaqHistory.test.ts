import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import { useFaqHistory } from './useFaqHistory'
import type { FaqHistory } from '@/api/types'

vi.mock('@/api/endpoints/faqs', () => ({
  getHistory: vi.fn(),
  rollback: vi.fn(),
}))
vi.mock('sonner', () => ({ toast: { error: vi.fn(), success: vi.fn() } }))

import * as faqsApi from '@/api/endpoints/faqs'
const mockGetHistory = faqsApi.getHistory as ReturnType<typeof vi.fn>
const mockRollback = faqsApi.rollback as ReturnType<typeof vi.fn>

const FAKE_HISTORY: FaqHistory[] = [
  { id: 'h1', item_id: 'f1', version: 2, question: 'Q2', answer: 'A2', category_id: 'c1', saved_by: 'u1', action: 'update', action_reason: null, created_at: null },
  { id: 'h2', item_id: 'f1', version: 1, question: 'Q1', answer: 'A1', category_id: 'c1', saved_by: 'u1', action: 'create', action_reason: null, created_at: null },
]

beforeEach(() => { vi.clearAllMocks() })

describe('useFaqHistory', () => {
  it('agentId 或 faqId 缺少時 history 為空陣列', async () => {
    const { result } = renderHook(() => useFaqHistory(undefined, null))
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.history).toEqual([])
    expect(mockGetHistory).not.toHaveBeenCalled()
  })

  it('載入歷史紀錄', async () => {
    mockGetHistory.mockResolvedValueOnce(FAKE_HISTORY)
    const { result } = renderHook(() => useFaqHistory('a1', 'f1'))

    await waitFor(() => expect(result.current.loading).toBe(false))

    expect(result.current.history).toEqual(FAKE_HISTORY)
    expect(mockGetHistory).toHaveBeenCalledWith('a1', 'f1')
  })

  it('API 失敗時 history 為空陣列', async () => {
    mockGetHistory.mockRejectedValueOnce(new Error('500'))
    const { result } = renderHook(() => useFaqHistory('a1', 'f1'))

    await waitFor(() => expect(result.current.loading).toBe(false))

    expect(result.current.history).toEqual([])
  })

  it('rollback 呼叫 API 並 reload', async () => {
    mockGetHistory.mockResolvedValue(FAKE_HISTORY)
    mockRollback.mockResolvedValueOnce({})
    const { result } = renderHook(() => useFaqHistory('a1', 'f1'))
    await waitFor(() => expect(result.current.history).toHaveLength(2))

    await act(async () => {
      await result.current.rollback(1)
    })

    expect(mockRollback).toHaveBeenCalledWith('a1', 'f1', 1)
    expect(mockGetHistory).toHaveBeenCalledTimes(2)
  })

  it('rollback 失敗時呼叫 toast.error', async () => {
    const { toast } = await import('sonner')
    mockGetHistory.mockResolvedValue(FAKE_HISTORY)
    mockRollback.mockRejectedValueOnce(new Error('403'))
    const { result } = renderHook(() => useFaqHistory('a1', 'f1'))
    await waitFor(() => expect(result.current.history).toHaveLength(2))

    await act(async () => {
      await result.current.rollback(1)
    })

    expect(toast.error).toHaveBeenCalled()
  })
})
