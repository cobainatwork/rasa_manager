import { useState } from 'react'
import { Undo2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { useFaqHistory } from './useFaqHistory'
import { relativeTime } from '@/lib/format'

const ACTION_LABELS: Record<string, string> = {
  create: '建立', update: '編輯', submit: '送審', approve: '核准', reject: '退回', sync: '同步',
}

interface Props {
  agentId: string | undefined
  faqId: string | null
}

export function VersionTimeline({ agentId, faqId }: Props) {
  const { history, loading, rollback } = useFaqHistory(agentId, faqId)
  const [showAll, setShowAll] = useState(false)

  if (loading) return <Skeleton className="h-32" />
  if (history.length === 0) return null

  const visible = showAll ? history : history.slice(0, 3)

  return (
    <div className="space-y-2 pt-3 border-t border-border-default">
      <div className="flex justify-between items-center">
        <h3 className="text-sm font-semibold">版本歷史（{history.length}）</h3>
        {history.length > 3 && (
          <Button variant="ghost" size="sm" onClick={() => setShowAll(!showAll)}>
            {showAll ? '收合' : '展開全部'}
          </Button>
        )}
      </div>
      <ul className="space-y-1.5 text-sm">
        {visible.map((v) => (
          <li key={v.id} className="flex items-center gap-2 p-2 rounded hover:bg-subtle">
            <span className="font-mono text-xs text-text-muted">v{v.version}</span>
            <span className="text-text-secondary">{ACTION_LABELS[v.action] ?? v.action}</span>
            <span className="text-xs text-text-muted ml-auto">{relativeTime(v.created_at)}</span>
            <Button variant="ghost" size="icon" onClick={() => rollback(v.id)} aria-label="還原">
              <Undo2 className="w-3.5 h-3.5" strokeWidth={1.5} />
            </Button>
          </li>
        ))}
      </ul>
    </div>
  )
}
