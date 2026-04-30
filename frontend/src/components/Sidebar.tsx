import { NavLink, useParams } from 'react-router-dom'
import { Home, BookOpen, RefreshCw, ArrowDownUp, MessageSquare, History, Settings, type LucideIcon } from 'lucide-react'
import { useAuthStore } from '@/store/useAuthStore'
import { Tooltip, TooltipContent, TooltipTrigger, TooltipProvider } from '@/components/ui/tooltip'
import { cn } from '@/lib/utils'

interface NavItem { to: string; icon: LucideIcon; label: string; superadminOnly?: boolean }

const NAV_ITEMS: NavItem[] = [
  { to: 'dashboard', icon: Home, label: '儀表板' },
  { to: 'knowledge', icon: BookOpen, label: '知識庫' },
  { to: 'sync', icon: RefreshCw, label: '同步' },
  { to: 'import-export', icon: ArrowDownUp, label: '匯入匯出' },
  { to: 'test-chat', icon: MessageSquare, label: '對話測試' },
  { to: 'audit', icon: History, label: '稽核日誌' },
  { to: 'settings', icon: Settings, label: 'Agent 設定', superadminOnly: true },
]

export function Sidebar() {
  const { id } = useParams<{ id: string }>()
  const isSuper = useAuthStore((s) => s.user?.is_superadmin ?? false)
  if (!id) return null
  return (
    <TooltipProvider delayDuration={300}>
      <aside className="w-16 h-screen bg-surface border-r border-border-default flex flex-col items-center py-4 gap-2 sticky top-0">
        {NAV_ITEMS.filter((it) => !it.superadminOnly || isSuper).map((item) => (
          <Tooltip key={item.to}>
            <TooltipTrigger asChild>
              <NavLink
                to={`/agents/${id}/${item.to}`}
                className={({ isActive }) => cn(
                  'w-10 h-10 rounded-md flex items-center justify-center cursor-pointer transition-colors duration-fast',
                  isActive ? 'bg-brand-50 text-brand-700' : 'text-text-secondary hover:bg-subtle hover:text-text-primary'
                )}
                aria-label={item.label}
              >
                <item.icon className="w-5 h-5" strokeWidth={1.5} />
              </NavLink>
            </TooltipTrigger>
            <TooltipContent side="right">{item.label}</TooltipContent>
          </Tooltip>
        ))}
      </aside>
    </TooltipProvider>
  )
}
