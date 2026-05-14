import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import { usePendingFaqs } from './usePendingFaqs'
import { useAuthStore } from '@/store/useAuthStore'
import type { FaqListResponse, User } from '@/api/types'

vi.mock('@/api/endpoints/faqs', () => ({
  listFaqs: vi.fn(),
}))

import * as faqsApi from '@/api/endpoints/faqs'
const mockListFaqs = faqsApi.listFaqs as ReturnType<typeof vi.fn>

const SUPERADMIN: User = { id: 'u1', username: 'admin', is_superadmin: true, is_active: true, created_at: '' }
const EDITOR: User    = { id: 'u2', username: 'editor', is_superadmin: false, is_active: true, created_at: '' }

const FAKE_RESP: FaqListResponse = {
  items: [
    {
      id: 'f1', agent_id: 'a1', category_id: 'c1',
      question: 'Q', answer: 'A', tags: [], status: 'pending',
      version: 1, locked_by: null, locked_by_username: null, locked_at: null,
      created_by: 'u1', created_at: null, updated_at: null,
    },
  ],
  total: 1, page: 1, per_page: 5,
}

beforeEach(() => {
  vi.clearAllMocks()
  useAuthStore.setState({ user: SUPERADMIN })
})

describe('usePendingFaqs', () => {
  it('agentId 為 undefined 時不呼叫 API', () => {
    renderHook(() => usePendingFaqs(undefined))
    expect(mockListFaqs).not.toHaveBeenCalled()
  })

  it('成功載入待審核項目', async () => {
    mockListFaqs.mockResolvedValueOnce(FAKE_RESP)
    const { result } = renderHook(() => usePendingFaqs('a1'))

    await waitFor(() => expect(result.current.loading).toBe(false))

    expect(result.current.items).toHaveLength(1)
    expect(result.current.error).toBeNull()
  })

  it('API 呼叫帶 status: pending 與 per_page: 5', async () => {
    mockListFaqs.mockResolvedValueOnce(FAKE_RESP)
    renderHook(() => usePendingFaqs('a1'))

    await waitFor(() => expect(mockListFaqs).toHaveBeenCalled())

    expect(mockListFaqs).toHaveBeenCalledWith('a1', {
      status: 'pending',
      per_page: 5,
    })
  })

  it('API 失敗時設定 error，items 為空陣列', async () => {
    mockListFaqs.mockRejectedValueOnce(new Error('500'))
    const { result } = renderHook(() => usePendingFaqs('a1'))

    await waitFor(() => expect(result.current.loading).toBe(false))

    expect(result.current.error).toBeTruthy()
    expect(result.current.items).toEqual([])
  })

  it('reload 可手動重新載入', async () => {
    mockListFaqs.mockResolvedValue(FAKE_RESP)
    const { result } = renderHook(() => usePendingFaqs('a1'))
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(mockListFaqs).toHaveBeenCalledTimes(1)

    await act(async () => { result.current.reload() })
    await waitFor(() => expect(result.current.loading).toBe(false))

    expect(mockListFaqs).toHaveBeenCalledTimes(2)
  })

  it('editor 角色也使用 pending status', async () => {
    useAuthStore.setState({ user: EDITOR })
    mockListFaqs.mockResolvedValueOnce(FAKE_RESP)
    renderHook(() => usePendingFaqs('a1'))

    await waitFor(() => expect(mockListFaqs).toHaveBeenCalled())

    expect(mockListFaqs).toHaveBeenCalledWith('a1', {
      status: 'pending',
      per_page: 5,
    })
  })
})
