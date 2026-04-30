import { Navigate, Outlet } from 'react-router-dom'
import { useAuthStore } from '@/store/useAuthStore'

export function AdminRoute() {
  const user = useAuthStore((s) => s.user)
  if (!user?.is_superadmin) return <Navigate to="/agents" replace />
  return <Outlet />
}
