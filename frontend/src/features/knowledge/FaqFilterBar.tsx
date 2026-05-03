import { Search, X, Plus } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import type { FaqFilters } from './useFaqFilter'

const STATUS_OPTIONS = [
  { v: 'all', label: '全部狀態' },
  { v: 'draft', label: '草稿' },
  { v: 'pending', label: '待審核' },
  { v: 'approved', label: '已核准' },
  { v: 'rejected', label: '已退回' },
  { v: 'synced', label: '已同步' },
]

interface Props {
  filters: FaqFilters
  setFilter: (p: Partial<FaqFilters>) => void
  clearAll: () => void
  onNew: () => void
  canAdd?: boolean
}

export function FaqFilterBar({ filters, setFilter, clearAll, onNew, canAdd = false }: Props) {
  const hasActive = filters.status || filters.category_id || filters.q
  return (
    <div className="border-b border-border-default p-3 space-y-2 bg-surface">
      <div className="flex gap-2 items-center">
        <div className="relative flex-1">
          <Search
            className="absolute left-2 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted"
            strokeWidth={1.5}
          />
          <Input
            value={filters.q}
            onChange={(e) => setFilter({ q: e.target.value })}
            placeholder="搜尋問題或答案..."
            className="pl-8"
          />
        </div>
        <Select
          value={filters.status || 'all'}
          onValueChange={(v) => setFilter({ status: v === 'all' ? '' : v })}
        >
          <SelectTrigger className="w-32" aria-label="狀態篩選"><SelectValue /></SelectTrigger>
          <SelectContent>
            {STATUS_OPTIONS.map((o) => (
              <SelectItem key={o.v} value={o.v}>{o.label}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Button
          onClick={onNew}
          disabled={!canAdd}
          title={!canAdd ? '請先選擇子分類（末層）才能新增 FAQ' : undefined}
        >
          <Plus className="w-4 h-4 mr-1" strokeWidth={1.5} /> 新增
        </Button>
      </div>

      {hasActive && (
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs text-text-muted">已套用：</span>
          {filters.status && (
            <Badge
              variant="secondary"
              className="cursor-pointer"
              onClick={() => setFilter({ status: '' })}
            >
              狀態:{filters.status} <X className="w-3 h-3 ml-1" />
            </Badge>
          )}
          {filters.category_id && (
            <Badge
              variant="secondary"
              className="cursor-pointer"
              onClick={() => setFilter({ category_id: '' })}
            >
              分類已選 <X className="w-3 h-3 ml-1" />
            </Badge>
          )}
          {filters.q && (
            <Badge
              variant="secondary"
              className="cursor-pointer"
              onClick={() => setFilter({ q: '' })}
            >
              搜尋:{filters.q} <X className="w-3 h-3 ml-1" />
            </Badge>
          )}
          <Button variant="ghost" size="sm" onClick={clearAll}>清除全部</Button>
        </div>
      )}
    </div>
  )
}
