import { useState, useEffect, useCallback } from 'react'
import * as api from '@/api/endpoints/categories'
import { buildCategoryTree } from '@/lib/categories'
import { extractErrorMessage } from '@/api/client'
import { toast } from 'sonner'
import type { CategoryNode } from '@/api/types'

/** 攤平 nested tree 用的內部型別，明示「無子節點」避免與 CategoryNode 混淆 */
interface FlatCategoryRow {
  id: string
  name: string
  parent_id: string | null
  sort_order: number
  created_at: string | null
  updated_at: string | null
}

/**
 * 後端 list_categories 已回傳 nested tree（含 children 陣列）；
 * 此處攤平回扁平列以便 buildCategoryTree 統一從 parent_id 重建關係。
 */
function flattenNested(nodes: CategoryNode[]): FlatCategoryRow[] {
  const out: FlatCategoryRow[] = []
  function walk(list: CategoryNode[]) {
    for (const n of list) {
      out.push({
        id: n.id,
        name: n.name,
        parent_id: n.parent_id,
        sort_order: n.sort_order,
        created_at: n.created_at,
        updated_at: n.updated_at,
      })
      if (n.children && n.children.length > 0) walk(n.children)
    }
  }
  walk(nodes)
  return out
}

export interface UseCategoryTreeResult {
  tree: CategoryNode[]
  loading: boolean
  selectedId: string | null
  pendingRenameId: string | null
  select: (id: string | null) => void
  reload: () => void
  rename: (id: string, name: string) => Promise<void>
  addChild: (parentId: string | null) => Promise<void>
  remove: (id: string) => Promise<void>
  clearPendingRename: () => void
}

export function useCategoryTree(agentId: string | undefined): UseCategoryTreeResult {
  const [rows, setRows] = useState<FlatCategoryRow[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [pendingRenameId, setPendingRenameId] = useState<string | null>(null)

  const reload = useCallback(() => {
    if (!agentId) return
    setLoading(true)
    api.listCategories(agentId)
      .then((nested) => setRows(flattenNested(nested)))
      .catch((err) => toast.error(extractErrorMessage(err)))
      .finally(() => setLoading(false))
  }, [agentId])

  useEffect(() => { reload() }, [reload])

  const tree = buildCategoryTree(rows)

  async function rename(id: string, name: string) {
    if (!agentId) return
    try {
      await api.updateCategory(agentId, id, { name })
      reload()
    } catch (err) { toast.error(extractErrorMessage(err)) }
  }

  async function addChild(parentId: string | null) {
    if (!agentId) return
    // 同層唯一名稱限制（DB 唯一約束 uq_cat_agent_parent_name）：
    // 以毫秒級 timestamp + 4 位亂數，降低快速雙擊或同秒併發碰撞的機率。
    // 若仍碰撞，後端會回 409，前端 toast.error 顯示友善訊息。
    const suffix = `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`
    const name = `新分類_${suffix}`
    try {
      const created = await api.createCategory(agentId, { name, parent_id: parentId })
      setPendingRenameId(created.id)
      reload()
    } catch (err) { toast.error(extractErrorMessage(err)) }
  }

  async function remove(id: string) {
    if (!agentId) return
    try {
      await api.deleteCategory(agentId, id)
      if (selectedId === id) setSelectedId(null)
      reload()
    } catch (err) { toast.error(extractErrorMessage(err)) }
  }

  function clearPendingRename() { setPendingRenameId(null) }

  return {
    tree, loading, selectedId, pendingRenameId,
    select: setSelectedId, reload, rename, addChild, remove,
    clearPendingRename,
  }
}
