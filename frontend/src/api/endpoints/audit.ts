import { apiClient } from '../client'
import { unwrap } from '../request'
import type { AuditLogEntry } from '../types'
import type { PaginationParams, Paginated } from './_helpers'

export interface AuditListParams extends PaginationParams {
  action?: string
  performed_by?: string
  date_from?: string
  date_to?: string
  item_id?: string
}

export type AuditLogList = Paginated<AuditLogEntry>

export async function listAuditLogs(agentId: string, params: AuditListParams = {}): Promise<AuditLogList> {
  return unwrap(apiClient.get(`/api/v1/agents/${agentId}/audit-logs`, { params }))
}
