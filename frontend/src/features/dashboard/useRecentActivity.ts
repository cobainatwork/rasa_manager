import { useEffect, useState } from 'react'
import { listAuditLogs } from '@/api/endpoints/audit'
import type { AuditLogEntry } from '@/api/types'

export function useRecentActivity(agentId: string | undefined) {
  const [items, setItems] = useState<AuditLogEntry[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!agentId) return
    setLoading(true)
    listAuditLogs(agentId, { per_page: 5 })
      .then((resp) => setItems(resp.items))
      .catch(() => setItems([]))
      .finally(() => setLoading(false))
  }, [agentId])

  return { items, loading }
}
