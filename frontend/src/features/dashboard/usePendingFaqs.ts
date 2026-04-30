import { useEffect, useState, useCallback } from 'react'
import { listFaqs } from '@/api/endpoints/faqs'
import { extractErrorMessage } from '@/api/client'
import { useAuthStore } from '@/store/useAuthStore'
import type { Faq } from '@/api/types'

export function usePendingFaqs(agentId: string | undefined) {
  const [items, setItems] = useState<Faq[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const isSuper = useAuthStore((s) => s.user?.is_superadmin ?? false)

  const reload = useCallback(() => {
    if (!agentId) return
    setLoading(true)
    setError(null)
    // Reviewer / Superadmin 看 pending；Editor 看 draft
    const status = isSuper ? 'pending' : 'pending'
    listFaqs(agentId, { status, per_page: 5 })
      .then((resp) => setItems(resp.items))
      .catch((err) => {
        console.error('[usePendingFaqs]', err)
        setError(extractErrorMessage(err))
        setItems([])
      })
      .finally(() => setLoading(false))
  }, [agentId, isSuper])

  useEffect(() => { reload() }, [reload])
  return { items, loading, error, reload }
}
