import { useState, useEffect, useMemo } from 'react'
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

  // 以 localStorage 記憶上次選取的 FAQ，跨路由導覽後能自動還原
  const [selectedFaqId, setSelectedFaqIdRaw] = useState<string | null>(() => {
    if (!id) return null
    try { return localStorage.getItem(`kb_selected_faq_${id}`) ?? null } catch { return null }
  })
  // 若有還原的 faqId，直接顯示詳情；否則顯示空狀態
  const [rightMode, setRightMode] = useState<RightPaneMode>(() => {
    if (!id) return 'empty'
    try { return localStorage.getItem(`kb_selected_faq_${id}`) ? 'detail' : 'empty' } catch { return 'empty' }
  })
  const [listVersion, setListVersion] = useState(0)

  // 切換 agent 時，從 localStorage 還原新 agent 的選取 FAQ
  useEffect(() => {
    if (!id) { setSelectedFaqIdRaw(null); setRightMode('empty'); return }
    try {
      const faqId = localStorage.getItem(`kb_selected_faq_${id}`)
      setSelectedFaqIdRaw(faqId)
      setRightMode(faqId ? 'detail' : 'empty')
    } catch { setSelectedFaqIdRaw(null); setRightMode('empty') }
  }, [id])

  // 包裝 setter：同步寫入 localStorage
  function setSelectedFaqId(faqId: string | null) {
    setSelectedFaqIdRaw(faqId)
    if (!id) return
    try {
      if (faqId) localStorage.setItem(`kb_selected_faq_${id}`, faqId)
      else localStorage.removeItem(`kb_selected_faq_${id}`)
    } catch { /* ignore */ }
  }

  function clearFaqSelection() {
    setSelectedFaqId(null)
    setRightMode('empty')
  }

  function handleImportDone(mode: 'append' | 'replace') {
    setListVersion((v) => v + 1)
    // replace 模式可能刪除了目前選取的 FAQ，清空右欄避免顯示殘留資料
    if (mode === 'replace') clearFaqSelection()
  }

  const { filters, setFilter } = useFaqFilter(id)

  function handleCategoryRemoved(deletedId: string) {
    // 任何分類被刪除，都刷新 FAQ 列表以反映最新狀態
    setListVersion((v) => v + 1)
    // 若當前篩選器正好篩選的是被刪除的分類，清空篩選器並重置右欄
    if (filters.category_id === deletedId) {
      setFilter({ category_id: '' })
      clearFaqSelection()
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
          onSelectFaq={handleSelectFaq}
          onNewFaq={handleNewFaq}
          canAdd={canAddFaq}
        />
      </ResizablePanel>

      <ResizableHandle withHandle />

      <ResizablePanel defaultSize={35} minSize="320px" className="h-full">
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
