import { useEffect } from 'react'
import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuthStore } from '@/store/useAuthStore'
import { ROUTE_PATHS } from '@/routes/paths'

// B3：移除 requireSuperadmin / children 死碼，固定 <Outlet /> 模式。
// Superadmin 限制改由 <AdminRoute /> 巢狀路由負責，避免雙路徑判斷。
export function ProtectedRoute() {
  const { user, isInitialized, initialize } = useAuthStore()
  const location = useLocation()

  useEffect(() => {
    if (!isInitialized) {
      initialize()
    }
  }, [isInitialized, initialize])

  if (!isInitialized) {
    return (
      <div className="flex h-screen items-center justify-center text-text-secondary">
        載入中...
      </div>
    )
  }

  if (!user) {
    return <Navigate to={ROUTE_PATHS.login} state={{ from: location }} replace />
  }

  return <Outlet />
}
