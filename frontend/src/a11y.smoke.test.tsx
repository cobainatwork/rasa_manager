/**
 * A11y Smoke Test — WCAG 2.1 AA 自動化檢查
 *
 * 範圍：主要頁面渲染後跑 axe-core，僅啟用 wcag2a / wcag2aa / wcag21a / wcag21aa rule sets
 * 不啟用 best-practice，避免 false positive 過多
 *
 * 注意：
 * - jsdom 不支援 layout，故 color-contrast / focus-visible 等規則於此環境會被 axe 自動 skip
 * - 真實 contrast 需以 Lighthouse / 真瀏覽器測試
 */
import { describe, it, expect } from 'vitest'
import { render, waitFor } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { axe } from 'jest-axe'
import { LoginPage } from '@/features/auth/LoginPage'
import { AgentSelectPage } from '@/features/agents/AgentSelectPage'
import { DashboardPage } from '@/features/dashboard/DashboardPage'
import { KnowledgePage } from '@/features/knowledge/KnowledgePage'
import { UserManagementPage } from '@/features/users/UserManagementPage'
import { useAuthStore } from '@/store/useAuthStore'

const axeOptions = {
  runOnly: {
    type: 'tag' as const,
    values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'],
  },
}

function setSuperadmin() {
  useAuthStore.setState({
    user: { id: 'u1', username: 'admin', is_superadmin: true, is_active: true, created_at: '' },
  })
}

describe('A11y Smoke (WCAG 2.1 AA)', () => {
  it('LoginPage 無 a11y 違規', async () => {
    const { container } = render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    )
    const results = await axe(container, axeOptions)
    expect(results).toHaveNoViolations()
  })

  it('AgentSelectPage 無 a11y 違規', async () => {
    setSuperadmin()
    const { container, findByText } = render(
      <MemoryRouter>
        <AgentSelectPage />
      </MemoryRouter>
    )
    await findByText('選擇 Agent 專案')
    const results = await axe(container, axeOptions)
    expect(results).toHaveNoViolations()
  })

  it('DashboardPage 無 a11y 違規', async () => {
    setSuperadmin()
    const { container, findByText } = render(
      <MemoryRouter initialEntries={['/agents/a1/dashboard']}>
        <Routes>
          <Route path="/agents/:id/dashboard" element={<DashboardPage />} />
        </Routes>
      </MemoryRouter>
    )
    await findByText('儀表板')
    await waitFor(() => findByText('FAQ 總數'))
    const results = await axe(container, axeOptions)
    expect(results).toHaveNoViolations()
  })

  it('KnowledgePage 無 a11y 違規', async () => {
    setSuperadmin()
    const { container } = render(
      <MemoryRouter initialEntries={['/agents/a1/knowledge']}>
        <Routes>
          <Route path="/agents/:id/knowledge" element={<KnowledgePage />} />
        </Routes>
      </MemoryRouter>
    )
    // 等三欄基本 mount
    await waitFor(() => container.querySelector('aside'))
    const results = await axe(container, axeOptions)
    expect(results).toHaveNoViolations()
  })

  it('UserManagementPage 無 a11y 違規', async () => {
    setSuperadmin()
    const { container } = render(
      <MemoryRouter>
        <UserManagementPage />
      </MemoryRouter>
    )
    await waitFor(() => container.querySelector('main, [role="main"], section, aside'))
    const results = await axe(container, axeOptions)
    expect(results).toHaveNoViolations()
  })
})
