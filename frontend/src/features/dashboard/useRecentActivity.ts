import { listAuditLogs } from '@/api/endpoints/audit'
import type { AuditLogEntry, AuditLogList } from '@/api/types'
import { useApiResource } from '@/hooks/useApiResource'

const EMPTY: AuditLogList = { items: [], total: 0, page: 1, per_page: 5 }

export function useRecentActivity(agentId: string | undefined) {
  const { data, loading, error } = useApiResource<AuditLogList>(
    () => (agentId ? listAuditLogs(agentId, { per_page: 5 }) : Promise.resolve(EMPTY)),
    [agentId],
    {
      initialLoading: true,
      fallback: EMPTY,
      logError: true,
      logPrefix: '[useRecentActivity]',
      skip: !agentId,
    },
  )
  const items: AuditLogEntry[] = data?.items ?? []
  return { items, loading, error }
}
