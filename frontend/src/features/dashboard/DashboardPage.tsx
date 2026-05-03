import { useParams } from 'react-router-dom'
import { useDashboardStats } from './useDashboardStats'
import { KpiGrid } from './KpiGrid'
import { PendingTasksPanel } from './PendingTasksPanel'
import { ActivityFeed } from './ActivityFeed'
import { QuickActions } from './QuickActions'

export function DashboardPage() {
  const { id } = useParams<{ id: string }>()
  const { stats, loading } = useDashboardStats(id)

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold">儀表板</h1>

      <KpiGrid stats={stats} loading={loading} />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <PendingTasksPanel agentId={id} />
        <ActivityFeed agentId={id} />
      </div>

      <QuickActions />
    </div>
  )
}
