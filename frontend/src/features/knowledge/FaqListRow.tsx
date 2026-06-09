import { memo } from 'react'
import { Lock } from 'lucide-react'
import { Checkbox } from '@/components/ui/checkbox'
import { cn } from '@/lib/utils'
import { relativeTime } from '@/lib/format'
import { FAQ_STATUS_LABEL, FAQ_STATUS_BADGE_CLASS } from './faqStatus'
import type { Faq } from '@/api/types'

interface Props {
  faq: Faq
  selected: boolean
  checked: boolean
  onSelect: (id: string) => void
  onToggleCheck: (id: string) => void
}

export const FaqListRow = memo(function FaqListRow({ faq, selected, checked, onSelect, onToggleCheck }: Props) {
  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => onSelect(faq.id)}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          onSelect(faq.id)
        }
      }}
      className={cn(
        'flex items-start gap-3 px-4 py-3 border-b border-border-default cursor-pointer text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-inset',
        selected
          ? 'bg-brand-500/[0.10] shadow-[inset_3px_0_0_theme(colors.brand.500)] text-brand-700'
          : 'hover:bg-black/[0.04]'
      )}
    >
      <Checkbox
        checked={checked}
        onCheckedChange={() => onToggleCheck(faq.id)}
        onClick={(e) => e.stopPropagation()}
        className="mt-0.5"
      />

      <span className="flex-1 min-w-0 line-clamp-2 leading-snug">{faq.question}</span>

      <span
        className={cn(
          'inline-flex shrink-0 px-2 py-0.5 rounded text-xs font-medium mt-0.5',
          FAQ_STATUS_BADGE_CLASS[faq.status]
        )}
      >
        {FAQ_STATUS_LABEL[faq.status]}
      </span>
      <span className="text-xs text-text-muted w-12 text-right shrink-0 mt-1">v{faq.version}</span>
      <span className="text-xs text-text-muted w-16 text-right shrink-0 mt-1">{relativeTime(faq.updated_at)}</span>
      <span className="w-5 flex justify-center shrink-0 mt-0.5">
        {faq.locked_by_username && (
          // amber-700：與 AgentCard pending highlight 對齊的中性警示色。
          // 兩個用例語意略有差異（此為鎖定通知、AgentCard 為待審行動召喚），
          // 暫不抽 design token（YAGNI / rule of three：第 3 個用例出現時再抽）。
          <Lock className="w-3.5 h-3.5 text-amber-700" strokeWidth={1.5} />
        )}
      </span>
    </div>
  )
})
