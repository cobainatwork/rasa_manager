import * as api from '@/api/endpoints/faqs'
import { extractErrorMessage } from '@/api/client'
import { toast } from 'sonner'
import type { Faq } from '@/api/types'
import { useApiResource } from '@/hooks/useApiResource'

export function useFaqDetail(
  agentId: string | undefined,
  faqId: string | null,
  onUpdated?: () => void,
) {
  const enabled = !!agentId && !!faqId
  // toast 模式：失敗以 toast 顯示而非 error state；invalid 時直接 fallback 為 null
  const { data, loading, reload } = useApiResource<Faq | null>(
    () => (enabled ? api.getFaq(agentId!, faqId!) : Promise.resolve(null)),
    [agentId, faqId],
    {
      initialLoading: false,
      fallback: null,
      skip: !enabled,
      silentError: true,
      onError: (err) => toast.error(extractErrorMessage(err)),
    },
  )

  async function update(patch: Partial<Pick<Faq, 'question' | 'answer' | 'category_id' | 'tags'>>) {
    if (!enabled) return
    await api.updateFaq(agentId!, faqId!, patch)
    reload()
    // 通知父層（KnowledgePage）刷新中間欄列表，確保狀態變更即時反映
    onUpdated?.()
  }

  return { faq: data, loading, reload, update }
}
