import { describe, it, expect, beforeEach, vi } from 'vitest'
import { useAuthStore } from './useAuthStore'
import { apiClient } from '@/api/client'
import type { Agent, User } from '@/api/types'

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

const FAKE_AGENT: Agent = {
  id: 'ag-1',
  name: '測試 Agent',
  txt_output_path: '/opt/test',
  rasa_rest_url: null,
  ingest_script_path: null,
  created_at: null,
}

beforeEach(() => {
  useAuthStore.setState({
    user: null,
    currentAgent: null,
    isLoading: false,
    isInitialized: false,
  })
  vi.clearAllMocks()
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

  it('login 回傳無 data 時不呼叫 fetchMe', async () => {
    mockApiClient.post.mockResolvedValueOnce({ data: {} })

    await useAuthStore.getState().login('admin', 'Admin1234')

    expect(mockApiClient.get).not.toHaveBeenCalled()
    expect(useAuthStore.getState().user).toBeNull()
  })

  it('login API 失敗後 isLoading 仍歸零', async () => {
    mockApiClient.post.mockRejectedValueOnce(new Error('Network Error'))

    await expect(useAuthStore.getState().login('admin', 'wrong')).rejects.toThrow()
    expect(useAuthStore.getState().isLoading).toBe(false)
  })

  it('login 期間 isLoading 為 true', async () => {
    let loadingDuringCall = false
    mockApiClient.post.mockImplementationOnce(async () => {
      loadingDuringCall = useAuthStore.getState().isLoading
      return { data: {} }
    })

    await useAuthStore.getState().login('admin', 'Admin1234')

    expect(loadingDuringCall).toBe(true)
  })
})

describe('useAuthStore — logout', () => {
  it('logout 後清除 user 與 currentAgent', async () => {
    useAuthStore.setState({ user: FAKE_USER, currentAgent: FAKE_AGENT })
    mockApiClient.post.mockResolvedValueOnce({})

    await useAuthStore.getState().logout()

    expect(useAuthStore.getState().user).toBeNull()
    expect(useAuthStore.getState().currentAgent).toBeNull()
  })

  it('logout 即使後端失敗也清除本地狀態', async () => {
    useAuthStore.setState({ user: FAKE_USER })
    mockApiClient.post.mockRejectedValueOnce(new Error('500'))

    await useAuthStore.getState().logout()

    expect(useAuthStore.getState().user).toBeNull()
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

describe('useAuthStore — setCurrentAgent', () => {
  it('setCurrentAgent 更新 currentAgent', () => {
    useAuthStore.getState().setCurrentAgent(FAKE_AGENT)
    expect(useAuthStore.getState().currentAgent).toEqual(FAKE_AGENT)
  })

  it('setCurrentAgent null 清除 currentAgent', () => {
    useAuthStore.setState({ currentAgent: FAKE_AGENT })
    useAuthStore.getState().setCurrentAgent(null)
    expect(useAuthStore.getState().currentAgent).toBeNull()
  })
})
