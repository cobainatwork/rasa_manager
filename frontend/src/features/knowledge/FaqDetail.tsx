import { ScrollArea } from '@/components/ui/scroll-area'
import { Skeleton } from '@/components/ui/skeleton'
import { Badge } from '@/components/ui/badge'
import { useFaqDetail } from './useFaqDetail'
import { EditableQuestion } from './EditableQuestion'
import { EditableAnswer } from './EditableAnswer'
import { EditableCategory } from './EditableCategory'
import { EditableTags } from './EditableTags'
import { StatusActions } from './StatusActions'
import { VersionTimeline } from './VersionTimeline'
import type { CategoryNode } from '@/api/types'

interface Props {
  agentId: string
  faqId: string
  categoryTree: CategoryNode[]
  onChanged: () => void
}

const STATUS_LABEL: Record<string, string> = {
  draft: '草稿', pending: '待審核', approved: '已核准', rejected: '已退回', synced: '已同步',
}

export function FaqDetail({ agentId, faqId, categoryTree, onChanged }: Props) {
  const { faq, loading, update } = useFaqDetail(agentId, faqId)

  if (loading || !faq) {
    return (
      <div className="p-6 space-y-4">
        <Skeleton className="h-8" />
        <Skeleton className="h-20" />
        <Skeleton className="h-40" />
      </div>
    )
  }

  return (
    <ScrollArea className="h-full">
      <div className="p-6 space-y-5">
        <div className="flex items-center gap-2 sticky top-0 bg-surface py-2 -mx-6 px-6 border-b border-border-default z-sticky">
          <span className="font-semibold truncate flex-1">{faq.question || '（未命名）'}</span>
          <Badge variant="outline">{STATUS_LABEL[faq.status]}</Badge>
        </div>

        <EditableQuestion value={faq.question} onSave={(v) => update({ question: v })} />
        <EditableAnswer value={faq.answer} onSave={(v) => update({ answer: v })} />
        <EditableCategory categoryId={faq.category_id} tree={categoryTree} onSave={(v) => update({ category_id: v })} />
        <EditableTags tags={faq.tags} onSave={(v) => update({ tags: v })} />

        <StatusActions agentId={agentId} faq={faq} onChanged={onChanged} />
        <VersionTimeline agentId={agentId} faqId={faqId} />
      </div>
    </ScrollArea>
  )
}
