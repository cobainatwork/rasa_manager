import { apiClient } from '../client'
import { unwrap } from '../request'
import type { SyncLog, SyncLogHistoryItem } from '../types'

export interface TriggerSyncResult {
  task_id: string | null
  sync_log_id: string
}

export async function triggerSync(agentId: string): Promise<TriggerSyncResult> {
  return unwrap(apiClient.post(`/api/v1/agents/${agentId}/sync`))
}

export async function getSyncStatus(syncLogId: string): Promise<SyncLog> {
  return unwrap(apiClient.get(`/api/v1/sync/tasks/${syncLogId}`))
}

export async function getSyncHistory(agentId: string, limit = 20): Promise<SyncLogHistoryItem[]> {
  return unwrap(apiClient.get(`/api/v1/agents/${agentId}/sync/history`, { params: { limit } }), [])
}
