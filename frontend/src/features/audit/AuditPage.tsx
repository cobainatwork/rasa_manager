import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { History } from 'lucide-react'
import { Skeleton } from '@/components/ui/skeleton'
import { Button } from '@/components/ui/button'
import { EmptyState } from '@/components/EmptyState'
import { AuditDayGroup } from './AuditDayGroup'
import { useAuditLog } from './useAuditLog'
import type { AuditLogEntry } from '@/api/types'

function groupByDay(entries: AuditLogEntry[]): Map<string, AuditLogEntry[]> {
  const map = new Map<string, AuditLogEntry[]>()
  for (const e of entries) {
    const day = e.created_at ? new Date(e.created_at).toLocaleDateString('zh-TW') : '未知'
    const arr = map.get(day) ?? []
    arr.push(e)
    map.set(day, arr)
  }
  return map
}

export function AuditPage() {
  const { id } = useParams<{ id: string }>()
  const [page, setPage] = useState(1)
  const { data, loading, perPage } = useAuditLog(id, page)

  const totalPages = data ? Math.max(1, Math.ceil(data.total / perPage)) : 1
  const grouped = data ? groupByDay(data.items) : new Map()

  return (
    <div className="p-8 max-w-4xl">
      <h1 className="text-2xl font-bold mb-6">稽核日誌</h1>

      {loading && <div className="space-y-2">{[1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-10" />)}</div>}

      {!loading && data && data.items.length === 0 && (
        <EmptyState icon={History} title="尚無稽核日誌" description="使用者操作後會自動記錄於此" />
      )}

      {!loading && data && data.items.length > 0 && (
        <>
          {[...grouped.entries()].map(([day, entries]) => (
            <AuditDayGroup key={day} date={day} entries={entries} />
          ))}
          <div className="flex justify-between items-center mt-6 text-sm">
            <span className="text-text-secondary">第 {page}/{totalPages} 頁，共 {data.total} 筆</span>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>上一頁</Button>
              <Button variant="outline" size="sm" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>下一頁</Button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
