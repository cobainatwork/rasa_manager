import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import { useUserManagement } from './useUserManagement'
import type { User } from '@/api/types'

vi.mock('@/api/endpoints/users', () => ({
  listUsers: vi.fn(),
}))
vi.mock('sonner', () => ({ toast: { error: vi.fn(), success: vi.fn() } }))

import * as usersApi from '@/api/endpoints/users'
const mockListUsers = usersApi.listUsers as ReturnType<typeof vi.fn>

const FAKE_USERS: User[] = [
  { id: 'u1', username: 'admin', is_superadmin: true,  is_active: true, created_at: '' },
  { id: 'u2', username: 'alice', is_superadmin: false, is_active: true, created_at: '' },
]

beforeEach(() => { vi.clearAllMocks() })

describe('useUserManagement', () => {
  it('初始載入使用者列表', async () => {
    mockListUsers.mockResolvedValueOnce(FAKE_USERS)
    const { result } = renderHook(() => useUserManagement())

    expect(result.current.loading).toBe(true)
    await waitFor(() => expect(result.current.loading).toBe(false))

    expect(result.current.users).toEqual(FAKE_USERS)
  })

  it('API 失敗時呼叫 toast.error', async () => {
    const { toast } = await import('sonner')
    mockListUsers.mockRejectedValueOnce(new Error('500'))
    const { result } = renderHook(() => useUserManagement())

    await waitFor(() => expect(result.current.loading).toBe(false))

    expect(toast.error).toHaveBeenCalled()
  })

  it('select 設定 selectedId 並回傳對應 selected 物件', async () => {
    mockListUsers.mockResolvedValueOnce(FAKE_USERS)
    const { result } = renderHook(() => useUserManagement())
    await waitFor(() => expect(result.current.users).toHaveLength(2))

    act(() => { result.current.select('u2') })

    expect(result.current.selectedId).toBe('u2')
    expect(result.current.selected?.username).toBe('alice')
  })

  it('select null 時 selected 為 null', async () => {
    mockListUsers.mockResolvedValueOnce(FAKE_USERS)
    const { result } = renderHook(() => useUserManagement())
    await waitFor(() => expect(result.current.users).toHaveLength(2))

    act(() => { result.current.select('u1') })
    act(() => { result.current.select(null) })

    expect(result.current.selectedId).toBeNull()
    expect(result.current.selected).toBeNull()
  })

  it('reload 重新呼叫 listUsers', async () => {
    mockListUsers.mockResolvedValue(FAKE_USERS)
    const { result } = renderHook(() => useUserManagement())
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(mockListUsers).toHaveBeenCalledTimes(1)

    await act(async () => { result.current.reload() })
    await waitFor(() => expect(result.current.loading).toBe(false))

    expect(mockListUsers).toHaveBeenCalledTimes(2)
  })

  it('selectedId 不存在於 users 時 selected 為 null', async () => {
    mockListUsers.mockResolvedValueOnce(FAKE_USERS)
    const { result } = renderHook(() => useUserManagement())
    await waitFor(() => expect(result.current.users).toHaveLength(2))

    act(() => { result.current.select('nonexistent') })

    expect(result.current.selected).toBeNull()
  })
})
