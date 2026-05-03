import { Card } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Activity } from 'lucide-react'
import { EmptyState } from '@/components/EmptyState'
import { useRecentActivity } from './useRecentActivity'
import { relativeTime } from '@/lib/format'

const ACTION_LABELS: Record<string, string> = {
  create: '建立了',
  update: '編輯了',
  delete: '刪除了',
  submit: '送審了',
  approve: '核准了',
  reject: '退回了',
  sync: '觸發了同步',
}

export function ActivityFeed({ agentId }: { agentId: string | undefined }) {
  const { items, loading } = useRecentActivity(agentId)

  if (loading) {
    return <Card className="p-5"><Skeleton className="h-40" /></Card>
  }

  return (
    <Card className="p-5">
      <h3 className="font-semibold mb-3">最近活動</h3>
      {items.length === 0 ? (
        <EmptyState icon={Activity} title="尚無活動紀錄" className="py-6" />
      ) : (
        <ul className="space-y-2.5">
          {items.map((log) => (
            <li key={log.id} className="text-sm flex items-start gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-brand-500 mt-2 shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="truncate">
                  <span className="font-medium">{log.performed_by_username ?? '系統'}</span>
                  <span className="text-text-secondary mx-1">{ACTION_LABELS[log.action] ?? log.action}</span>
                </p>
                <p className="text-xs text-text-muted">{relativeTime(log.created_at)}</p>
              </div>
            </li>
          ))}
        </ul>
      )}
    </Card>
  )
}
