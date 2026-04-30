import { useSearchParams } from 'react-router-dom'

export interface FaqFilters {
  status: string
  category_id: string
  q: string
  page: number
}

export function useFaqFilter() {
  const [params, setParams] = useSearchParams()
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
  }

  return { filters, setFilter, clearAll }
}
