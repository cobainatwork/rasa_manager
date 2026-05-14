import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import { useSyncTrigger } from './useSyncTrigger'
import type { SyncLog } from '@/api/types'

vi.mock('@/api/endpoints/sync', () => ({
  triggerSync: vi.fn(),
  getSyncStatus: vi.fn(),
}))
vi.mock('sonner', () => ({ toast: { error: vi.fn(), success: vi.fn() } }))

import * as syncApi from '@/api/endpoints/sync'
const mockTriggerSync = syncApi.triggerSync as ReturnType<typeof vi.fn>
const mockGetSyncStatus = syncApi.getSyncStatus as ReturnType<typeof vi.fn>

const FAKE_LOG_RUNNING: SyncLog = {
  id: 'sl1', agent_id: 'a1', triggered_by: null, celery_task_id: 'ct1',
  status: 'running', items_count: 0, output_file: null,
  stdout: null, stderr: null, started_at: null, finished_at: null,
  duration_sec: null, created_at: null,
}
const FAKE_LOG_COMPLETED: SyncLog = { ...FAKE_LOG_RUNNING, status: 'completed', items_count: 5 }

beforeEach(() => { vi.clearAllMocks() })

describe('useSyncTrigger — trigger', () => {
  it('agentId 為 undefined 時 trigger 不執行', async () => {
    const { result } = renderHook(() => useSyncTrigger(undefined))
    await act(async () => { await result.current.trigger() })
    expect(mockTriggerSync).not.toHaveBeenCalled()
  })

  it('trigger 成功後設定 activeLog 並顯示 toast.success', async () => {
    const { toast } = await import('sonner')
    mockTriggerSync.mockResolvedValueOnce({ task_id: 'ct1', sync_log_id: 'sl1' })
    mockGetSyncStatus.mockResolvedValueOnce(FAKE_LOG_RUNNING)

    const { result } = renderHook(() => useSyncTrigger('a1'))

    await act(async () => { await result.current.trigger() })

    expect(result.current.activeLog).toEqual(FAKE_LOG_RUNNING)
    expect(result.current.triggering).toBe(false)
    expect(toast.success).toHaveBeenCalled()
  })

  it('trigger 失敗時呼叫 toast.error，triggering 歸零', async () => {
    const { toast } = await import('sonner')
    mockTriggerSync.mockRejectedValueOnce(new Error('500'))

    const { result } = renderHook(() => useSyncTrigger('a1'))

    await act(async () => { await result.current.trigger() })

    expect(toast.error).toHaveBeenCalled()
    expect(result.current.triggering).toBe(false)
    expect(result.current.activeLog).toBeNull()
  })

  it('trigger 執行期間 triggering 為 true', async () => {
    let capturedTriggering = false
    mockTriggerSync.mockImplementationOnce(async () => {
      capturedTriggering = true
      return { task_id: null, sync_log_id: 'sl1' }
    })
    mockGetSyncStatus.mockResolvedValueOnce(FAKE_LOG_RUNNING)

    const { result } = renderHook(() => useSyncTrigger('a1'))
    await act(async () => { await result.current.trigger() })

    expect(capturedTriggering).toBe(true)
  })
})

describe('useSyncTrigger — 輪詢', () => {
  afterEach(() => { vi.useRealTimers() })

  it('activeLog 狀態為 running 時啟動輪詢，completed 後停止', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })

    mockTriggerSync.mockResolvedValueOnce({ task_id: 'ct1', sync_log_id: 'sl1' })
    mockGetSyncStatus
      .mockResolvedValueOnce(FAKE_LOG_RUNNING)    // trigger 後的初始狀態
      .mockResolvedValueOnce(FAKE_LOG_COMPLETED)  // 第一次輪詢

    const { result } = renderHook(() => useSyncTrigger('a1'))

    await act(async () => { await result.current.trigger() })
    expect(result.current.activeLog?.status).toBe('running')

    // 推進 2 秒（POLL_INTERVAL = 2000）讓 setInterval 觸發
    await act(async () => { vi.advanceTimersByTime(2001) })
    await waitFor(() => expect(result.current.activeLog?.status).toBe('completed'))
  })

  it('activeLog 為 null 時不啟動輪詢', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    const { result } = renderHook(() => useSyncTrigger('a1'))

    expect(result.current.activeLog).toBeNull()
    await act(async () => { vi.advanceTimersByTime(4000) })

    expect(mockGetSyncStatus).not.toHaveBeenCalled()
  })
})

describe('useSyncTrigger — clearActive', () => {
  it('clearActive 清除 activeLog', async () => {
    mockTriggerSync.mockResolvedValueOnce({ task_id: 'ct1', sync_log_id: 'sl1' })
    mockGetSyncStatus.mockResolvedValueOnce(FAKE_LOG_COMPLETED)

    const { result } = renderHook(() => useSyncTrigger('a1'))
    await act(async () => { await result.current.trigger() })
    expect(result.current.activeLog).not.toBeNull()

    act(() => { result.current.clearActive() })
    expect(result.current.activeLog).toBeNull()
  })
})
