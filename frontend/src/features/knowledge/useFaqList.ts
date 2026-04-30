import { useEffect, useState } from 'react'
import { listFaqs } from '@/api/endpoints/faqs'
import { useDebounce } from '@/hooks/useDebounce'
import { extractErrorMessage } from '@/api/client'
import type { FaqListResponse } from '@/api/types'
import type { FaqFilters } from './useFaqFilter'

const PER_PAGE = 20

export function useFaqList(agentId: string | undefined, filters: FaqFilters) {
  const [data, setData] = useState<FaqListResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const debouncedQ = useDebounce(filters.q, 300)

  useEffect(() => {
    if (!agentId) return
    setLoading(true)
    setError(null)
    listFaqs(agentId, {
      page: filters.page,
      per_page: PER_PAGE,
      status: filters.status || undefined,
      category_id: filters.category_id || undefined,
      q: debouncedQ || undefined,
    })
      .then(setData)
      .catch((err) => setError(extractErrorMessage(err)))
      .finally(() => setLoading(false))
  }, [agentId, filters.page, filters.status, filters.category_id, debouncedQ])

  const totalPages = data ? Math.max(1, Math.ceil(data.total / PER_PAGE)) : 1
  return { data, loading, error, totalPages, perPage: PER_PAGE }
}
