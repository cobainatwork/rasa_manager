import { useState, useRef, useEffect } from 'react'
import { ChevronRight, ChevronDown, MoreHorizontal, Pencil, Plus, Trash2, Download, Upload, RefreshCw } from 'lucide-react'
import { Input } from '@/components/ui/input'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuSub,
  DropdownMenuSubContent,
  DropdownMenuSubTrigger,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { cn } from '@/lib/utils'
import type { CategoryNode } from '@/api/types'

// 分類最多兩層（depth 0 = 根，depth 1 = 子），子分類不再允許建立子分類
const MAX_PARENT_DEPTH = 0

interface Props {
  node: CategoryNode
  depth: number
  selectedId: string | null
  pendingRenameId: string | null
  isExpanded: (id: string) => boolean
  onToggleExpand: (id: string) => void
  onSelect: (id: string) => void
  onRename: (id: string, name: string) => void
  onAddChild: (parentId: string) => void
  onRemove: (id: string) => void
  onClearPendingRename: () => void
  onExport: (id: string) => void
  onImport: (id: string, file: File, mode: 'append' | 'replace') => void
  onSync: (id: string) => void
}

export function CategoryTreeNode({
  node,
  depth,
  selectedId,
  pendingRenameId,
  isExpanded,
  onToggleExpand,
  onSelect,
  onRename,
  onAddChild,
  onRemove,
  onClearPendingRename,
  onExport,
  onImport,
  onSync,
}: Props) {
  const expanded = isExpanded(node.id)
  const [editing, setEditing] = useState(false)
  const [name, setName] = useState(node.name)
  const [menuOpen, setMenuOpen] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  // 用 ref 而非 state 避免 React 非同步更新與 onChange 之間的競態
  const pendingImportMode = useRef<'append' | 'replace'>('append')

  const isSelected = selectedId === node.id
  const hasChildren = node.children.length > 0

  // 新建分類後自動進入 rename 模式（解決：使用者點「新增子目錄」看不出反應而連按）
  useEffect(() => {
    if (pendingRenameId === node.id) {
      setEditing(true)
      onClearPendingRename()
    }
  }, [pendingRenameId, node.id, onClearPendingRename])

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

  // Radix UI submenu 關閉動畫完成前，Chromium 會攔截 user-gesture，
  // 導致系統檔案對話框無法開啟。setTimeout 0 讓動畫完成後再觸發。
  function triggerFileImport(mode: 'append' | 'replace') {
    pendingImportMode.current = mode
    setTimeout(() => fileInputRef.current?.click(), 0)
  }

  return (
    <li>
      <input
        type="file"
        ref={fileInputRef}
        accept=".xlsx"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0]
          if (file) {
            onImport(node.id, file, pendingImportMode.current)
            e.target.value = ''
          }
        }}
      />
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
            if (hasChildren) onToggleExpand(node.id)
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

        <DropdownMenu open={menuOpen} onOpenChange={setMenuOpen}>
          <DropdownMenuTrigger asChild>
            <button
              type="button"
              onClick={(e) => e.stopPropagation()}
              className="opacity-0 group-hover:opacity-100 p-0.5 rounded hover:bg-white transition-colors"
              aria-label="更多操作"
            >
              <MoreHorizontal className="w-3.5 h-3.5" strokeWidth={1.5} />
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="min-w-[11rem] border-border-strong shadow-md">
            <DropdownMenuItem onClick={() => setEditing(true)}>
              <Pencil className="w-3.5 h-3.5 mr-2" strokeWidth={1.5} /> 重新命名
            </DropdownMenuItem>
            {depth <= MAX_PARENT_DEPTH && (
              <DropdownMenuItem onClick={() => onAddChild(node.id)}>
                <Plus className="w-3.5 h-3.5 mr-2" strokeWidth={1.5} /> 新增子分類
              </DropdownMenuItem>
            )}
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={() => onExport(node.id)}>
              <Download className="w-3.5 h-3.5 mr-2" strokeWidth={1.5} /> 匯出 FAQ
            </DropdownMenuItem>
            <DropdownMenuSub>
              <DropdownMenuSubTrigger>
                <Upload className="w-3.5 h-3.5 mr-2" strokeWidth={1.5} /> 匯入 FAQ
              </DropdownMenuSubTrigger>
              <DropdownMenuSubContent>
                <DropdownMenuItem onClick={() => triggerFileImport('append')}>
                  新增匯入（保留現有資料）
                </DropdownMenuItem>
                <DropdownMenuItem
                  className="text-amber-600 focus:text-amber-600"
                  onClick={() => triggerFileImport('replace')}
                >
                  覆蓋匯入（先刪除全部）
                </DropdownMenuItem>
              </DropdownMenuSubContent>
            </DropdownMenuSub>
            <DropdownMenuItem onClick={() => onSync(node.id)}>
              <RefreshCw className="w-3.5 h-3.5 mr-2" strokeWidth={1.5} /> 同步至向量庫
            </DropdownMenuItem>
            <DropdownMenuSeparator />
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
              pendingRenameId={pendingRenameId}
              isExpanded={isExpanded}
              onToggleExpand={onToggleExpand}
              onSelect={onSelect}
              onRename={onRename}
              onAddChild={onAddChild}
              onRemove={onRemove}
              onClearPendingRename={onClearPendingRename}
              onExport={onExport}
              onImport={onImport}
              onSync={onSync}
            />
          ))}
        </ul>
      )}
    </li>
  )
}
