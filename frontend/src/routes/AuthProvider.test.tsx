import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, act } from '@testing-library/react'
import { MemoryRouter, Routes, Route, useLocation } from 'react-router-dom'
import { AuthProvider } from './AuthProvider'
import { AUTH_EXPIRED_EVENT } from '@/api/client'
import { useAuthStore } from '@/store/useAuthStore'
import { useAgentContext } from '@/store/useAgentContext'

function LocationProbe() {
  const loc = useLocation()
  return <div data-testid="loc">{loc.pathname + loc.search}</div>
}

beforeEach(() => {
  useAuthStore.setState({
    user: { id: 'u1', username: 'u', is_superadmin: false, is_active: true, created_at: '' },
    isInitialized: true,
  })
  useAgentContext.setState({ current: null })
  vi.clearAllMocks()
})

describe('AuthProvider — auth:expired 事件處理（B4）', () => {
  it('收到事件時清除 user / agent 並導向 /login，並以 next query 保留路徑', async () => {
    render(
      <MemoryRouter initialEntries={['/agents/a1/knowledge?tab=list']}>
        <AuthProvider>
          <Routes>
            <Route path="/login" element={<LocationProbe />} />
            <Route path="*" element={<LocationProbe />} />
          </Routes>
        </AuthProvider>
      </MemoryRouter>,
    )

    // 初始位置
    expect(screen.getByTestId('loc').textContent).toBe('/agents/a1/knowledge?tab=list')

    await act(async () => {
      window.dispatchEvent(new CustomEvent(AUTH_EXPIRED_EVENT))
    })

    expect(useAuthStore.getState().user).toBeNull()
    expect(useAgentContext.getState().current).toBeNull()
    const loc = screen.getByTestId('loc').textContent ?? ''
    expect(loc.startsWith('/login?next=')).toBe(true)
    expect(loc).toContain(encodeURIComponent('/agents/a1/knowledge?tab=list'))
  })

  it('已在 /login 時不再次導頁', async () => {
    render(
      <MemoryRouter initialEntries={['/login']}>
        <AuthProvider>
          <Routes>
            <Route path="/login" element={<LocationProbe />} />
          </Routes>
        </AuthProvider>
      </MemoryRouter>,
    )

    await act(async () => {
      window.dispatchEvent(new CustomEvent(AUTH_EXPIRED_EVENT))
    })

    // 仍應停在 /login（不附加 next）
    expect(screen.getByTestId('loc').textContent).toBe('/login')
  })
})
