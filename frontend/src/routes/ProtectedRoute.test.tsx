import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { ProtectedRoute } from '@/routes/ProtectedRoute'
import { useAuthStore } from '@/store/useAuthStore'

const FAKE_USER = {
  id: 'uid-001',
  username: 'editor',
  is_superadmin: false,
  is_active: true,
  created_at: '2024-01-01T00:00:00',
}

/**
 * 將 ProtectedRoute 包在 MemoryRouter 內渲染。
 * 使用 <Outlet /> 模式：/protected 是 ProtectedRoute 的子路由。
 */
function renderRoute(initialPath: string = '/protected') {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route path="/login" element={<div>登入頁面</div>} />
        <Route element={<ProtectedRoute />}>
          <Route path="/protected" element={<div>受保護頁面</div>} />
        </Route>
      </Routes>
    </MemoryRouter>,
  )
}

const mockInitialize = vi.fn()

beforeEach(() => {
  vi.clearAllMocks()
  useAuthStore.setState({
    user: null,
    isLoading: false,
    isInitialized: false,
    initialize: mockInitialize,
    login: vi.fn(),
    logout: vi.fn(),
    fetchMe: vi.fn(),
  })
})

describe('ProtectedRoute — 未初始化（isInitialized = false）', () => {
  it('顯示「載入中...」', () => {
    renderRoute()
    expect(screen.getByText('載入中...')).toBeDefined()
  })

  it('呼叫 initialize() 觸發身分驗證初始化', () => {
    renderRoute()
    expect(mockInitialize).toHaveBeenCalledTimes(1)
  })

  it('不渲染子元件', () => {
    renderRoute()
    expect(screen.queryByText('受保護頁面')).toBeNull()
  })

  it('不導向登入頁', () => {
    renderRoute()
    expect(screen.queryByText('登入頁面')).toBeNull()
  })
})

describe('ProtectedRoute — 已初始化、未登入（user = null）', () => {
  beforeEach(() => {
    useAuthStore.setState({ user: null, isInitialized: true })
  })

  it('導向 /login（顯示登入頁面標記）', () => {
    renderRoute()
    expect(screen.getByText('登入頁面')).toBeDefined()
  })

  it('不渲染子元件', () => {
    renderRoute()
    expect(screen.queryByText('受保護頁面')).toBeNull()
  })

  it('不顯示「載入中」', () => {
    renderRoute()
    expect(screen.queryByText('載入中...')).toBeNull()
  })

  it('不呼叫 initialize()（已初始化無需重複呼叫）', () => {
    renderRoute()
    expect(mockInitialize).not.toHaveBeenCalled()
  })
})

describe('ProtectedRoute — 已登入', () => {
  beforeEach(() => {
    useAuthStore.setState({ user: FAKE_USER, isInitialized: true })
  })

  it('透過 <Outlet /> 渲染巢狀子路由', () => {
    renderRoute()
    expect(screen.getByText('受保護頁面')).toBeDefined()
  })

  it('不顯示「載入中」', () => {
    renderRoute()
    expect(screen.queryByText('載入中...')).toBeNull()
  })

  it('不導向登入頁', () => {
    renderRoute()
    expect(screen.queryByText('登入頁面')).toBeNull()
  })
})
