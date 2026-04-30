import { useState, useRef, useEffect } from 'react'
import { ChevronRight, ChevronDown, MoreHorizontal, Pencil, Plus, Trash2 } from 'lucide-react'
import { Input } from '@/components/ui/input'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { cn } from '@/lib/utils'
import type { CategoryNode } from '@/api/types'

interface Props {
  node: CategoryNode
  depth: number
  selectedId: string | null
  onSelect: (id: string) => void
  onRename: (id: string, name: string) => void
  onAddChild: (parentId: string) => void
  onRemove: (id: string) => void
}

export function CategoryTreeNode({
  node,
  depth,
  selectedId,
  onSelect,
  onRename,
  onAddChild,
  onRemove,
}: Props) {
  const [expanded, setExpanded] = useState(true)
  const [editing, setEditing] = useState(false)
  const [name, setName] = useState(node.name)
  const inputRef = useRef<HTMLInputElement>(null)

  const isSelected = selectedId === node.id
  const hasChildren = node.children.length > 0

  useEffect(() => {
    if (editing && inputRef.current) {
      inputRef.current.focus()
      inputRef.current.select()
    }
  }, [editing])

  function commitRename() {
    setEditing(false)
    if (name.trim() && name !== node.name) onRename(node.id, name.trim())
    else setName(node.name)
  }

  return (
    <li>
      <div
        className={cn(
          'group flex items-center gap-1 py-1 px-2 rounded cursor-pointer text-sm',
          isSelected
            ? 'bg-brand-50 text-brand-700 border-l-2 border-brand-500'
            : 'hover:bg-subtle'
        )}
        style={{ paddingLeft: `${depth * 12 + 8}px` }}
        onClick={() => onSelect(node.id)}
      >
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation()
            if (hasChildren) setExpanded(!expanded)
          }}
          className="w-4 h-4 flex items-center justify-center shrink-0"
          aria-label={expanded ? '收合' : '展開'}
        >
          {hasChildren && (
            expanded
              ? <ChevronDown className="w-3 h-3" strokeWidth={1.5} />
              : <ChevronRight className="w-3 h-3" strokeWidth={1.5} />
          )}
        </button>

        {editing ? (
          <Input
            ref={inputRef}
            value={name}
            onChange={(e) => setName(e.target.value)}
            onBlur={commitRename}
            onKeyDown={(e) => {
              if (e.key === 'Enter') { e.preventDefault(); commitRename() }
              if (e.key === 'Escape') { setEditing(false); setName(node.name) }
            }}
            onClick={(e) => e.stopPropagation()}
            className="h-6 text-sm"
          />
        ) : (
          <span
            className="flex-1 truncate"
            onDoubleClick={(e) => { e.stopPropagation(); setEditing(true) }}
          >
            {node.name}
          </span>
        )}

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button
              type="button"
              onClick={(e) => e.stopPropagation()}
              className="opacity-0 group-hover:opacity-100 p-0.5 rounded hover:bg-white"
              aria-label="更多操作"
            >
              <MoreHorizontal className="w-3.5 h-3.5" strokeWidth={1.5} />
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={() => setEditing(true)}>
              <Pencil className="w-3.5 h-3.5 mr-2" strokeWidth={1.5} /> 重新命名
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => onAddChild(node.id)}>
              <Plus className="w-3.5 h-3.5 mr-2" strokeWidth={1.5} /> 新增子分類
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => onRemove(node.id)} className="text-red-600">
              <Trash2 className="w-3.5 h-3.5 mr-2" strokeWidth={1.5} /> 刪除
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {hasChildren && expanded && (
        <ul>
          {node.children.map((child) => (
            <CategoryTreeNode
              key={child.id}
              node={child}
              depth={depth + 1}
              selectedId={selectedId}
              onSelect={onSelect}
              onRename={onRename}
              onAddChild={onAddChild}
              onRemove={onRemove}
            />
          ))}
        </ul>
      )}
    </li>
  )
}
