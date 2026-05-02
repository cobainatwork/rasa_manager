import { useState, useMemo } from 'react'
import { useParams } from 'react-router-dom'
import { FileText } from 'lucide-react'
import { EmptyState } from '@/components/EmptyState'
import { ResizablePanelGroup, ResizablePanel, ResizableHandle } from '@/components/ui/resizable'
import { CategoryTree } from './CategoryTree'
import { FaqList } from './FaqList'
import { FaqDetail } from './FaqDetail'
import { NewFaqForm } from './NewFaqForm'
import { useCategoryTree } from './useCategoryTree'
import { useFaqFilter } from './useFaqFilter'
import { findInTree } from '@/lib/categories'

type RightPaneMode = 'detail' | 'new' | 'empty'

export function KnowledgePage() {
  const { id } = useParams<{ id: string }>()
  const [selectedFaqId, setSelectedFaqId] = useState<string | null>(null)
  const [rightMode, setRightMode] = useState<RightPaneMode>('empty')
  const [listVersion, setListVersion] = useState(0)

  function clearFaqSelection() {
    setSelectedFaqId(null)
    setRightMode('empty')
  }

  function handleImportDone(mode: 'append' | 'replace') {
    setListVersion((v) => v + 1)
    // replace 模式可能刪除了目前選取的 FAQ，清空右欄避免顯示殘留資料
    if (mode === 'replace') clearFaqSelection()
  }

  const categoryTree = useCategoryTree(id, handleImportDone)
  const { setFilter } = useFaqFilter()

  const canAddFaq = useMemo(() => {
    if (!categoryTree.selectedId) return false
    const node = findInTree(categoryTree.tree, categoryTree.selectedId)
    return node !== null && (node.children?.length ?? 0) === 0
  }, [categoryTree.selectedId, categoryTree.tree])

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

  function handleFaqDeleted() {
    clearFaqSelection()
    setListVersion((v) => v + 1)
  }

  if (!id) return null

  return (
    <ResizablePanelGroup orientation="horizontal" className="h-[calc(100vh-4rem)]">
      <ResizablePanel defaultSize={20} minSize="180px" maxSize="320px">
        <CategoryTree result={{ ...categoryTree, select: handleCategorySelect }} />
      </ResizablePanel>

      <ResizableHandle />

      <ResizablePanel defaultSize={45} minSize={15}>
        <FaqList
          key={listVersion}
          agentId={id}
          selectedFaqId={selectedFaqId}
          onSelectFaq={handleSelectFaq}
          onNewFaq={handleNewFaq}
          canAdd={canAddFaq}
        />
      </ResizablePanel>

      <ResizableHandle withHandle />

      <ResizablePanel defaultSize={35} minSize="320px">
        <aside className="h-full bg-surface flex flex-col">
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
              onDeleted={handleFaqDeleted}
            />
          )}
        </aside>
      </ResizablePanel>
    </ResizablePanelGroup>
  )
}
