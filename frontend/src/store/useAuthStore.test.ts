import { describe, it, expect, beforeEach, vi } from 'vitest'
import { useAuthStore } from './useAuthStore'
import { apiClient } from '@/api/client'
import type { User } from '@/api/types'

// mock apiClient
vi.mock('@/api/client', () => ({
  apiClient: {
    post: vi.fn(),
    get: vi.fn(),
  },
}))

const mockApiClient = apiClient as unknown as {
  post: ReturnType<typeof vi.fn>
  get: ReturnType<typeof vi.fn>
}

const FAKE_USER: User = {
  id: 'uid-001',
  username: 'admin',
  is_superadmin: true,
  is_active: true,
  created_at: '2026-01-01T00:00:00Z',
}

beforeEach(() => {
  useAuthStore.setState({
    user: null,
    isLoading: false,
    isInitialized: false,
  })
  vi.clearAllMocks()
})

describe('useAuthStore — state shape', () => {
  it('state 不應包含 currentAgent / setCurrentAgent（B1：唯一 source 由 useAgentContext 提供）', () => {
    const state = useAuthStore.getState() as unknown as Record<string, unknown>
    expect('currentAgent' in state).toBe(false)
    expect('setCurrentAgent' in state).toBe(false)
  })

  it('state 僅暴露 auth 相關欄位', () => {
    const state = useAuthStore.getState()
    expect(Object.keys(state).sort()).toEqual(
      ['fetchMe', 'initialize', 'isInitialized', 'isLoading', 'login', 'logout', 'user'].sort(),
    )
  })
})

describe('useAuthStore — login', () => {
  it('login 成功後呼叫 fetchMe 並設定 user', async () => {
    mockApiClient.post.mockResolvedValueOnce({ data: { data: { username: 'admin' } } })
    mockApiClient.get.mockResolvedValueOnce({ data: { data: FAKE_USER } })

    await useAuthStore.getState().login('admin', 'Admin1234')

    expect(mockApiClient.post).toHaveBeenCalledWith('/api/v1/auth/login', {
      username: 'admin',
      password: 'Admin1234',
    })
    expect(useAuthStore.getState().user?.username).toBe('admin')
    expect(useAuthStore.getState().isLoading).toBe(false)
  })

  it('login 一律呼叫 fetchMe（不再依賴 if(data) 死碼，I3）', async () => {
    mockApiClient.post.mockResolvedValueOnce({ data: {} })
    mockApiClient.get.mockResolvedValueOnce({ data: { data: FAKE_USER } })

    await useAuthStore.getState().login('admin', 'Admin1234')

    expect(mockApiClient.get).toHaveBeenCalledTimes(1)
    expect(useAuthStore.getState().user).toEqual(FAKE_USER)
  })

  it('login API 失敗會 rethrow，且 isLoading 仍歸零', async () => {
    mockApiClient.post.mockRejectedValueOnce(new Error('Network Error'))

    await expect(useAuthStore.getState().login('admin', 'wrong')).rejects.toThrow('Network Error')
    expect(useAuthStore.getState().isLoading).toBe(false)
  })

  it('login 期間 isLoading 為 true', async () => {
    let loadingDuringCall = false
    mockApiClient.post.mockImplementationOnce(async () => {
      loadingDuringCall = useAuthStore.getState().isLoading
      return { data: {} }
    })
    mockApiClient.get.mockResolvedValueOnce({ data: { data: FAKE_USER } })

    await useAuthStore.getState().login('admin', 'Admin1234')

    expect(loadingDuringCall).toBe(true)
  })
})

describe('useAuthStore — logout', () => {
  it('logout 後清除 user', async () => {
    useAuthStore.setState({ user: FAKE_USER })
    mockApiClient.post.mockResolvedValueOnce({})

    await useAuthStore.getState().logout()

    expect(useAuthStore.getState().user).toBeNull()
  })

  it('logout 即使後端失敗也清除本地狀態（並輸出 warning，I4）', async () => {
    useAuthStore.setState({ user: FAKE_USER })
    mockApiClient.post.mockRejectedValueOnce(new Error('500'))
    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})

    await useAuthStore.getState().logout()

    expect(useAuthStore.getState().user).toBeNull()
    expect(warnSpy).toHaveBeenCalledWith('[auth] logout backend call failed', expect.any(Error))
    warnSpy.mockRestore()
  })
})

describe('useAuthStore — fetchMe', () => {
  it('fetchMe 成功後更新 user', async () => {
    mockApiClient.get.mockResolvedValueOnce({ data: { data: FAKE_USER } })

    await useAuthStore.getState().fetchMe()

    expect(useAuthStore.getState().user).toEqual(FAKE_USER)
  })

  it('fetchMe 回傳 null data 時 user 設為 null', async () => {
    mockApiClient.get.mockResolvedValueOnce({ data: {} })

    await useAuthStore.getState().fetchMe()

    expect(useAuthStore.getState().user).toBeNull()
  })
})

describe('useAuthStore — initialize', () => {
  it('initialize 成功後 isInitialized 為 true', async () => {
    mockApiClient.get.mockResolvedValueOnce({ data: { data: FAKE_USER } })

    await useAuthStore.getState().initialize()

    expect(useAuthStore.getState().isInitialized).toBe(true)
    expect(useAuthStore.getState().user).toEqual(FAKE_USER)
  })

  it('initialize 失敗（未登入）時 isInitialized 仍設為 true，user 維持 null', async () => {
    mockApiClient.get.mockRejectedValueOnce(new Error('401'))

    await useAuthStore.getState().initialize()

    expect(useAuthStore.getState().isInitialized).toBe(true)
    expect(useAuthStore.getState().user).toBeNull()
  })

  it('initialize 重複呼叫只執行一次', async () => {
    useAuthStore.setState({ isInitialized: true })
    mockApiClient.get.mockResolvedValueOnce({ data: { data: FAKE_USER } })

    await useAuthStore.getState().initialize()

    expect(mockApiClient.get).not.toHaveBeenCalled()
  })
})
