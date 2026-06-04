import { useEffect, useState, useCallback } from 'react'
import * as api from '@/api/endpoints/faqs'
import { extractErrorMessage } from '@/api/client'
import { toast } from 'sonner'
import type { Faq } from '@/api/types'

export function useFaqDetail(
  agentId: string | undefined,
  faqId: string | null,
  onUpdated?: () => void,
) {
  const [faq, setFaq] = useState<Faq | null>(null)
  const [loading, setLoading] = useState(false)

  const reload = useCallback(() => {
    if (!agentId || !faqId) { setFaq(null); return }
    setLoading(true)
    api.getFaq(agentId, faqId)
      .then(setFaq)
      .catch((err) => toast.error(extractErrorMessage(err)))
      .finally(() => setLoading(false))
  }, [agentId, faqId])

  useEffect(() => { reload() }, [reload])

  async function update(patch: Partial<Pick<Faq, 'question' | 'answer' | 'category_id' | 'tags'>>) {
    if (!agentId || !faqId) return
    await api.updateFaq(agentId, faqId, patch)
    reload()
    // 通知父層（KnowledgePage）刷新中間欄列表，確保狀態變更即時反映
    onUpdated?.()
  }

  return { faq, loading, reload, update }
}
