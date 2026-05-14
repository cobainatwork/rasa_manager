import { FileText, Clock, CheckCircle2, RefreshCw } from 'lucide-react'
import { Card } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'
import type { AgentStats } from '@/api/types'

interface KpiGridProps {
  stats: AgentStats | null
  loading: boolean
}

const KPI_CONFIG = [
  { key: 'total_faqs' as const,     label: 'FAQ 總數', icon: FileText,     chipClass: 'bg-slate-500/10 text-slate-600' },
  { key: 'pending_count' as const,  label: '待審核',   icon: Clock,        chipClass: 'bg-amber-500/10 text-amber-600' },
  { key: 'approved_count' as const, label: '已核准',   icon: CheckCircle2, chipClass: 'bg-emerald-500/10 text-emerald-600' },
  { key: 'synced_count' as const,   label: '已同步',   icon: RefreshCw,    chipClass: 'bg-brand-500/10 text-brand-600' },
]

export function KpiGrid({ stats, loading }: KpiGridProps) {
  if (loading) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-28" />)}
      </div>
    )
  }
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      {KPI_CONFIG.map((kpi) => (
        <Card key={kpi.key} className="p-5">
          <div className={cn('w-8 h-8 rounded-lg flex items-center justify-center mb-3', kpi.chipClass)}>
            <kpi.icon className="w-4 h-4" strokeWidth={1.5} />
          </div>
          <p className="text-2xl font-bold tracking-tight">{stats?.[kpi.key] ?? 0}</p>
          <p className="text-sm text-text-secondary mt-0.5">{kpi.label}</p>
        </Card>
      ))}
    </div>
  )
}
