import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { Plus } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { ScrollArea } from '@/components/ui/scroll-area'
import { CategoryTreeNode } from './CategoryTreeNode'
import type { UseCategoryTreeResult } from './useCategoryTree'

interface Props {
  result: UseCategoryTreeResult
}

// ── 展開狀態持久化 ────────────────────────────────────────────────────────────
// 以 agent 為單位，儲存於 localStorage，預設全部收合
function loadExpanded(agentId: string | undefined): Record<string, boolean> {
  if (!agentId) return {}
  try {
    const raw = localStorage.getItem(`kb_cat_expanded_${agentId}`)
    return raw ? (JSON.parse(raw) as Record<string, boolean>) : {}
  } catch {
    return {}
  }
}

function saveExpanded(agentId: string, map: Record<string, boolean>) {
  try {
    localStorage.setItem(`kb_cat_expanded_${agentId}`, JSON.stringify(map))
  } catch { /* ignore */ }
}

function useCategoryExpanded(agentId: string | undefined) {
  const [expandedMap, setExpandedMap] = useState<Record<string, boolean>>(
    () => loadExpanded(agentId),
  )

  // 切換 agent 時重新從 localStorage 載入（安全邊界）
  useEffect(() => {
    setExpandedMap(loadExpanded(agentId))
  }, [agentId])

  function isExpanded(id: string): boolean {
    return expandedMap[id] ?? false
  }

  function toggle(id: string) {
    setExpandedMap((prev) => {
      const next = { ...prev, [id]: !prev[id] }
      if (agentId) saveExpanded(agentId, next)
      return next
    })
  }

  function expand(id: string) {
    setExpandedMap((prev) => {
      if (prev[id]) return prev          // 已展開，無需更新
      const next = { ...prev, [id]: true }
      if (agentId) saveExpanded(agentId, next)
      return next
    })
  }

  return { isExpanded, toggle, expand }
}
// ─────────────────────────────────────────────────────────────────────────────

export function CategoryTree({ result }: Props) {
  const { id: agentId } = useParams<{ id: string }>()
  const { isExpanded, toggle, expand } = useCategoryExpanded(agentId)

  const {
    tree, loading, selectedId, pendingRenameId,
    select, rename, addChild, remove, clearPendingRename,
    exportCategory, importCategory, syncCategory,
  } = result

  // 新增子分類時自動展開父節點，讓 rename input 立即可見
  function handleAddChild(parentId: string | null) {
    if (parentId) expand(parentId)
    return addChild(parentId)
  }

  return (
    <aside className="h-full bg-surface flex flex-col">
      <div className="p-3 border-b border-border-default flex items-center justify-between">
        <h2 className="text-sm font-semibold">類別</h2>
        <Button variant="ghost" size="icon" onClick={() => addChild(null)} aria-label="新增根類別">
          <Plus className="w-4 h-4" strokeWidth={1.5} />
        </Button>
      </div>
      <ScrollArea className="flex-1">
        <div className="p-2">
          {loading && (
            <div className="space-y-2">
              <Skeleton className="h-6" />
              <Skeleton className="h-6" />
              <Skeleton className="h-6" />
            </div>
          )}
          {!loading && tree.length === 0 && (
            <p className="text-xs text-text-muted text-center py-8">尚無分類</p>
          )}
          {!loading && tree.length > 0 && (
            <ul>
              {tree.map((node) => (
                <CategoryTreeNode
                  key={node.id}
                  node={node}
                  depth={0}
                  selectedId={selectedId}
                  pendingRenameId={pendingRenameId}
                  isExpanded={isExpanded}
                  onToggleExpand={toggle}
                  onSelect={select}
                  onRename={rename}
                  onAddChild={handleAddChild}
                  onRemove={remove}
                  onClearPendingRename={clearPendingRename}
                  onExport={exportCategory}
                  onImport={importCategory}
                  onSync={syncCategory}
                />
              ))}
            </ul>
          )}
        </div>
      </ScrollArea>
    </aside>
  )
}
