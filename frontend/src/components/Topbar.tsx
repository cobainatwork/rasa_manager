import { useNavigate } from 'react-router-dom'
import { Bell, ChevronDown, LogOut } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu, DropdownMenuContent,
  DropdownMenuItem, DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { useAuthStore } from '@/store/useAuthStore'
import { useAgentContext } from '@/store/useAgentContext'
import { ROUTE_PATHS } from '@/routes/paths'
import { AppLogo } from './AppLogo'
import { Breadcrumb } from './Breadcrumb'

export function Topbar() {
  const navigate   = useNavigate()
  const user       = useAuthStore((s) => s.user)
  const logout     = useAuthStore((s) => s.logout)
  const currentAgent    = useAgentContext((s) => s.current)
  const setCurrentAgent = useAgentContext((s) => s.setCurrent)

  async function handleLogout() {
    await logout()
    setCurrentAgent(null)
    navigate(ROUTE_PATHS.login)
  }

  return (
    <header className="h-11 bg-[#F2F2F7]/80 backdrop-blur-xl border-b border-black/[0.08] flex items-center px-4 sticky top-0 z-sticky shrink-0">
      {/* Logo */}
      <div className="mr-4">
        <AppLogo />
      </div>

      {/* Agent 切換 */}
      {currentAgent && (
        <>
          <span className="text-border-strong text-sm mx-1">／</span>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate(ROUTE_PATHS.agents)}
            className="h-7 px-2 text-[13px] font-normal text-text-secondary hover:text-text-primary"
          >
            {currentAgent.name}
            <ChevronDown className="w-3 h-3 ml-0.5 opacity-60" />
          </Button>
        </>
      )}

      {/* 麵包屑（靠右） */}
      <Breadcrumb className="ml-auto mr-2 text-[12px]" />

      {/* 通知（尚未實作） */}
      <Button
        variant="ghost"
        size="icon"
        aria-label="通知"
        title="尚未實作"
        disabled
        className="w-7 h-7 text-text-muted"
      >
        <Bell className="w-4 h-4" strokeWidth={1.5} />
      </Button>

      {/* 使用者選單 */}
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            variant="ghost"
            size="sm"
            className="h-7 px-2 ml-1 text-[13px] font-normal text-text-secondary hover:text-text-primary"
          >
            {user?.username}
            <ChevronDown className="w-3 h-3 ml-0.5 opacity-60" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="text-[13px]">
          <DropdownMenuItem onClick={handleLogout}>
            <LogOut className="w-3.5 h-3.5 mr-2" />
            登出
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </header>
  )
}
