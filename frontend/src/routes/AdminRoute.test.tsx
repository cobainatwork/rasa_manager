import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { useAuthStore } from '@/store/useAuthStore'
import { AdminRoute } from './AdminRoute'

function renderWithAuth(isSuper: boolean) {
  useAuthStore.setState({
    user: { id: '1', username: 'u', is_superadmin: isSuper, is_active: true, created_at: '' },
  })
  return render(
    <MemoryRouter initialEntries={['/admin']}>
      <Routes>
        <Route element={<AdminRoute />}>
          <Route path="/admin" element={<div>admin-only</div>} />
        </Route>
        <Route path="/" element={<div>home</div>} />
        <Route path="/agents" element={<div>agents-list</div>} />
      </Routes>
    </MemoryRouter>
  )
}

describe('AdminRoute', () => {
  it('superadmin 可進入', () => {
    renderWithAuth(true)
    expect(screen.getByText('admin-only')).toBeInTheDocument()
  })
  it('非 superadmin 重新導向到 /agents', () => {
    renderWithAuth(false)
    expect(screen.getByText('agents-list')).toBeInTheDocument()
  })
})
