import { useCallback, useEffect, useState } from 'react'

/**
 * 右欄顯示模式。
 * - `detail`：顯示已選取的 FAQ 詳情（需有 selectedFaqId）
 * - `new`：顯示新增 FAQ 表單（臨時態，不持久化）
 * - `empty`：空狀態提示
 */
export type RightPaneMode = 'detail' | 'new' | 'empty'

/**
 * 跨 KnowledgePage / PendingTasksPanel 共用的 localStorage key 規則。
 * 變動格式會破壞 Dashboard → Knowledge 的跳轉自動還原行為。
 */
function selectionKey(agentId: string): string {
  return `kb_selected_faq_${agentId}`
}

/**
 * 安全讀取 localStorage，遇到 SecurityError / QuotaError 一律回 null。
 */
function readSelection(agentId: string | undefined): string | null {
  if (!agentId) return null
  try {
    return localStorage.getItem(selectionKey(agentId)) ?? null
  } catch {
    // 私密瀏覽 / 容量爆滿時 localStorage 會丟例外，靜默回 null
    return null
  }
}

/**
 * 安全寫入 / 清除 localStorage。
 */
function writeSelection(agentId: string, faqId: string | null): void {
  try {
    if (faqId) localStorage.setItem(selectionKey(agentId), faqId)
    else localStorage.removeItem(selectionKey(agentId))
  } catch {
    // 容量爆滿或被瀏覽器限制時靜默忽略；UI 仍保持正確的 in-memory 狀態
  }
}

export interface FaqSelectionPersistence {
  selectedFaqId: string | null
  rightMode: RightPaneMode
  /** 選取一筆 FAQ → 進入 detail 模式並寫入 localStorage */
  selectFaq: (faqId: string) => void
  /** 開啟新增表單 → 清掉選取，rightMode = 'new'（不持久化） */
  openNewForm: () => void
  /** 取消新增（從 new 退回 empty），不動 selectedFaqId（已為 null） */
  cancelNewForm: () => void
  /** 清空選取並關閉右欄（rightMode = 'empty'） */
  clearSelection: () => void
}

/**
 * 封裝 KnowledgePage 右欄的「選取 FAQ」狀態 + localStorage 持久化。
 *
 * 持久化規則：
 * - `detail` 模式：selectedFaqId 寫入 localStorage
 * - `new` / `empty` 模式：清空 localStorage（重新整理回到 empty）
 * - agentId 變化：自動從新 agent 的 localStorage 還原
 */
export function useFaqSelectionPersistence(agentId: string | undefined): FaqSelectionPersistence {
  const [selectedFaqId, setSelectedFaqId] = useState<string | null>(() => readSelection(agentId))
  const [rightMode, setRightMode] = useState<RightPaneMode>(() =>
    readSelection(agentId) ? 'detail' : 'empty',
  )

  // agentId 變動時，從對應 localStorage 重新讀取選取狀態
  useEffect(() => {
    if (!agentId) {
      setSelectedFaqId(null)
      setRightMode('empty')
      return
    }
    const faqId = readSelection(agentId)
    setSelectedFaqId(faqId)
    setRightMode(faqId ? 'detail' : 'empty')
  }, [agentId])

  const selectFaq = useCallback(
    (faqId: string) => {
      setSelectedFaqId(faqId)
      setRightMode('detail')
      if (agentId) writeSelection(agentId, faqId)
    },
    [agentId],
  )

  const openNewForm = useCallback(() => {
    setSelectedFaqId(null)
    setRightMode('new')
    if (agentId) writeSelection(agentId, null)
  }, [agentId])

  const cancelNewForm = useCallback(() => {
    setRightMode('empty')
  }, [])

  const clearSelection = useCallback(() => {
    setSelectedFaqId(null)
    setRightMode('empty')
    if (agentId) writeSelection(agentId, null)
  }, [agentId])

  return { selectedFaqId, rightMode, selectFaq, openNewForm, cancelNewForm, clearSelection }
}
