import { useState, useEffect, useCallback } from 'react'
import * as api from '@/api/endpoints/categories'
import { extractErrorMessage } from '@/api/client'
import { toast } from 'sonner'
import type { CategoryNode } from '@/api/types'

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
  const [tree, setTree] = useState<CategoryNode[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [pendingRenameId, setPendingRenameId] = useState<string | null>(null)

  const reload = useCallback(() => {
    if (!agentId) return
    setLoading(true)
    api.listCategories(agentId)
      .then((nested) => setTree(nested))
      .catch((err) => toast.error(extractErrorMessage(err)))
      .finally(() => setLoading(false))
  }, [agentId])

  useEffect(() => { reload() }, [reload])

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
