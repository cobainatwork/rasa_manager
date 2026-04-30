import { useEffect, useState, useCallback } from 'react'
import * as api from '@/api/endpoints/sync'
import type { SyncLogHistoryItem } from '@/api/types'

export function useSyncHistory(agentId: string | undefined) {
  const [items, setItems] = useState<SyncLogHistoryItem[]>([])
  const [loading, setLoading] = useState(true)

  const reload = useCallback(() => {
    if (!agentId) return
    setLoading(true)
    api.getSyncHistory(agentId, 20)
      .then(setItems)
      .catch(() => setItems([]))
      .finally(() => setLoading(false))
  }, [agentId])

  useEffect(() => { reload() }, [reload])
  return { items, loading, reload }
}
