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
  exportCategory: (id: string) => Promise<void>
  importCategory: (id: string, file: File, mode: 'append' | 'replace') => Promise<void>
  syncCategory: (id: string) => Promise<void>
}

export function useCategoryTree(
  agentId: string | undefined,
  onImportDone?: (mode: 'append' | 'replace') => void,
): UseCategoryTreeResult {
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

  async function exportCategory(id: string) {
    if (!agentId) return
    try {
      const blob = await api.exportCategoryFaqs(agentId, id)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'category_export.xlsx'
      a.click()
      URL.revokeObjectURL(url)
    } catch (err) { toast.error(extractErrorMessage(err)) }
  }

  async function importCategory(id: string, file: File, mode: 'append' | 'replace') {
    if (!agentId) return
    try {
      const result = await api.importCategoryFaqs(agentId, id, file, mode)
      const modeLabel = mode === 'replace' ? '覆蓋' : '新增'
      toast.success(`匯入完成（${modeLabel}模式）：新增 ${result.imported} 筆，跳過 ${result.skipped} 筆`)
      if (result.errors.length > 0) {
        const rows = result.errors.map((e) => e.row).join('、')
        toast.warning(`${result.errors.length} 列匯入失敗（第 ${rows} 列）`)
      }
      reload()
      onImportDone?.(mode)
    } catch (err) { toast.error(extractErrorMessage(err)) }
  }

  async function syncCategory(id: string) {
    if (!agentId) return
    try {
      await api.syncCategory(agentId, id)
      toast.success('分類同步已觸發，背景執行中')
    } catch (err) { toast.error(`同步失敗：${extractErrorMessage(err)}`) }
  }

  return {
    tree, loading, selectedId, pendingRenameId,
    select: setSelectedId, reload, rename, addChild, remove,
    clearPendingRename, exportCategory, importCategory, syncCategory,
  }
}
