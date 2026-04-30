import { useEffect, useState, useCallback } from 'react'
import { listFaqs } from '@/api/endpoints/faqs'
import { useAuthStore } from '@/store/useAuthStore'
import type { Faq } from '@/api/types'

export function usePendingFaqs(agentId: string | undefined) {
  const [items, setItems] = useState<Faq[]>([])
  const [loading, setLoading] = useState(true)
  const isSuper = useAuthStore((s) => s.user?.is_superadmin ?? false)

  const reload = useCallback(() => {
    if (!agentId) return
    setLoading(true)
    // Reviewer / Superadmin 看 pending；Editor 看 draft
    const status = isSuper ? 'pending' : 'pending'
    listFaqs(agentId, { status, per_page: 5 })
      .then((resp) => setItems(resp.items))
      .catch(() => setItems([]))
      .finally(() => setLoading(false))
  }, [agentId, isSuper])

  useEffect(() => { reload() }, [reload])
  return { items, loading, reload }
}
