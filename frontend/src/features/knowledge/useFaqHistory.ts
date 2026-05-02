import { useEffect, useState, useCallback } from 'react'
import * as api from '@/api/endpoints/faqs'
import { extractErrorMessage } from '@/api/client'
import { toast } from 'sonner'
import type { FaqHistory } from '@/api/types'

export function useFaqHistory(agentId: string | undefined, faqId: string | null) {
  const [history, setHistory] = useState<FaqHistory[]>([])
  const [loading, setLoading] = useState(false)

  const reload = useCallback(() => {
    if (!agentId || !faqId) { setHistory([]); return }
    setLoading(true)
    api.getHistory(agentId, faqId)
      .then(setHistory)
      .catch(() => setHistory([]))
      .finally(() => setLoading(false))
  }, [agentId, faqId])

  useEffect(() => { reload() }, [reload])

  async function rollback(version: number) {
    if (!agentId || !faqId) return
    try {
      await api.rollback(agentId, faqId, version)
      toast.success('已還原')
      reload()
    } catch (err) {
      toast.error(extractErrorMessage(err))
    }
  }

  return { history, loading, reload, rollback }
}
