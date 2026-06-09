import * as api from '@/api/endpoints/sync'
import type { SyncLogHistoryItem } from '@/api/types'
import { useApiResource } from '@/hooks/useApiResource'

export function useSyncHistory(agentId: string | undefined) {
  const { data, loading, error, reload } = useApiResource<SyncLogHistoryItem[]>(
    () => (agentId ? api.getSyncHistory(agentId, 20) : Promise.resolve([])),
    [agentId],
    {
      initialLoading: true,
      fallback: [],
      logError: true,
      logPrefix: '[useSyncHistory]',
      skip: !agentId,
    },
  )
  return { items: data ?? [], loading, error, reload }
}
