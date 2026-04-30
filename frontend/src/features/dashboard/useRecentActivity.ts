import { useEffect, useState } from 'react'
import { listAuditLogs } from '@/api/endpoints/audit'
import { extractErrorMessage } from '@/api/client'
import type { AuditLogEntry } from '@/api/types'

export function useRecentActivity(agentId: string | undefined) {
  const [items, setItems] = useState<AuditLogEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!agentId) return
    setLoading(true)
    setError(null)
    listAuditLogs(agentId, { per_page: 5 })
      .then((resp) => setItems(resp.items))
      .catch((err) => {
        console.error('[useRecentActivity]', err)
        setError(extractErrorMessage(err))
        setItems([])
      })
      .finally(() => setLoading(false))
  }, [agentId])

  return { items, loading, error }
}
