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
import { FAQ_STATUS_LABEL } from './faqStatus'
import type { CategoryNode } from '@/api/types'

interface Props {
  agentId: string
  faqId: string
  categoryTree: CategoryNode[]
  onChanged: () => void
  onDeleted?: () => void
}

export function FaqDetail({ agentId, faqId, categoryTree, onChanged, onDeleted }: Props) {
  const { faq, loading, update, reload } = useFaqDetail(agentId, faqId, onChanged)

  function handleStatusChanged() {
    reload()
    onChanged()
  }

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
    <ScrollArea className="h-full w-full">
      <div className="p-4 space-y-5 min-w-0 w-full overflow-x-hidden">
        <div className="flex items-center gap-2 sticky top-0 bg-surface py-2 -mx-4 px-4 border-b border-border-default z-sticky min-w-0">
          <span className="font-semibold truncate flex-1 min-w-0">{faq.question || '（未命名）'}</span>
          <Badge variant="outline" className="shrink-0">{FAQ_STATUS_LABEL[faq.status]}</Badge>
        </div>

        <EditableQuestion value={faq.question} onSave={(v) => update({ question: v })} />
        <EditableAnswer value={faq.answer} onSave={(v) => update({ answer: v })} />
        <EditableCategory categoryId={faq.category_id} tree={categoryTree} onSave={(v) => update({ category_id: v })} />
        <EditableTags tags={faq.tags} onSave={(v) => update({ tags: v })} />

        <StatusActions agentId={agentId} faq={faq} onChanged={handleStatusChanged} onDeleted={onDeleted} />
        <VersionTimeline agentId={agentId} faqId={faqId} />
      </div>
    </ScrollArea>
  )
}
