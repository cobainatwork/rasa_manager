import { NavLink, useParams } from 'react-router-dom'
import {
  Home, BookOpen, RefreshCw, ArrowDownUp,
  MessageSquare, History, Settings, type LucideIcon,
} from 'lucide-react'
import { useAuthStore } from '@/store/useAuthStore'
import { cn } from '@/lib/utils'
import { AGENT_SUBPATHS } from '@/routes/paths'

interface NavItem {
  to: string
  icon: LucideIcon
  label: string
  superadminOnly?: boolean
}

const NAV_ITEMS: NavItem[] = [
  { to: AGENT_SUBPATHS.dashboard,    icon: Home,         label: '儀表板' },
  { to: AGENT_SUBPATHS.knowledge,    icon: BookOpen,     label: '知識庫' },
  { to: AGENT_SUBPATHS.sync,         icon: RefreshCw,    label: '同步' },
  { to: AGENT_SUBPATHS.importExport, icon: ArrowDownUp,  label: '匯入匯出' },
  { to: AGENT_SUBPATHS.testChat,     icon: MessageSquare, label: '對話測試' },
  { to: AGENT_SUBPATHS.audit,        icon: History,      label: '稽核日誌' },
  { to: AGENT_SUBPATHS.settings,     icon: Settings,     label: 'Agent 設定', superadminOnly: true },
]

export function Sidebar() {
  const { id } = useParams<{ id: string }>()
  const isSuper = useAuthStore((s) => s.user?.is_superadmin ?? false)
  if (!id) return null

  return (
    <aside className="w-52 h-screen shrink-0 bg-gradient-to-b from-canvas to-subtle border-r border-black/[0.06] flex flex-col py-2 px-2 gap-0.5 sticky top-0 overflow-y-auto">
      {NAV_ITEMS.filter((it) => !it.superadminOnly || isSuper).map((item) => (
        <NavLink
          key={item.to}
          to={`/agents/${id}/${item.to}`}
          className={({ isActive }) => cn(
            'flex items-center gap-2.5 px-3 py-1.5 rounded-md text-[13px] transition-colors duration-fast cursor-pointer select-none',
            isActive
              ? 'bg-canvas text-text-primary font-medium shadow-[inset_3px_0_0_theme(colors.brand.500)]'
              : 'text-text-secondary hover:bg-black/5 hover:text-text-primary',
          )}
        >
          <item.icon className="w-4 h-4 shrink-0" strokeWidth={1.5} />
          <span>{item.label}</span>
        </NavLink>
      ))}
    </aside>
  )
}
