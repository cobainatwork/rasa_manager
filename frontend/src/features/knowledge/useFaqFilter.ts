import { useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'

export interface FaqFilters {
  status: string
  category_id: string
  q: string
  page: number
}

// ── 純函式 helpers ────────────────────────────────────────────────────────────

/** localStorage key 計算邏輯集中於此 */
function filtersKey(agentId: string) { return `kb_filters_${agentId}` }

/** 從 URLSearchParams 讀取並組合成 FaqFilters 物件 */
function readFilters(params: URLSearchParams): FaqFilters {
  return {
    status: params.get('status') ?? '',
    category_id: params.get('category_id') ?? '',
    q: params.get('q') ?? '',
    page: Number(params.get('page') ?? 1),
  }
}

/** 判斷 filters 是否含任何非預設值，用來決定是否要持久化至 localStorage */
function hasActiveFilters(f: FaqFilters): boolean {
  return !!(f.status || f.category_id || f.q || f.page > 1)
}

/** 將 FaqFilters 物件序列化為 URLSearchParams（僅輸出非預設值） */
function filtersToParams(f: FaqFilters): URLSearchParams {
  const p = new URLSearchParams()
  if (f.status) p.set('status', f.status)
  if (f.category_id) p.set('category_id', f.category_id)
  if (f.q) p.set('q', f.q)
  if (f.page > 1) p.set('page', String(f.page))
  return p
}

// ── Hook ──────────────────────────────────────────────────────────────────────

export function useFaqFilter(agentId?: string) {
  const [params, setParams] = useSearchParams()

  // 掛載或切換 Agent 時，若 URL 無篩選參數，從 localStorage 還原上次的篩選狀態。
  // params / setParams 刻意從依賴陣列省略：此 effect 僅在 agent 切換/掛載時執行一次。
  useEffect(() => {
    if (!agentId) return
    const hasUrlParams = (['status', 'category_id', 'q', 'page'] as const).some(k => params.has(k))
    if (hasUrlParams) return
    const saved = localStorage.getItem(filtersKey(agentId))
    if (!saved) return
    try {
      const restored = filtersToParams(JSON.parse(saved) as FaqFilters)
      if (restored.toString()) setParams(restored, { replace: true })
    } catch { /* ignore localStorage parse errors */ }
  }, [agentId]) // eslint-disable-line react-hooks/exhaustive-deps

  // render 中計算一次，供 effect 與 hook 回傳值共用，避免重複呼叫 readFilters
  const filters = readFilters(params)

  // 每次 URL 篩選參數變更後，同步儲存至 localStorage。
  // WHY 變更偵測：params 每次 navigate 均為新物件，會觸發此 effect；若實際篩選值
  // 未改變（如 replace 同一 URL），不需要重複寫入 localStorage，避免無效 I/O。
  useEffect(() => {
    if (!agentId) return
    const key = filtersKey(agentId)
    const json = hasActiveFilters(filters) ? JSON.stringify(filters) : null
    const stored = localStorage.getItem(key)
    if (json === stored) return
    try {
      if (json) localStorage.setItem(key, json)
      else localStorage.removeItem(key)
    } catch { /* ignore */ }
  }, [params, agentId]) // eslint-disable-line react-hooks/exhaustive-deps

  function setFilter(patch: Partial<FaqFilters>) {
    const merged: FaqFilters = { ...filters, ...patch, page: patch.page ?? 1 }
    // 以現有 params 為基底，保留非 filter keys（如其他 hook 寫入的 URL params）
    const next = new URLSearchParams(params)
    ;(['status', 'category_id', 'q', 'page'] as const).forEach(k => next.delete(k))
    filtersToParams(merged).forEach((v, k) => next.set(k, v))
    setParams(next, { replace: true })
  }

  function clearAll() {
    setParams(new URLSearchParams(), { replace: true })
    if (agentId) try { localStorage.removeItem(filtersKey(agentId)) } catch { /* ignore */ }
  }

  return { filters, setFilter, clearAll }
}
