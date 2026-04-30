import { useEffect, useState } from 'react'
import { getAgentStats } from '@/api/endpoints/agents'
import type { AgentStats } from '@/api/types'

export function useDashboardStats(agentId: string | undefined) {
  const [stats, setStats] = useState<AgentStats | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!agentId) return
    setLoading(true)
    getAgentStats(agentId)
      .then(setStats)
      .catch(() => setStats(null))
      .finally(() => setLoading(false))
  }, [agentId])

  return { stats, loading }
}
