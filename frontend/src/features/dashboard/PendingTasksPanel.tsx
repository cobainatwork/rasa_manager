import { useNavigate, useParams } from 'react-router-dom'
import { CheckCircle2 } from 'lucide-react'
import { Card } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Button } from '@/components/ui/button'
import { EmptyState } from '@/components/EmptyState'
import { usePendingFaqs } from './usePendingFaqs'
import { relativeTime } from '@/lib/format'

interface Props {
  agentId: string | undefined
}

export function PendingTasksPanel({ agentId }: Props) {
  const navigate = useNavigate()
  const { id } = useParams<{ id: string }>()
  const { items, loading } = usePendingFaqs(agentId)

  if (loading) {
    return <Card className="p-5"><Skeleton className="h-40" /></Card>
  }

  if (items.length === 0) {
    return (
      <Card className="p-5">
        <h3 className="font-semibold mb-2">待我處理</h3>
        <EmptyState icon={CheckCircle2} title="太好了，沒有待處理項目" className="py-6" />
      </Card>
    )
  }

  return (
    <Card className="p-5">
      <div className="flex justify-between items-center mb-3">
        <h3 className="font-semibold">待我處理（{items.length}）</h3>
        <Button variant="ghost" size="sm" onClick={() => navigate(`/agents/${id}/knowledge?status=pending`)}>
          查看全部
        </Button>
      </div>
      <ul className="space-y-2">
        {items.map((faq) => (
          <li
            key={faq.id}
            onClick={() => {
              try { if (id) localStorage.setItem(`kb_selected_faq_${id}`, faq.id) } catch { /* ignore */ }
              navigate(`/agents/${id}/knowledge`)
            }}
            className="p-2 rounded hover:bg-subtle transition-colors cursor-pointer text-sm flex justify-between items-center"
          >
            <span className="truncate flex-1">{faq.question}</span>
            <span className="text-xs text-text-muted ml-2">{relativeTime(faq.updated_at)}</span>
          </li>
        ))}
      </ul>
    </Card>
  )
}
