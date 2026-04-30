import { Card } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import type { AgentStats } from '@/api/types'

interface KpiGridProps {
  stats: AgentStats | null
  loading: boolean
}

const KPI_CONFIG = [
  { key: 'total_faqs', label: 'FAQ 總數', accent: 'bg-slate-600' },
  { key: 'pending_count', label: '待審核', accent: 'bg-amber-600' },
  { key: 'approved_count', label: '已核准', accent: 'bg-emerald-600' },
  { key: 'synced_count', label: '已同步', accent: 'bg-blue-600' },
] as const

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
          <div className={`w-2 h-8 ${kpi.accent} rounded-full mb-2`} />
          <p className="text-sm text-text-secondary">{kpi.label}</p>
          <p className="text-3xl font-bold mt-1">{stats?.[kpi.key] ?? 0}</p>
          <p className="text-xs text-text-muted mt-2">— vs 昨日</p>
        </Card>
      ))}
    </div>
  )
}
