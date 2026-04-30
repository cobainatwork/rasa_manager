import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { FileText } from 'lucide-react'
import { EmptyState } from '@/components/EmptyState'
import { CategoryTree } from './CategoryTree'
import { FaqList } from './FaqList'
import { useCategoryTree } from './useCategoryTree'
import { useFaqFilter } from './useFaqFilter'

export function KnowledgePage() {
  const { id } = useParams<{ id: string }>()
  const categoryTree = useCategoryTree(id)
  const { setFilter } = useFaqFilter()
  const [selectedFaqId, setSelectedFaqId] = useState<string | null>(null)

  function handleCategorySelect(categoryId: string | null) {
    categoryTree.select(categoryId)
    setFilter({ category_id: categoryId ?? '' })
  }

  if (!id) return null

  return (
    <div className="flex h-[calc(100vh-4rem)]">
      <CategoryTree result={{ ...categoryTree, select: handleCategorySelect }} />

      <FaqList
        agentId={id}
        selectedFaqId={selectedFaqId}
        onSelectFaq={setSelectedFaqId}
        onNewFaq={() => alert('新增 FAQ — Phase 12b 實作 inline 表單')}
      />

      <aside className="w-[480px] border-l border-border-default bg-surface flex items-center justify-center">
        <EmptyState
          icon={FileText}
          title="選擇一筆 FAQ"
          description="從左側列表選一筆 FAQ 以檢視詳情"
        />
      </aside>
    </div>
  )
}
