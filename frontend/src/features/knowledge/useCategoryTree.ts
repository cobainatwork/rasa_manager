import { useState, useEffect, useCallback } from 'react'
import * as api from '@/api/endpoints/categories'
import { buildCategoryTree } from '@/lib/categories'
import { extractErrorMessage } from '@/api/client'
import { toast } from 'sonner'
import type { CategoryNode } from '@/api/types'

export interface UseCategoryTreeResult {
  tree: CategoryNode[]
  flat: CategoryNode[]
  loading: boolean
  selectedId: string | null
  select: (id: string | null) => void
  reload: () => void
  rename: (id: string, name: string) => Promise<void>
  addChild: (parentId: string | null) => Promise<void>
  remove: (id: string) => Promise<void>
}

export function useCategoryTree(agentId: string | undefined): UseCategoryTreeResult {
  const [flat, setFlat] = useState<CategoryNode[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedId, setSelectedId] = useState<string | null>(null)

  const reload = useCallback(() => {
    if (!agentId) return
    setLoading(true)
    api.listCategories(agentId)
      .then(setFlat)
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
    try {
      await api.createCategory(agentId, { name: '未命名分類', parent_id: parentId })
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

  return { tree, flat, loading, selectedId, select: setSelectedId, reload, rename, addChild, remove }
}
