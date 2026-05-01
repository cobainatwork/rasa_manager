import { Navigate, Outlet } from 'react-router-dom'
import { useAuthStore } from '@/store/useAuthStore'
import { ROUTE_PATHS } from '@/routes/paths'

export function AdminRoute() {
  const user = useAuthStore((s) => s.user)
  if (!user?.is_superadmin) return <Navigate to={ROUTE_PATHS.agents} replace />
  return <Outlet />
}
