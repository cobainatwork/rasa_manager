import { listFaqs } from '@/api/endpoints/faqs'
import { useAuthStore } from '@/store/useAuthStore'
import type { Faq, FaqListResponse } from '@/api/types'
import { useApiResource } from '@/hooks/useApiResource'

const EMPTY_RESP: FaqListResponse = { items: [], total: 0, page: 1, per_page: 5 }

export function usePendingFaqs(agentId: string | undefined) {
  const isSuper = useAuthStore((s) => s.user?.is_superadmin ?? false)
  // Reviewer / Superadmin 看 pending；Editor 看 draft（目前皆 pending，保留原邏輯）
  const status = isSuper ? 'pending' : 'pending'

  const { data, loading, error, reload } = useApiResource<FaqListResponse>(
    () => (agentId ? listFaqs(agentId, { status, per_page: 5 }) : Promise.resolve(EMPTY_RESP)),
    [agentId, isSuper],
    {
      initialLoading: true,
      fallback: EMPTY_RESP,
      logError: true,
      logPrefix: '[usePendingFaqs]',
      skip: !agentId,
    },
  )

  const items: Faq[] = data?.items ?? []
  return { items, loading, error, reload }
}
