import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { ProtectedRoute } from '@/routes/ProtectedRoute'
import { useAuthStore } from '@/store/useAuthStore'
import type { ReactNode } from 'react'

// ─── 測試用假資料 ──────────────────────────────────────────────────────────────

const FAKE_USER = {
  id: 'uid-001',
  username: 'editor',
  is_superadmin: false,
  is_active: true,
  created_at: '2024-01-01T00:00:00',
}

const FAKE_SUPERADMIN = {
  id: 'uid-002',
  username: 'admin',
  is_superadmin: true,
  is_active: true,
  created_at: '2024-01-01T00:00:00',
}

// ─── 渲染輔助 ──────────────────────────────────────────────────────────────────

/**
 * 將 ProtectedRoute 包在 MemoryRouter 內渲染。
 * - /login  → <div>登入頁面</div>（驗證 Navigate redirect）
 * - /protected → ProtectedRoute 包裹的目標內容
 */
function renderRoute({
  requireSuperadmin = false,
  children = <div>受保護頁面</div> as ReactNode,
  initialPath = '/protected',
}: {
  requireSuperadmin?: boolean
  children?: ReactNode
  initialPath?: string
} = {}) {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route path="/login" element={<div>登入頁面</div>} />
        <Route
          path="/protected"
          element={
            <ProtectedRoute requireSuperadmin={requireSuperadmin}>
              {children}
            </ProtectedRoute>
          }
        />
      </Routes>
    </MemoryRouter>,
  )
}

// ─── 共用 Mock ─────────────────────────────────────────────────────────────────

const mockInitialize = vi.fn()

beforeEach(() => {
  vi.clearAllMocks()
  // 重置 store 至初始狀態，確保每筆測試隔離
  useAuthStore.setState({
    user: null,
    currentAgent: null,
    isLoading: false,
    isInitialized: false,
    initialize: mockInitialize,
    login: vi.fn(),
    logout: vi.fn(),
    fetchMe: vi.fn(),
    setCurrentAgent: vi.fn(),
  })
})

// ─── 測試案例 ──────────────────────────────────────────────────────────────────

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

describe('ProtectedRoute — 已登入、requireSuperadmin = false（預設）', () => {
  beforeEach(() => {
    useAuthStore.setState({ user: FAKE_USER, isInitialized: true })
  })

  it('渲染子元件', () => {
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

  it('不顯示「權限不足」', () => {
    renderRoute()
    expect(screen.queryByText(/權限不足/)).toBeNull()
  })

  it('不呼叫 initialize()', () => {
    renderRoute()
    expect(mockInitialize).not.toHaveBeenCalled()
  })
})

describe('ProtectedRoute — requireSuperadmin = true，非 Superadmin', () => {
  beforeEach(() => {
    useAuthStore.setState({ user: FAKE_USER, isInitialized: true })
  })

  it('顯示「權限不足」訊息', () => {
    renderRoute({ requireSuperadmin: true })
    expect(screen.getByText(/權限不足/)).toBeDefined()
  })

  it('不渲染子元件', () => {
    renderRoute({ requireSuperadmin: true })
    expect(screen.queryByText('受保護頁面')).toBeNull()
  })

  it('不導向登入頁（已登入）', () => {
    renderRoute({ requireSuperadmin: true })
    expect(screen.queryByText('登入頁面')).toBeNull()
  })
})

describe('ProtectedRoute — requireSuperadmin = true，Superadmin', () => {
  beforeEach(() => {
    useAuthStore.setState({ user: FAKE_SUPERADMIN, isInitialized: true })
  })

  it('渲染子元件', () => {
    renderRoute({ requireSuperadmin: true })
    expect(screen.getByText('受保護頁面')).toBeDefined()
  })

  it('不顯示「權限不足」', () => {
    renderRoute({ requireSuperadmin: true })
    expect(screen.queryByText(/權限不足/)).toBeNull()
  })
})

describe('ProtectedRoute — 邊界情境', () => {
  it('requireSuperadmin 預設值為 false，一般使用者可瀏覽', () => {
    useAuthStore.setState({ user: FAKE_USER, isInitialized: true })
    renderRoute() // 不傳 requireSuperadmin
    expect(screen.getByText('受保護頁面')).toBeDefined()
  })

  it('自訂 children 正確渲染', () => {
    useAuthStore.setState({ user: FAKE_USER, isInitialized: true })
    renderRoute({ children: <span>自訂子元件內容</span> })
    expect(screen.getByText('自訂子元件內容')).toBeDefined()
  })

  it('Superadmin 存取非限制路由也可正常渲染', () => {
    useAuthStore.setState({ user: FAKE_SUPERADMIN, isInitialized: true })
    renderRoute({ requireSuperadmin: false })
    expect(screen.getByText('受保護頁面')).toBeDefined()
  })
})
