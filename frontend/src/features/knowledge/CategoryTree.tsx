import { Plus } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { ScrollArea } from '@/components/ui/scroll-area'
import { CategoryTreeNode } from './CategoryTreeNode'
import type { UseCategoryTreeResult } from './useCategoryTree'

interface Props {
  result: UseCategoryTreeResult
}

export function CategoryTree({ result }: Props) {
  const { tree, loading, selectedId, select, rename, addChild, remove } = result

  return (
    <aside className="w-60 border-r border-border-default bg-surface flex flex-col">
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
                  onSelect={select}
                  onRename={rename}
                  onAddChild={addChild}
                  onRemove={remove}
                />
              ))}
            </ul>
          )}
        </div>
      </ScrollArea>
    </aside>
  )
}
