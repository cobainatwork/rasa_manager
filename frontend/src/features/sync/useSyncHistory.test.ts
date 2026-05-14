import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import { useSyncHistory } from './useSyncHistory'
import type { SyncLogHistoryItem } from '@/api/types'

vi.mock('@/api/endpoints/sync', () => ({
  getSyncHistory: vi.fn(),
}))

import * as syncApi from '@/api/endpoints/sync'
const mockGetSyncHistory = syncApi.getSyncHistory as ReturnType<typeof vi.fn>

const FAKE_ITEMS: SyncLogHistoryItem[] = [
  {
    id: 'sl1', status: 'completed', triggered_by_username: 'admin',
    started_at: '2026-01-01T00:00:00Z', finished_at: '2026-01-01T00:01:00Z',
    duration_sec: 60, items_count: 10, output_file: null, stdout: null, stderr: null,
  },
]

beforeEach(() => { vi.clearAllMocks() })

describe('useSyncHistory', () => {
  it('agentId 為 undefined 時不呼叫 API', () => {
    renderHook(() => useSyncHistory(undefined))
    expect(mockGetSyncHistory).not.toHaveBeenCalled()
  })

  it('成功載入歷史紀錄', async () => {
    mockGetSyncHistory.mockResolvedValueOnce(FAKE_ITEMS)
    const { result } = renderHook(() => useSyncHistory('a1'))

    await waitFor(() => expect(result.current.loading).toBe(false))

    expect(result.current.items).toEqual(FAKE_ITEMS)
    expect(result.current.error).toBeNull()
    expect(mockGetSyncHistory).toHaveBeenCalledWith('a1', 20)
  })

  it('API 失敗時設定 error 並 items 為空陣列', async () => {
    mockGetSyncHistory.mockRejectedValueOnce(new Error('500'))
    const { result } = renderHook(() => useSyncHistory('a1'))

    await waitFor(() => expect(result.current.loading).toBe(false))

    expect(result.current.error).toBeTruthy()
    expect(result.current.items).toEqual([])
  })

  it('reload 可手動重新載入', async () => {
    mockGetSyncHistory.mockResolvedValue(FAKE_ITEMS)
    const { result } = renderHook(() => useSyncHistory('a1'))
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(mockGetSyncHistory).toHaveBeenCalledTimes(1)

    await act(async () => { result.current.reload() })
    await waitFor(() => expect(result.current.loading).toBe(false))

    expect(mockGetSyncHistory).toHaveBeenCalledTimes(2)
  })
})
