import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { LoginPage } from './LoginPage'
import { useAuthStore } from '@/store/useAuthStore'

const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return { ...actual, useNavigate: () => mockNavigate, useLocation: () => ({ state: null, pathname: '/login' }) }
})

describe('LoginPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useAuthStore.setState({ user: null, isLoading: false })
  })

  function renderPage() {
    return render(<MemoryRouter><LoginPage /></MemoryRouter>)
  }

  it('顯示帳號與密碼欄位', () => {
    renderPage()
    expect(screen.getByLabelText('帳號')).toBeInTheDocument()
    expect(screen.getByLabelText('密碼')).toBeInTheDocument()
  })

  it('空欄位送出顯示驗證錯誤', async () => {
    const user = userEvent.setup()
    renderPage()
    await user.click(screen.getByRole('button', { name: /登入/ }))
    expect(await screen.findByText('請輸入帳號')).toBeInTheDocument()
    expect(await screen.findByText('請輸入密碼')).toBeInTheDocument()
  })

  it('密碼 show/hide toggle', async () => {
    const user = userEvent.setup()
    renderPage()
    const pwInput = screen.getByLabelText('密碼') as HTMLInputElement
    expect(pwInput.type).toBe('password')
    await user.click(screen.getByLabelText('顯示密碼'))
    expect(pwInput.type).toBe('text')
  })

  it('成功登入後 navigate 到 /agents', async () => {
    const user = userEvent.setup()
    const loginSpy = vi.fn().mockResolvedValue(undefined)
    useAuthStore.setState({ login: loginSpy })

    renderPage()
    await user.type(screen.getByLabelText('帳號'), 'admin')
    await user.type(screen.getByLabelText('密碼'), 'Admin1234')
    await user.click(screen.getByRole('button', { name: /登入/ }))

    expect(loginSpy).toHaveBeenCalledWith('admin', 'Admin1234')
  })
})
