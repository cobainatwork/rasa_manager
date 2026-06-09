import { listAuditLogs } from '@/api/endpoints/audit'
import type { AuditLogList } from '@/api/types'
import { useApiResource } from '@/hooks/useApiResource'

const PER_PAGE = 50

export function useAuditLog(agentId: string | undefined, page: number) {
  const { data, loading } = useApiResource<AuditLogList | null>(
    () => (agentId ? listAuditLogs(agentId, { page, per_page: PER_PAGE }) : Promise.resolve(null)),
    [agentId, page],
    {
      initialLoading: true,
      fallback: null,
      skip: !agentId,
    },
  )

  return { data, loading, perPage: PER_PAGE }
}
