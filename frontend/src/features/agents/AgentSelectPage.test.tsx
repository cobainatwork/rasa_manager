import { describe, it, expect } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { AgentSelectPage } from './AgentSelectPage'
import { useAuthStore } from '@/store/useAuthStore'

function renderPage(isSuper = true) {
  useAuthStore.setState({
    user: { id: 'u1', username: 'admin', is_superadmin: isSuper, is_active: true, created_at: '' },
  })
  return render(<MemoryRouter><AgentSelectPage /></MemoryRouter>)
}

describe('AgentSelectPage', () => {
  it('顯示頁標題', async () => {
    renderPage()
    expect(screen.getByText('選擇 Agent 專案')).toBeInTheDocument()
  })

  it('superadmin 顯示「建立 Agent」按鈕', async () => {
    renderPage(true)
    await waitFor(() => expect(screen.getAllByRole('button', { name: /建立 Agent/ }).length).toBeGreaterThan(0))
  })

  it('非 superadmin 不顯示「建立 Agent」按鈕', async () => {
    renderPage(false)
    await waitFor(() => {
      const buttons = screen.queryAllByRole('button', { name: /建立 Agent/ })
      expect(buttons).toHaveLength(0)
    })
  })

  it('載入後顯示 Agent 卡片', async () => {
    renderPage()
    await waitFor(() => expect(screen.getByText('Demo')).toBeInTheDocument())
  })
})
