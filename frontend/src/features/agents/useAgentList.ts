import { useEffect, useState, useCallback } from 'react'
import { listAgents } from '@/api/endpoints/agents'
import { extractErrorMessage } from '@/api/client'
import type { Agent } from '@/api/types'

export interface UseAgentListResult {
  agents: Agent[]
  loading: boolean
  error: string | null
  reload: () => void
}

export function useAgentList(): UseAgentListResult {
  const [agents, setAgents] = useState<Agent[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const reload = useCallback(() => {
    setLoading(true)
    setError(null)
    listAgents()
      .then(setAgents)
      .catch((err) => setError(extractErrorMessage(err)))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { reload() }, [reload])
  return { agents, loading, error, reload }
}
