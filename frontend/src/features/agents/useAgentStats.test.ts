import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { useAgentStats } from './useAgentStats'
import type { AgentStats } from '@/api/types'

vi.mock('@/api/endpoints/agents', () => ({
  getAgentStats: vi.fn(),
}))

import * as agentsApi from '@/api/endpoints/agents'
const mockGetAgentStats = agentsApi.getAgentStats as ReturnType<typeof vi.fn>

const FAKE_STATS: AgentStats = {
  total_faqs: 100,
  pending_count: 5,
  approved_count: 20,
  synced_count: 70,
  draft_count: 3,
  rejected_count: 2,
  categories_count: 8,
}

beforeEach(() => { vi.clearAllMocks() })

describe('useAgentStats', () => {
  it('agentId 為 undefined 時不呼叫 API', () => {
    renderHook(() => useAgentStats(undefined))
    expect(mockGetAgentStats).not.toHaveBeenCalled()
  })

  it('成功載入統計資料', async () => {
    mockGetAgentStats.mockResolvedValueOnce(FAKE_STATS)
    const { result } = renderHook(() => useAgentStats('a1'))

    await waitFor(() => expect(result.current.loading).toBe(false))

    expect(result.current.stats).toEqual(FAKE_STATS)
    expect(result.current.error).toBeNull()
    expect(mockGetAgentStats).toHaveBeenCalledWith('a1')
  })

  it('API 失敗時設定 error，stats 為 null', async () => {
    mockGetAgentStats.mockRejectedValueOnce(new Error('500'))
    const { result } = renderHook(() => useAgentStats('a1'))

    await waitFor(() => expect(result.current.loading).toBe(false))

    expect(result.current.error).toBeTruthy()
    expect(result.current.stats).toBeNull()
  })

  it('agentId 變更時重新 fetch', async () => {
    mockGetAgentStats.mockResolvedValue(FAKE_STATS)
    const { rerender } = renderHook(
      ({ id }) => useAgentStats(id),
      { initialProps: { id: 'a1' as string | undefined } },
    )
    await waitFor(() => expect(mockGetAgentStats).toHaveBeenCalledTimes(1))

    rerender({ id: 'a2' })
    await waitFor(() => expect(mockGetAgentStats).toHaveBeenCalledTimes(2))
    expect(mockGetAgentStats).toHaveBeenLastCalledWith('a2')
  })
})
