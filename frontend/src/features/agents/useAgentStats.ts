import { useEffect, useState } from 'react'
import { getAgentStats } from '@/api/endpoints/agents'
import { extractErrorMessage } from '@/api/client'
import type { AgentStats } from '@/api/types'

export function useAgentStats(agentId: string | undefined) {
  const [stats, setStats] = useState<AgentStats | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!agentId) return
    setLoading(true)
    setError(null)
    getAgentStats(agentId)
      .then(setStats)
      .catch((err) => {
        console.error('[useAgentStats]', err)
        setError(extractErrorMessage(err))
        setStats(null)
      })
      .finally(() => setLoading(false))
  }, [agentId])

  return { stats, loading, error }
}
