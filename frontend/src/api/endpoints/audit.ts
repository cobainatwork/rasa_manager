import { apiClient } from '../client'
import type { AuditLogList } from '../types'

export interface AuditListParams {
  page?: number
  per_page?: number
  action?: string
  performed_by?: string
  date_from?: string
  date_to?: string
  item_id?: string
}

export async function listAuditLogs(agentId: string, params: AuditListParams = {}): Promise<AuditLogList> {
  const resp = await apiClient.get(`/api/v1/agents/${agentId}/audit-logs`, { params })
  return resp.data.data as AuditLogList
}
