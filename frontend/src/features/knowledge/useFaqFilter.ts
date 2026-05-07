import { useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'

export interface FaqFilters {
  status: string
  category_id: string
  q: string
  page: number
}

// localStorage 鍵：以 agentId 隔離，儲存上次的篩選狀態
function filtersKey(agentId: string) { return `kb_filters_${agentId}` }

export function useFaqFilter(agentId?: string) {
  const [params, setParams] = useSearchParams()

  // 掛載或切換 Agent 時，若 URL 無篩選參數，從 localStorage 還原上次的篩選狀態
  // params / setParams 刻意從依賴陣列省略：此 effect 僅在 agent 切換/掛載時執行一次
  useEffect(() => {
    if (!agentId) return
    const hasUrlParams = (['status', 'category_id', 'q', 'page'] as const).some(k => params.has(k))
    if (hasUrlParams) return
    const saved = localStorage.getItem(filtersKey(agentId))
    if (!saved) return
    try {
      const restored = JSON.parse(saved) as Partial<FaqFilters>
      const next = new URLSearchParams()
      if (restored.status) next.set('status', restored.status)
      if (restored.category_id) next.set('category_id', restored.category_id)
      if (restored.q) next.set('q', restored.q)
      if (restored.page && restored.page > 1) next.set('page', String(restored.page))
      if (next.toString()) setParams(next, { replace: true })
    } catch { /* ignore localStorage parse errors */ }
  }, [agentId]) // eslint-disable-line react-hooks/exhaustive-deps

  // 每次 URL 篩選參數變更後，同步儲存至 localStorage
  useEffect(() => {
    if (!agentId) return
    const status = params.get('status') ?? ''
    const category_id = params.get('category_id') ?? ''
    const q = params.get('q') ?? ''
    const page = Number(params.get('page') ?? 1)
    if (status || category_id || q || page > 1) {
      const toSave: Partial<FaqFilters> = {}
      if (status) toSave.status = status
      if (category_id) toSave.category_id = category_id
      if (q) toSave.q = q
      if (page > 1) toSave.page = page
      try { localStorage.setItem(filtersKey(agentId), JSON.stringify(toSave)) } catch { /* ignore */ }
    } else {
      try { localStorage.removeItem(filtersKey(agentId)) } catch { /* ignore */ }
    }
  }, [params, agentId])

  const filters: FaqFilters = {
    status: params.get('status') ?? '',
    category_id: params.get('category_id') ?? '',
    q: params.get('q') ?? '',
    page: Number(params.get('page') ?? 1),
  }

  function setFilter(patch: Partial<FaqFilters>) {
    const next = new URLSearchParams(params)
    Object.entries({ ...filters, ...patch, page: patch.page ?? 1 }).forEach(([k, v]) => {
      if (v === '' || v === 0 || v === undefined || v === null) next.delete(k)
      else next.set(k, String(v))
    })
    setParams(next, { replace: true })
  }

  function clearAll() {
    setParams(new URLSearchParams(), { replace: true })
    if (agentId) try { localStorage.removeItem(filtersKey(agentId)) } catch { /* ignore */ }
  }

  return { filters, setFilter, clearAll }
}
