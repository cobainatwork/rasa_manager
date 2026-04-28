import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { apiClient, extractErrorMessage } from '@/api/client'
import { useToastStore } from '@/store/useToastStore'
import { useDialogStore } from '@/store/useDialogStore'
import type { CategoryNode } from '@/api/types'

export function Categories() {
  const { id: agentId } = useParams<{ id: string }>()
  const [tree, setTree] = useState<CategoryNode[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [expanded, setExpanded] = useState<Set<string>>(new Set())
  const { addToast } = useToastStore()
  const { showConfirm, showPrompt } = useDialogStore()

  const reload = () => {
    if (!agentId) return
    setLoading(true)
    apiClient
      .get(`/api/v1/agents/${agentId}/categories`)
      .then((resp) => setTree(resp.data?.data ?? []))
      .catch((err) => setError(extractErrorMessage(err)))
      .finally(() => setLoading(false))
  }

  useEffect(reload, [agentId])

  const toggle = (id: string) => {
    setExpanded((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const handleAdd = async (parentId: string | null) => {
    const name = await showPrompt('請輸入分類名稱')
    if (!name) return
    try {
      await apiClient.post(`/api/v1/agents/${agentId}/categories`, {
        name,
        parent_id: parentId,
        sort_order: 0,
      })
      reload()
    } catch (err) {
      addToast(extractErrorMessage(err), 'error')
    }
  }

  const handleRename = async (cat: CategoryNode) => {
    const name = await showPrompt('新名稱', cat.name)
    if (!name || name === cat.name) return
    try {
      await apiClient.patch(`/api/v1/agents/${agentId}/categories/${cat.id}`, { name })
      reload()
    } catch (err) {
      addToast(extractErrorMessage(err), 'error')
    }
  }

  const handleDelete = async (cat: CategoryNode) => {
    const confirmed = await showConfirm(`確定刪除「${cat.name}」？子分類也將一併刪除。`)
    if (!confirmed) return
    try {
      await apiClient.delete(`/api/v1/agents/${agentId}/categories/${cat.id}`)
      reload()
    } catch (err) {
      addToast(extractErrorMessage(err), 'error')
    }
  }

  return (
    <div className="p-8">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">分類管理</h1>
        <button onClick={() => handleAdd(null)} className="btn-primary">
          新增根分類
        </button>
      </div>

      {loading && <p className="text-slate-500">載入中...</p>}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-md p-3 mb-4">
          {error}
        </div>
      )}

      <div className="card p-4">
        {tree.length === 0 && !loading && (
          <p className="text-slate-500 text-sm">尚無分類，請新增根分類。</p>
        )}
        {tree.map((node) => (
          <TreeNode
            key={node.id}
            node={node}
            depth={0}
            expanded={expanded}
            onToggle={toggle}
            onAdd={handleAdd}
            onRename={handleRename}
            onDelete={handleDelete}
          />
        ))}
      </div>
    </div>
  )
}

interface TreeNodeProps {
  node: CategoryNode
  depth: number
  expanded: Set<string>
  onToggle: (id: string) => void
  onAdd: (parentId: string | null) => void
  onRename: (cat: CategoryNode) => void
  onDelete: (cat: CategoryNode) => void
}

function TreeNode({ node, depth, expanded, onToggle, onAdd, onRename, onDelete }: TreeNodeProps) {
  const hasChildren = node.children.length > 0
  const isOpen = expanded.has(node.id)

  return (
    <div>
      <div
        className="flex items-center gap-2 py-1.5 hover:bg-slate-50 rounded px-2"
        style={{ paddingLeft: `${depth * 20 + 8}px` }}
      >
        {hasChildren ? (
          <button onClick={() => onToggle(node.id)} className="text-slate-500 w-4">
            {isOpen ? '▼' : '▶'}
          </button>
        ) : (
          <span className="w-4" />
        )}
        <span className="flex-1 text-sm font-medium">{node.name}</span>
        <div className="flex gap-1 text-xs opacity-0 hover:opacity-100 group-hover:opacity-100">
          <button onClick={() => onAdd(node.id)} className="text-blue-600 hover:underline">
            +子分類
          </button>
          <button onClick={() => onRename(node)} className="text-slate-600 hover:underline">
            改名
          </button>
          <button onClick={() => onDelete(node)} className="text-red-600 hover:underline">
            刪除
          </button>
        </div>
      </div>
      {hasChildren && isOpen && (
        <div>
          {node.children.map((child) => (
            <TreeNode
              key={child.id}
              node={child}
              depth={depth + 1}
              expanded={expanded}
              onToggle={onToggle}
              onAdd={onAdd}
              onRename={onRename}
              onDelete={onDelete}
            />
          ))}
        </div>
      )}
    </div>
  )
}
