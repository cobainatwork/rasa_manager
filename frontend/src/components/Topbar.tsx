import { useNavigate } from 'react-router-dom'
import { Bell, ChevronDown, LogOut } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu'
import { useAuthStore } from '@/store/useAuthStore'
import { useAgentContext } from '@/store/useAgentContext'
import { ROUTE_PATHS } from '@/routes/paths'
import { Breadcrumb } from './Breadcrumb'

export function Topbar() {
  const navigate = useNavigate()
  const user = useAuthStore((s) => s.user)
  const logout = useAuthStore((s) => s.logout)
  const currentAgent = useAgentContext((s) => s.current)
  const setCurrentAgent = useAgentContext((s) => s.setCurrent)

  async function handleLogout() {
    await logout()
    setCurrentAgent(null)
    navigate(ROUTE_PATHS.login)
  }

  return (
    <header className="h-16 bg-surface border-b border-border-default flex items-center px-6 sticky top-0 z-sticky">
      <div className="flex items-center gap-3 mr-6">
        <div className="w-8 h-8 rounded bg-brand-500 flex items-center justify-center font-bold text-white">R</div>
        <span className="font-semibold text-text-primary">Rasa KB</span>
      </div>

      {currentAgent && (
        <>
          <span className="text-text-muted mx-2">/</span>
          <Button variant="ghost" size="sm" onClick={() => navigate(ROUTE_PATHS.agents)}>
            {currentAgent.name} <ChevronDown className="w-4 h-4 ml-1" />
          </Button>
        </>
      )}

      <Breadcrumb className="ml-auto mr-4" />

      {/* I13：通知中心尚未實作（spec §13 未含通知端點），保留 placeholder 並 disabled 避免誤點 */}
      <Button variant="ghost" size="icon" aria-label="通知" title="尚未實作" disabled>
        <Bell className="w-5 h-5" strokeWidth={1.5} />
      </Button>

      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" size="sm">
            {user?.username} <ChevronDown className="w-4 h-4 ml-1" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuItem onClick={handleLogout}>
            <LogOut className="w-4 h-4 mr-2" /> 登出
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </header>
  )
}
