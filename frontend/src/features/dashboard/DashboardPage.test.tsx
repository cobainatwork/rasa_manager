import { describe, it, expect } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { DashboardPage } from './DashboardPage'
import { useAuthStore } from '@/store/useAuthStore'

function renderPage() {
  useAuthStore.setState({
    user: { id: 'u1', username: 'admin', is_superadmin: true, is_active: true, created_at: '' },
  })
  return render(
    <MemoryRouter initialEntries={['/agents/a1/dashboard']}>
      <Routes>
        <Route path="/agents/:id/dashboard" element={<DashboardPage />} />
      </Routes>
    </MemoryRouter>
  )
}

describe('DashboardPage', () => {
  it('顯示頁標題', () => {
    renderPage()
    expect(screen.getByText('儀表板')).toBeInTheDocument()
  })

  it('顯示 KPI 卡片（4 個）', async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('FAQ 總數')).toBeInTheDocument()
      expect(screen.getByText('待審核')).toBeInTheDocument()
      expect(screen.getByText('已核准')).toBeInTheDocument()
      expect(screen.getByText('已同步')).toBeInTheDocument()
    })
  })

  it('顯示快速操作按鈕', () => {
    renderPage()
    expect(screen.getByRole('button', { name: /新增 FAQ/ })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /觸發同步/ })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /對話測試/ })).toBeInTheDocument()
  })
})
