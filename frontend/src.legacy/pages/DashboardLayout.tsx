import { useEffect } from 'react'
import { NavLink, Outlet, useNavigate, useParams } from 'react-router-dom'
import { apiClient } from '@/api/client'
import { useAuthStore } from '@/store/useAuthStore'
import { cn } from '@/lib/utils'

const NAV_ITEMS = [
  { to: 'dashboard', label: '儀表板' },
  { to: 'categories', label: '分類管理' },
  { to: 'faqs', label: '知識庫 FAQ' },
  { to: 'import-export', label: '匯入 / 匯出' },
  { to: 'sync', label: '同步管理' },
  { to: 'chat', label: '對話測試' },
  { to: 'audit', label: '軌跡追蹤' },
]

export function DashboardLayout() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { user, currentAgent, setCurrentAgent, logout } = useAuthStore()

  useEffect(() => {
    if (!id) return
    if (currentAgent?.id === id) return
    apiClient
      .get(`/api/v1/agents/${id}`)
      .then((resp) => setCurrentAgent(resp.data?.data ?? null))
      .catch(() => navigate('/agents'))
  }, [id, currentAgent, setCurrentAgent, navigate])

  const handleLogout = async () => {
    await logout()
    navigate('/login')
  }

  return (
    <div className="min-h-screen flex">
      {/* Sidebar */}
      <aside className="w-56 bg-slate-900 text-slate-100 flex flex-col">
        <div className="p-4 border-b border-slate-800">
          <p className="text-xs text-slate-400">當前 Agent</p>
          <p className="font-semibold truncate">{currentAgent?.name || '...'}</p>
          <button
            onClick={() => navigate('/agents')}
            className="text-xs text-blue-300 mt-1 hover:underline"
          >
            切換 Agent
          </button>
        </div>

        <nav className="flex-1 p-2 space-y-1">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                cn(
                  'block px-3 py-2 rounded text-sm transition-colors',
                  isActive ? 'bg-blue-600 text-white' : 'text-slate-300 hover:bg-slate-800'
                )
              }
            >
              {item.label}
            </NavLink>
          ))}
          {user?.is_superadmin && (
            <>
              <div className="border-t border-slate-800 my-2 pt-2">
                <p className="text-xs text-slate-500 px-3 mb-1">Superadmin</p>
                <NavLink
                  to="settings"
                  className={({ isActive }) =>
                    cn(
                      'block px-3 py-2 rounded text-sm transition-colors',
                      isActive ? 'bg-blue-600 text-white' : 'text-slate-300 hover:bg-slate-800'
                    )
                  }
                >
                  Agent 設定
                </NavLink>
                <NavLink
                  to="/admin/users"
                  className={({ isActive }) =>
                    cn(
                      'block px-3 py-2 rounded text-sm transition-colors',
                      isActive ? 'bg-blue-600 text-white' : 'text-slate-300 hover:bg-slate-800'
                    )
                  }
                >
                  使用者管理
                </NavLink>
              </div>
            </>
          )}
        </nav>

        <div className="p-4 border-t border-slate-800">
          <p className="text-xs text-slate-400">登入者</p>
          <p className="text-sm truncate">{user?.username}</p>
          <button onClick={handleLogout} className="text-xs text-red-300 mt-2 hover:underline">
            登出
          </button>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  )
}
