import { useState, useEffect, useCallback } from 'react'
import * as api from '@/api/endpoints/categories'
import { extractErrorMessage } from '@/api/client'
import { toast } from 'sonner'
import type { CategoryNode } from '@/api/types'
import { downloadBlob } from '@/lib/download'

// ── 純函式 helpers ────────────────────────────────────────────────────────────

function toastError(err: unknown) {
  toast.error(extractErrorMessage(err))
}

/** localStorage key 計算邏輯集中於此，避免散落多處 */
function selectionKey(agentId: string) {
  return `kb_selected_${agentId}`
}

/** 從 localStorage 讀取指定 agent 的上次選取分類 ID */
function readSelection(agentId: string | undefined): string | null {
  if (!agentId) return null
  try { return localStorage.getItem(selectionKey(agentId)) } catch { return null }
}

/** 將選取的分類 ID 寫入 localStorage（id 為 null 時移除） */
function writeSelection(agentId: string, id: string | null) {
  try {
    if (id) localStorage.setItem(selectionKey(agentId), id)
    else localStorage.removeItem(selectionKey(agentId))
  } catch { /* ignore */ }
}

/**
 * 產生含毫秒時間戳 + 4 位亂數的暫用分類名稱。
 * 目的：降低快速雙擊或同秒併發時碰撞 DB 唯一約束（uq_cat_agent_parent_name）的機率。
 * 若仍碰撞，後端回 409，前端 toast.error 顯示友善訊息。
 */
function generateUniqueName() {
  const suffix = `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`
  return `新分類_${suffix}`
}

// ── Hook ──────────────────────────────────────────────────────────────────────

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
  onCategoryRemoved?: (deletedId: string) => void,
): UseCategoryTreeResult {
  const [tree, setTree] = useState<CategoryNode[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedId, setSelectedId] = useState<string | null>(() => readSelection(agentId))
  const [pendingRenameId, setPendingRenameId] = useState<string | null>(null)

  // 切換 agent 時從 localStorage 還原新 agent 的選取狀態
  useEffect(() => {
    setSelectedId(readSelection(agentId))
  }, [agentId])

  function select(id: string | null) {
    setSelectedId(id)
    if (agentId) writeSelection(agentId, id)
  }

  const reload = useCallback(() => {
    if (!agentId) return
    setLoading(true)
    api.listCategories(agentId)
      .then(setTree)
      .catch(toastError)
      .finally(() => setLoading(false))
  }, [agentId])

  useEffect(() => { reload() }, [reload])

  async function rename(id: string, name: string) {
    if (!agentId) return
    try {
      await api.updateCategory(agentId, id, { name })
      reload()
    } catch (err) { toastError(err) }
  }

  async function addChild(parentId: string | null) {
    if (!agentId) return
    try {
      const created = await api.createCategory(agentId, { name: generateUniqueName(), parent_id: parentId })
      setPendingRenameId(created.id)
      reload()
    } catch (err) { toastError(err) }
  }

  async function remove(id: string) {
    if (!agentId) return
    try {
      await api.deleteCategory(agentId, id)
      if (selectedId === id) select(null)
      reload()
      onCategoryRemoved?.(id)
    } catch (err) { toastError(err) }
  }

  function clearPendingRename() { setPendingRenameId(null) }

  async function exportCategory(id: string) {
    if (!agentId) return
    try {
      const { blob, filename } = await api.exportCategoryFaqs(agentId, id)
      downloadBlob(blob, filename)
    } catch (err) { toastError(err) }
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
    } catch (err) { toastError(err) }
  }

  async function syncCategory(id: string) {
    if (!agentId) return
    try {
      await api.syncCategory(agentId, id)
      toast.success('分類同步已觸發，背景執行中')
    } catch (err) { toastError(err) }
  }

  return {
    tree, loading, selectedId, pendingRenameId,
    select, reload, rename, addChild, remove,
    clearPendingRename, exportCategory, importCategory, syncCategory,
  }
}
