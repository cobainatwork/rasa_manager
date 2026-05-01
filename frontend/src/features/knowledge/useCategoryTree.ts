import { useState, useEffect, useCallback } from 'react'
import * as api from '@/api/endpoints/categories'
import { buildCategoryTree } from '@/lib/categories'
import { extractErrorMessage } from '@/api/client'
import { toast } from 'sonner'
import type { CategoryNode } from '@/api/types'

/**
 * 後端 list_categories 已回傳 nested tree（含 children 陣列）；
 * 此處攤平回 flat 以便 buildCategoryTree 與其他工具函式正確處理。
 */
function flattenNested(nodes: CategoryNode[]): CategoryNode[] {
  const out: CategoryNode[] = []
  function walk(list: CategoryNode[]) {
    for (const n of list) {
      out.push({ ...n, children: [] })
      if (n.children && n.children.length > 0) walk(n.children)
    }
  }
  walk(nodes)
  return out
}

export interface UseCategoryTreeResult {
  tree: CategoryNode[]
  flat: CategoryNode[]
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
  const [flat, setFlat] = useState<CategoryNode[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [pendingRenameId, setPendingRenameId] = useState<string | null>(null)

  const reload = useCallback(() => {
    if (!agentId) return
    setLoading(true)
    api.listCategories(agentId)
      .then((nested) => setFlat(flattenNested(nested)))
      .catch((err) => toast.error(extractErrorMessage(err)))
      .finally(() => setLoading(false))
  }, [agentId])

  useEffect(() => { reload() }, [reload])

  const tree = buildCategoryTree(flat)

  async function rename(id: string, name: string) {
    if (!agentId) return
    try {
      await api.updateCategory(agentId, id, { name })
      reload()
    } catch (err) { toast.error(extractErrorMessage(err)) }
  }

  async function addChild(parentId: string | null) {
    if (!agentId) return
    // 同層級不允許同名（DB 唯一約束）；以時分秒後綴保證每次唯一，不依賴 flat 即時性
    const ts = new Date().toLocaleTimeString('zh-TW', { hour12: false }).replace(/:/g, '')
    const name = `新分類_${ts}`
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
    tree, flat, loading, selectedId, pendingRenameId,
    select: setSelectedId, reload, rename, addChild, remove,
    clearPendingRename,
  }
}
