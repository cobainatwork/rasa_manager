import { useLocation, useParams, Link } from 'react-router-dom'
import { ChevronRight } from 'lucide-react'
import { cn } from '@/lib/utils'

const PAGE_LABELS: Record<string, string> = {
  dashboard: '儀表板',
  knowledge: '知識庫',
  sync: '同步',
  'import-export': '匯入匯出',
  'test-chat': '對話測試',
  audit: '稽核日誌',
  settings: 'Agent 設定',
}

export function Breadcrumb({ className }: { className?: string }) {
  const { pathname } = useLocation()
  const { id } = useParams<{ id: string }>()
  if (!id) return null

  const segments = pathname.split('/').filter(Boolean)
  const lastSeg = segments[segments.length - 1] ?? ''
  // N5：未匹配時 fallback 至首字大寫的 segment 原文，避免整個 breadcrumb 消失
  const label = PAGE_LABELS[lastSeg] ?? (lastSeg ? lastSeg.charAt(0).toUpperCase() + lastSeg.slice(1) : '')
  if (!label) return null

  return (
    <nav className={cn('text-sm text-text-secondary flex items-center gap-1', className)} aria-label="Breadcrumb">
      <Link to={`/agents/${id}/dashboard`} className="hover:text-text-primary">主頁</Link>
      <ChevronRight className="w-4 h-4" strokeWidth={1.5} />
      <span className="text-text-primary font-medium">{label}</span>
    </nav>
  )
}
