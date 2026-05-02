import { useState } from 'react'
import { Skeleton } from '@/components/ui/skeleton'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Checkbox } from '@/components/ui/checkbox'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog'
import { EmptyState } from '@/components/EmptyState'
import { Inbox } from 'lucide-react'
import { FaqFilterBar } from './FaqFilterBar'
import { FaqListRow } from './FaqListRow'
import { useFaqList } from './useFaqList'
import { useFaqFilter } from './useFaqFilter'
import * as api from '@/api/endpoints/faqs'
import { extractErrorMessage } from '@/api/client'
import { toast } from 'sonner'
import type { Faq } from '@/api/types'

interface Props {
  agentId: string
  selectedFaqId: string | null
  onSelectFaq: (id: string) => void
  onNewFaq: () => void
  canAdd?: boolean
}

export function FaqList({ agentId, selectedFaqId, onSelectFaq, onNewFaq, canAdd = false }: Props) {
  const { filters, setFilter, clearAll } = useFaqFilter()
  const [version, setVersion] = useState(0)
  const { data, loading, error, totalPages } = useFaqList(agentId, filters, version)
  const [checked, setChecked] = useState<Set<string>>(new Set())
  const [busy, setBusy] = useState(false)

  // ── 全選狀態（僅作用於當前頁） ─────────────────────────────────────────────
  const pageIds = data?.items.map((f) => f.id) ?? []
  const pageCheckedCount = pageIds.filter((id) => checked.has(id)).length
  const pageAllSelected = pageIds.length > 0 && pageCheckedCount === pageIds.length
  const pageSomeSelected = pageCheckedCount > 0 && !pageAllSelected

  function toggleSelectAll() {
    if (pageAllSelected) {
      const next = new Set(checked)
      pageIds.forEach((id) => next.delete(id))
      setChecked(next)
    } else {
      setChecked(new Set([...checked, ...pageIds]))
    }
  }

  function toggleCheck(id: string) {
    setChecked((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  function refreshList() {
    setChecked(new Set())
    setVersion((v) => v + 1)
  }

  async function bulkAction(label: string, fn: (id: string) => Promise<unknown>) {
    if (!checked.size || busy) return
    setBusy(true)
    const ids = [...checked]
    const results = await Promise.allSettled(ids.map((id) => fn(id)))
    const ok = results.filter((r) => r.status === 'fulfilled').length
    const fail = ids.length - ok
    if (ok > 0) {
      toast.success(`${label} ${ok} 筆成功${fail > 0 ? `，${fail} 筆失敗` : ''}`)
    } else {
      const firstErr = results.find((r) => r.status === 'rejected') as PromiseRejectedResult | undefined
      toast.error(`${label}失敗：${firstErr ? extractErrorMessage(firstErr.reason) : '未知錯誤'}`)
    }
    setBusy(false)
    refreshList()
  }

  const hasActiveFilters = !!(filters.status || filters.q || filters.category_id)

  return (
    // h-full 確保中間欄填滿 ResizablePanel，避免底部出現色塊
    <div className="h-full flex flex-col bg-canvas">
      <FaqFilterBar
        filters={filters}
        setFilter={setFilter}
        clearAll={clearAll}
        onNew={onNewFaq}
        canAdd={canAdd}
      />

      {/* 批次操作列：勾選任一筆後出現 */}
      {checked.size > 0 && (
        <div className="flex items-center gap-2 px-4 py-2 bg-brand-50 border-b border-brand-200 text-sm shrink-0">
          <span className="text-brand-700 font-medium">已選 {checked.size} 筆</span>
          <Button
            size="sm"
            variant="ghost"
            className="h-7 px-2 text-xs"
            onClick={() => setChecked(new Set())}
          >
            取消
          </Button>
          <div className="ml-auto flex gap-2">
            <Button
              size="sm"
              variant="outline"
              className="h-7 text-xs"
              disabled={busy}
              onClick={() => bulkAction('送審', (id) => api.submit(agentId, id))}
            >
              批次送審
            </Button>
            <Button
              size="sm"
              variant="outline"
              className="h-7 text-xs"
              disabled={busy}
              onClick={() => bulkAction('核准', (id) => api.approve(agentId, id))}
            >
              批次核准
            </Button>
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button size="sm" variant="destructive" className="h-7 text-xs" disabled={busy}>
                  批次刪除
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>批次刪除 {checked.size} 筆 FAQ？</AlertDialogTitle>
                  <AlertDialogDescription>
                    此操作將同時清除版本歷史，無法復原。
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>取消</AlertDialogCancel>
                  <AlertDialogAction
                    className="bg-red-600 hover:bg-red-700"
                    onClick={() => bulkAction('刪除', (id) => api.deleteFaq(agentId, id))}
                  >
                    確認刪除
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          </div>
        </div>
      )}

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
              hasActiveFilters
                ? <Button variant="outline" onClick={clearAll}>清除所有篩選</Button>
                : canAdd
                ? <Button onClick={onNewFaq}>+ 新增 FAQ</Button>
                : undefined
            }
          />
        )}

        {!loading && data && data.items.length > 0 && (
          <>
            {/* 全選列 */}
            <div className="flex items-center gap-3 px-4 py-2 border-b border-border-default bg-surface sticky top-0 z-10">
              <Checkbox
                checked={pageAllSelected ? true : pageSomeSelected ? 'indeterminate' : false}
                onCheckedChange={toggleSelectAll}
                aria-label="全選本頁"
              />
              <span className="text-xs text-text-secondary select-none">
                {pageAllSelected ? '取消全選' : '全選本頁'}
                {pageSomeSelected && ` (已選 ${pageCheckedCount} / ${pageIds.length})`}
              </span>
            </div>
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
          </>
        )}
      </div>

      {data && data.total > 0 && (
        <div className="border-t border-border-default p-3 flex justify-between items-center text-sm bg-surface shrink-0">
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
