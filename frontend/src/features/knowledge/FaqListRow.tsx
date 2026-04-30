import { Lock } from 'lucide-react'
import { Checkbox } from '@/components/ui/checkbox'
import { cn } from '@/lib/utils'
import { relativeTime } from '@/lib/format'
import type { Faq } from '@/api/types'

const STATUS_BADGE: Record<Faq['status'], string> = {
  draft: 'bg-slate-100 text-slate-700',
  pending: 'bg-amber-100 text-amber-800',
  approved: 'bg-emerald-100 text-emerald-800',
  rejected: 'bg-red-100 text-red-800',
  synced: 'bg-blue-100 text-blue-800',
}

const STATUS_LABEL: Record<Faq['status'], string> = {
  draft: '草稿',
  pending: '待審',
  approved: '已核准',
  rejected: '已退回',
  synced: '已同步',
}

interface Props {
  faq: Faq
  selected: boolean
  checked: boolean
  onSelect: (id: string) => void
  onToggleCheck: (id: string) => void
}

export function FaqListRow({ faq, selected, checked, onSelect, onToggleCheck }: Props) {
  return (
    <div
      onClick={() => onSelect(faq.id)}
      className={cn(
        'flex items-center gap-3 px-4 py-3 border-b border-border-default cursor-pointer text-sm',
        selected ? 'bg-brand-50' : 'hover:bg-subtle'
      )}
    >
      <Checkbox
        checked={checked}
        onCheckedChange={() => onToggleCheck(faq.id)}
        onClick={(e) => e.stopPropagation()}
      />
      <span className="flex-1 truncate">{faq.question}</span>
      <span
        className={cn(
          'inline-flex px-2 py-0.5 rounded text-xs font-medium',
          STATUS_BADGE[faq.status]
        )}
      >
        {STATUS_LABEL[faq.status]}
      </span>
      <span className="text-xs text-text-muted w-16 text-right">v{faq.version}</span>
      <span className="text-xs text-text-muted w-20 text-right">{relativeTime(faq.updated_at)}</span>
      <span className="w-6 flex justify-center">
        {faq.locked_by_username && (
          <Lock className="w-3.5 h-3.5 text-amber-600" strokeWidth={1.5} />
        )}
      </span>
    </div>
  )
}
