import { listAgents } from '@/api/endpoints/agents'
import type { Agent } from '@/api/types'
import { useApiResource } from '@/hooks/useApiResource'

export interface UseAgentListResult {
  agents: Agent[]
  loading: boolean
  error: string | null
  reload: () => void
}

export function useAgentList(): UseAgentListResult {
  const { data, loading, error, reload } = useApiResource<Agent[]>(
    () => listAgents(),
    [],
    { initialLoading: true },
  )
  return { agents: data ?? [], loading, error, reload }
}
