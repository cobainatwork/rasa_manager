import { useEffect, type ReactNode } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { AUTH_EXPIRED_EVENT } from '@/api/client'
import { useAuthStore } from '@/store/useAuthStore'
import { useAgentContext } from '@/store/useAgentContext'
import { ROUTE_PATHS } from '@/routes/paths'

/**
 * B4：訂閱 'auth:expired' 事件，使用 React Router 的 useNavigate 導向 /login，
 * 並透過 query string 保留原 pathname，供登入後返回。
 */
export function AuthProvider({ children }: { children: ReactNode }) {
  const navigate = useNavigate()
  const location = useLocation()

  useEffect(() => {
    function onExpired() {
      // 清除本地身分與 agent context（避免殘留 stale state）
      useAuthStore.setState({ user: null })
      useAgentContext.setState({ current: null })
      if (location.pathname.startsWith(ROUTE_PATHS.login)) return
      const next = encodeURIComponent(location.pathname + location.search)
      navigate(`${ROUTE_PATHS.login}?next=${next}`, { replace: true })
    }
    window.addEventListener(AUTH_EXPIRED_EVENT, onExpired)
    return () => window.removeEventListener(AUTH_EXPIRED_EVENT, onExpired)
  }, [navigate, location.pathname, location.search])

  return <>{children}</>
}
