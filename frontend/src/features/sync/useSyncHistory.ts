import { useEffect, useState, useCallback } from 'react'
import * as api from '@/api/endpoints/sync'
import { extractErrorMessage } from '@/api/client'
import type { SyncLogHistoryItem } from '@/api/types'

export function useSyncHistory(agentId: string | undefined) {
  const [items, setItems] = useState<SyncLogHistoryItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const reload = useCallback(() => {
    if (!agentId) return
    setLoading(true)
    setError(null)
    api.getSyncHistory(agentId, 20)
      .then(setItems)
      .catch((err) => {
        console.error('[useSyncHistory]', err)
        setError(extractErrorMessage(err))
        setItems([])
      })
      .finally(() => setLoading(false))
  }, [agentId])

  useEffect(() => { reload() }, [reload])
  return { items, loading, error, reload }
}
