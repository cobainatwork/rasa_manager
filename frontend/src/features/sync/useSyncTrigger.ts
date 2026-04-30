import { useState, useEffect } from 'react'
import * as api from '@/api/endpoints/sync'
import { extractErrorMessage } from '@/api/client'
import { toast } from 'sonner'
import type { SyncLog } from '@/api/types'

const POLL_INTERVAL = 2000

export function useSyncTrigger(agentId: string | undefined) {
  const [activeLog, setActiveLog] = useState<SyncLog | null>(null)
  const [triggering, setTriggering] = useState(false)

  async function trigger() {
    if (!agentId) return
    setTriggering(true)
    try {
      const { sync_log_id } = await api.triggerSync(agentId)
      const detail = await api.getSyncStatus(sync_log_id)
      setActiveLog(detail)
      toast.success('同步任務已觸發')
    } catch (err) {
      toast.error(extractErrorMessage(err))
    } finally {
      setTriggering(false)
    }
  }

  // 輪詢進行中任務
  useEffect(() => {
    if (!activeLog || activeLog.status === 'completed' || activeLog.status === 'failed') return
    const t = setInterval(async () => {
      try {
        const next = await api.getSyncStatus(activeLog.id)
        setActiveLog(next)
      } catch { /* noop */ }
    }, POLL_INTERVAL)
    return () => clearInterval(t)
  }, [activeLog])

  return { activeLog, triggering, trigger, clearActive: () => setActiveLog(null) }
}
