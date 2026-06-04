import { useState, useMemo } from 'react'
import { useParams } from 'react-router-dom'
import { FileText } from 'lucide-react'
import { EmptyState } from '@/components/EmptyState'
import { ResizablePanelGroup, ResizablePanel, ResizableHandle } from '@/components/ui/resizable'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { CategoryTree } from './CategoryTree'
import { FaqList } from './FaqList'
import { FaqDetail } from './FaqDetail'
import { NewFaqForm } from './NewFaqForm'
import { useCategoryTree } from './useCategoryTree'
import { useFaqFilter } from './useFaqFilter'
import { useFaqSelectionPersistence } from './useFaqSelectionPersistence'
import { findInTree } from '@/lib/categories'

export function KnowledgePage() {
  const { id } = useParams<{ id: string }>()

  // 選取 FAQ + 右欄模式 + localStorage 持久化（抽至 hook）
  const {
    selectedFaqId,
    rightMode,
    selectFaq,
    openNewForm,
    cancelNewForm,
    clearSelection,
  } = useFaqSelectionPersistence(id)

  // listVersion 為純 in-memory 計數器，用以強制 FaqList 重掛載刷新；不需要持久化
  const [listVersion, setListVersion] = useState(0)

  function handleImportDone(mode: 'append' | 'replace') {
    setListVersion((v) => v + 1)
    // replace 模式可能刪除了目前選取的 FAQ，清空右欄避免顯示殘留資料
    if (mode === 'replace') clearSelection()
  }

  const { filters, setFilter } = useFaqFilter(id)

  function handleCategoryRemoved(deletedId: string) {
    // 任何分類被刪除，都刷新 FAQ 列表以反映最新狀態
    setListVersion((v) => v + 1)
    // 若當前篩選器正好篩選的是被刪除的分類，清空篩選器並重置右欄
    if (filters.category_id === deletedId) {
      setFilter({ category_id: '' })
      clearSelection()
    }
  }

  const categoryTree = useCategoryTree(id, handleImportDone, handleCategoryRemoved)

  const canAddFaq = useMemo(() => {
    if (!categoryTree.selectedId) return false
    const node = findInTree(categoryTree.tree, categoryTree.selectedId)
    return node !== null && (node.children?.length ?? 0) === 0
  }, [categoryTree.selectedId, categoryTree.tree])

  function handleCategorySelect(categoryId: string | null) {
    categoryTree.select(categoryId)
    setFilter({ category_id: categoryId ?? '' })
  }

  function handleFaqCreated(newId: string) {
    selectFaq(newId)
    setListVersion((v) => v + 1)
  }

  function handleFaqChanged() {
    setListVersion((v) => v + 1)
  }

  function handleFaqDeleted() {
    clearSelection()
    setListVersion((v) => v + 1)
  }

  if (!id) return null

  const rightPane = (
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
          onCancel={cancelNewForm}
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
  )

  return (
    <>
      {/* Mobile: < md (768px) — 以 Tabs 切換三個面板，避免三欄擠壓 */}
      <div className="md:hidden h-full flex flex-col">
        <Tabs defaultValue="list" className="h-full flex flex-col">
          <TabsList className="mx-3 mt-3 self-start">
            <TabsTrigger value="categories">分類</TabsTrigger>
            <TabsTrigger value="list">FAQ 列表</TabsTrigger>
            <TabsTrigger value="detail">詳情</TabsTrigger>
          </TabsList>
          <TabsContent value="categories" className="flex-1 overflow-hidden mt-2">
            <CategoryTree result={{ ...categoryTree, select: handleCategorySelect }} />
          </TabsContent>
          <TabsContent value="list" className="flex-1 overflow-hidden mt-2">
            <FaqList
              key={`m-${listVersion}`}
              agentId={id}
              selectedFaqId={selectedFaqId}
              onSelectFaq={selectFaq}
              onNewFaq={openNewForm}
              canAdd={canAddFaq}
            />
          </TabsContent>
          <TabsContent value="detail" className="flex-1 overflow-hidden mt-2">
            {rightPane}
          </TabsContent>
        </Tabs>
      </div>

      {/* Desktop: ≥ md — 三欄 ResizablePanelGroup（原設計） */}
      <div className="hidden md:block h-full">
        <ResizablePanelGroup orientation="horizontal" className="h-full">
          <ResizablePanel defaultSize={20} minSize="180px" maxSize="320px" className="h-full !overflow-hidden">
            <CategoryTree result={{ ...categoryTree, select: handleCategorySelect }} />
          </ResizablePanel>

          <ResizableHandle />

          <ResizablePanel defaultSize={45} minSize={15} className="h-full !overflow-hidden">
            <FaqList
              key={listVersion}
              agentId={id}
              selectedFaqId={selectedFaqId}
              onSelectFaq={selectFaq}
              onNewFaq={openNewForm}
              canAdd={canAddFaq}
            />
          </ResizablePanel>

          <ResizableHandle withHandle />

          <ResizablePanel defaultSize={35} minSize="320px" className="h-full">
            {rightPane}
          </ResizablePanel>
        </ResizablePanelGroup>
      </div>
    </>
  )
}
