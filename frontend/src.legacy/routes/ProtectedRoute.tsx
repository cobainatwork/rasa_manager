import { ReactNode, useEffect } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { useAuthStore } from '@/store/useAuthStore'

interface Props {
  children: ReactNode
  requireSuperadmin?: boolean
}

export function ProtectedRoute({ children, requireSuperadmin = false }: Props) {
  const { user, isInitialized, initialize } = useAuthStore()
  const location = useLocation()

  useEffect(() => {
    if (!isInitialized) {
      initialize()
    }
  }, [isInitialized, initialize])

  if (!isInitialized) {
    return (
      <div className="flex h-screen items-center justify-center text-slate-500">
        載入中...
      </div>
    )
  }

  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  if (requireSuperadmin && !user.is_superadmin) {
    return (
      <div className="flex h-screen items-center justify-center text-red-600">
        權限不足，僅 Superadmin 可存取此頁面。
      </div>
    )
  }

  return <>{children}</>
}
