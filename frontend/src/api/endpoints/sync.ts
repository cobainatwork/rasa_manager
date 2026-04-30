import { apiClient } from '../client'
import type { SyncLog, SyncLogHistoryItem } from '../types'

export async function triggerSync(agentId: string): Promise<{ task_id: string | null; sync_log_id: string }> {
  const resp = await apiClient.post(`/api/v1/agents/${agentId}/sync`)
  return resp.data.data
}

export async function getSyncStatus(syncLogId: string): Promise<SyncLog> {
  const resp = await apiClient.get(`/api/v1/sync/tasks/${syncLogId}`)
  return resp.data.data as SyncLog
}

export async function getSyncHistory(agentId: string, limit = 20): Promise<SyncLogHistoryItem[]> {
  const resp = await apiClient.get(`/api/v1/agents/${agentId}/sync/history`, { params: { limit } })
  return resp.data.data ?? []
}
