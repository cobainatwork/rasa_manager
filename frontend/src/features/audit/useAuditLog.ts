import { useEffect, useState } from 'react'
import { listAuditLogs } from '@/api/endpoints/audit'
import type { AuditLogList } from '@/api/types'

const PER_PAGE = 50

export function useAuditLog(agentId: string | undefined, page: number) {
  const [data, setData] = useState<AuditLogList | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!agentId) return
    setLoading(true)
    listAuditLogs(agentId, { page, per_page: PER_PAGE })
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false))
  }, [agentId, page])

  return { data, loading, perPage: PER_PAGE }
}
