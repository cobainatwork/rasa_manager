import { useState } from 'react'
import { Skeleton } from '@/components/ui/skeleton'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { EmptyState } from '@/components/EmptyState'
import { Inbox } from 'lucide-react'
import { FaqFilterBar } from './FaqFilterBar'
import { FaqListRow } from './FaqListRow'
import { useFaqList } from './useFaqList'
import { useFaqFilter } from './useFaqFilter'
import type { Faq } from '@/api/types'

interface Props {
  agentId: string
  selectedFaqId: string | null
  onSelectFaq: (id: string) => void
  onNewFaq: () => void
}

export function FaqList({ agentId, selectedFaqId, onSelectFaq, onNewFaq }: Props) {
  const { filters, setFilter, clearAll } = useFaqFilter()
  const { data, loading, error, totalPages } = useFaqList(agentId, filters)
  const [checked, setChecked] = useState<Set<string>>(new Set())

  function toggleCheck(id: string) {
    setChecked((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const hasActiveFilters = !!(filters.status || filters.q || filters.category_id)

  return (
    <div className="flex-1 flex flex-col bg-canvas overflow-hidden">
      <FaqFilterBar
        filters={filters}
        setFilter={setFilter}
        clearAll={clearAll}
        onNew={onNewFaq}
      />

      <div className="flex-1 overflow-auto">
        {loading && (
          <div className="p-4 space-y-2">
            {[1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-12" />)}
          </div>
        )}
        {error && (
          <div className="p-4">
            <Alert variant="destructive">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          </div>
        )}

        {!loading && data && data.items.length === 0 && (
          <EmptyState
            icon={Inbox}
            title="沒有符合條件的 FAQ"
            description={hasActiveFilters ? '試試調整篩選條件' : '建立第一筆 FAQ'}
            action={
              !hasActiveFilters
                ? <Button onClick={onNewFaq}>+ 新增 FAQ</Button>
                : <Button variant="outline" onClick={clearAll}>清除所有篩選</Button>
            }
          />
        )}

        {!loading && data && data.items.length > 0 && (
          <ul>
            {data.items.map((faq: Faq) => (
              <FaqListRow
                key={faq.id}
                faq={faq}
                selected={selectedFaqId === faq.id}
                checked={checked.has(faq.id)}
                onSelect={onSelectFaq}
                onToggleCheck={toggleCheck}
              />
            ))}
          </ul>
        )}
      </div>

      {data && data.total > 0 && (
        <div className="border-t border-border-default p-3 flex justify-between items-center text-sm bg-surface">
          <span className="text-text-secondary">
            第 {filters.page} / {totalPages} 頁，共 {data.total} 筆
          </span>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={filters.page <= 1}
              onClick={() => setFilter({ page: filters.page - 1 })}
            >
              上一頁
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={filters.page >= totalPages}
              onClick={() => setFilter({ page: filters.page + 1 })}
            >
              下一頁
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
