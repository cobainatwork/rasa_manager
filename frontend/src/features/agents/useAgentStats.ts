import { getAgentStats } from '@/api/endpoints/agents'
import type { AgentStats } from '@/api/types'
import { useApiResource } from '@/hooks/useApiResource'

export function useAgentStats(agentId: string | undefined) {
  const { data, loading, error } = useApiResource<AgentStats | null>(
    () => (agentId ? getAgentStats(agentId) : Promise.resolve(null)),
    [agentId],
    {
      initialLoading: false,
      fallback: null,
      logError: true,
      logPrefix: '[useAgentStats]',
      skip: !agentId,
    },
  )

  return { stats: data, loading, error }
}
