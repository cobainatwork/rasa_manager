import { useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { History } from 'lucide-react'
import { Card } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { EmptyState } from '@/components/EmptyState'
import { SyncTriggerCard } from './SyncTriggerCard'
import { SyncHistoryItem } from './SyncHistoryItem'
import { useSyncTrigger } from './useSyncTrigger'
import { useSyncHistory } from './useSyncHistory'

export function SyncPage() {
  const { id } = useParams<{ id: string }>()
  const { activeLog, triggering, trigger } = useSyncTrigger(id)
  const { items, loading, reload } = useSyncHistory(id)

  // 任務完成後重抓歷史
  useEffect(() => {
    if (activeLog && (activeLog.status === 'completed' || activeLog.status === 'failed')) {
      reload()
    }
  }, [activeLog, reload])

  return (
    <div className="p-8 max-w-4xl space-y-6">
      <h1 className="text-2xl font-bold">同步任務</h1>

      <SyncTriggerCard triggering={triggering} activeLog={activeLog} onTrigger={trigger} />

      <Card className="p-6">
        <h2 className="text-lg font-semibold mb-3">歷史紀錄（最近 20 筆）</h2>
        {loading && <div className="space-y-2">{[1, 2, 3].map((i) => <Skeleton key={i} className="h-12" />)}</div>}
        {!loading && items.length === 0 && (
          <EmptyState icon={History} title="尚無同步紀錄" description="觸發第一次同步以建立歷史" />
        )}
        {!loading && items.length > 0 && (
          <ul className="space-y-2">
            {items.map((it) => <SyncHistoryItem key={it.id} item={it} />)}
          </ul>
        )}
      </Card>
    </div>
  )
}
