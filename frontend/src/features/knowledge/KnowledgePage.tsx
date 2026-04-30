import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { FileText } from 'lucide-react'
import { EmptyState } from '@/components/EmptyState'
import { CategoryTree } from './CategoryTree'
import { FaqList } from './FaqList'
import { FaqDetail } from './FaqDetail'
import { NewFaqForm } from './NewFaqForm'
import { useCategoryTree } from './useCategoryTree'
import { useFaqFilter } from './useFaqFilter'

type RightPaneMode = 'detail' | 'new' | 'empty'

export function KnowledgePage() {
  const { id } = useParams<{ id: string }>()
  const categoryTree = useCategoryTree(id)
  const { setFilter } = useFaqFilter()
  const [selectedFaqId, setSelectedFaqId] = useState<string | null>(null)
  const [rightMode, setRightMode] = useState<RightPaneMode>('empty')
  const [listVersion, setListVersion] = useState(0)

  function handleCategorySelect(categoryId: string | null) {
    categoryTree.select(categoryId)
    setFilter({ category_id: categoryId ?? '' })
  }

  function handleSelectFaq(faqId: string) {
    setSelectedFaqId(faqId)
    setRightMode('detail')
  }

  function handleNewFaq() {
    setSelectedFaqId(null)
    setRightMode('new')
  }

  function handleFaqCreated(newId: string) {
    setSelectedFaqId(newId)
    setRightMode('detail')
    setListVersion((v) => v + 1)
  }

  function handleFaqChanged() {
    setListVersion((v) => v + 1)
  }

  if (!id) return null

  return (
    <div className="flex h-[calc(100vh-4rem)]">
      <CategoryTree result={{ ...categoryTree, select: handleCategorySelect }} />

      <FaqList
        key={listVersion}
        agentId={id}
        selectedFaqId={selectedFaqId}
        onSelectFaq={handleSelectFaq}
        onNewFaq={handleNewFaq}
      />

      <aside className="w-[480px] border-l border-border-default bg-surface flex flex-col">
        {rightMode === 'empty' && (
          <div className="flex-1 flex items-center justify-center">
            <EmptyState icon={FileText} title="選擇一筆 FAQ" description="從左側列表選一筆 FAQ 以檢視詳情" />
          </div>
        )}
        {rightMode === 'new' && (
          <NewFaqForm
            agentId={id}
            categoryTree={categoryTree.tree}
            defaultCategoryId={categoryTree.selectedId}
            onCreated={handleFaqCreated}
            onCancel={() => setRightMode('empty')}
          />
        )}
        {rightMode === 'detail' && selectedFaqId && (
          <FaqDetail
            agentId={id}
            faqId={selectedFaqId}
            categoryTree={categoryTree.tree}
            onChanged={handleFaqChanged}
          />
        )}
      </aside>
    </div>
  )
}
