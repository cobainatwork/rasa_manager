import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import { useFaqDetail } from './useFaqDetail'
import type { Faq } from '@/api/types'

vi.mock('@/api/endpoints/faqs', () => ({
  getFaq: vi.fn(),
  updateFaq: vi.fn(),
}))
vi.mock('sonner', () => ({ toast: { error: vi.fn(), success: vi.fn() } }))

import * as faqsApi from '@/api/endpoints/faqs'
const mockGetFaq = faqsApi.getFaq as ReturnType<typeof vi.fn>
const mockUpdateFaq = faqsApi.updateFaq as ReturnType<typeof vi.fn>

const FAKE_FAQ: Faq = {
  id: 'f1', agent_id: 'a1', category_id: 'c1',
  question: 'Q', answer: 'A', tags: [], status: 'draft',
  version: 1, locked_by: null, locked_by_username: null, locked_at: null,
  created_by: 'u1', created_at: null, updated_at: null,
}

beforeEach(() => { vi.clearAllMocks() })

describe('useFaqDetail', () => {
  it('agentId 或 faqId 為 null 時不呼叫 API，faq 為 null', async () => {
    const { result } = renderHook(() => useFaqDetail(undefined, null))
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(mockGetFaq).not.toHaveBeenCalled()
    expect(result.current.faq).toBeNull()
  })

  it('agentId 與 faqId 均有值時載入 FAQ', async () => {
    mockGetFaq.mockResolvedValueOnce(FAKE_FAQ)
    const { result } = renderHook(() => useFaqDetail('a1', 'f1'))

    await waitFor(() => expect(result.current.loading).toBe(false))

    expect(result.current.faq).toEqual(FAKE_FAQ)
    expect(mockGetFaq).toHaveBeenCalledWith('a1', 'f1')
  })

  it('API 失敗時呼叫 toast.error，loading 歸零', async () => {
    const { toast } = await import('sonner')
    mockGetFaq.mockRejectedValueOnce(new Error('404'))
    const { result } = renderHook(() => useFaqDetail('a1', 'f1'))

    await waitFor(() => expect(result.current.loading).toBe(false))

    expect(toast.error).toHaveBeenCalled()
  })

  it('update 呼叫 updateFaq 並觸發 reload', async () => {
    mockGetFaq.mockResolvedValue(FAKE_FAQ)
    mockUpdateFaq.mockResolvedValueOnce({ ...FAKE_FAQ, question: 'Q2' })
    const { result } = renderHook(() => useFaqDetail('a1', 'f1'))
    await waitFor(() => expect(result.current.faq).toEqual(FAKE_FAQ))

    await act(async () => {
      await result.current.update({ question: 'Q2' })
    })

    expect(mockUpdateFaq).toHaveBeenCalledWith('a1', 'f1', { question: 'Q2' })
    // reload 重新呼叫 getFaq
    expect(mockGetFaq).toHaveBeenCalledTimes(2)
  })

  it('update 在 agentId / faqId 為 undefined 時不執行', async () => {
    const { result } = renderHook(() => useFaqDetail(undefined, null))
    await act(async () => {
      await result.current.update({ question: 'Q2' })
    })
    expect(mockUpdateFaq).not.toHaveBeenCalled()
  })

  it('onUpdated callback 在 update 後被呼叫', async () => {
    mockGetFaq.mockResolvedValue(FAKE_FAQ)
    mockUpdateFaq.mockResolvedValueOnce(FAKE_FAQ)
    const onUpdated = vi.fn()
    const { result } = renderHook(() => useFaqDetail('a1', 'f1', onUpdated))
    await waitFor(() => expect(result.current.faq).toBeTruthy())

    await act(async () => {
      await result.current.update({ answer: 'A2' })
    })

    expect(onUpdated).toHaveBeenCalledTimes(1)
  })
})
