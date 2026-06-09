import * as api from '@/api/endpoints/faqs'
import type { FaqHistory } from '@/api/types'
import { useApiResource } from '@/hooks/useApiResource'
import { runWithToast } from '@/lib/runWithToast'

export function useFaqHistory(agentId: string | undefined, faqId: string | null) {
  const enabled = !!agentId && !!faqId
  const { data, loading, reload } = useApiResource<FaqHistory[]>(
    () => (enabled ? api.getHistory(agentId!, faqId!) : Promise.resolve([])),
    [agentId, faqId],
    {
      initialLoading: false,
      fallback: [],
      skip: !enabled,
      silentError: true,
    },
  )

  async function rollback(version: number) {
    if (!enabled) return
    await runWithToast(
      () => api.rollback(agentId!, faqId!, version),
      { success: '已還原', onSuccess: () => reload() },
    )
  }

  return { history: data ?? [], loading, reload, rollback }
}
