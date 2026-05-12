// 對應後端 API 回應的 TypeScript 型別定義

export interface ApiSuccess<T> {
  success: true
  data: T
  message?: string
}

export interface ApiError {
  success: false
  error: { code: string; message: string }
}

export interface User {
  id: string
  username: string
  is_superadmin: boolean
  is_active: boolean
  created_at: string
}

export interface Agent {
  id: string
  name: string
  qdrant_collection: string
  txt_output_path: string
  rasa_rest_url: string | null
  ingest_script_path: string | null
  created_at: string | null
}

export interface AgentStats {
  total_faqs: number
  pending_count: number
  approved_count: number
  synced_count: number
  draft_count: number
  rejected_count: number
  categories_count: number
}

export interface CategoryNode {
  id: string
  name: string
  parent_id: string | null
  sort_order: number
  created_at: string | null
  updated_at: string | null
  children: CategoryNode[]
}

export type FaqStatus = 'draft' | 'pending' | 'approved' | 'rejected' | 'synced'

export interface Faq {
  id: string
  agent_id: string
  category_id: string
  question: string
  answer: string
  tags: string[]
  status: FaqStatus
  version: number
  locked_by: string | null
  locked_by_username: string | null
  locked_at: string | null
  created_by: string
  created_at: string | null
  updated_at: string | null
}

export interface FaqListResponse {
  items: Faq[]
  total: number
  page: number
  per_page: number
}

export interface FaqHistory {
  id: string
  item_id: string | null
  version: number
  question: string
  answer: string
  category_id: string | null
  saved_by: string | null
  action: string
  action_reason: string | null
  created_at: string | null
}

export interface SyncLog {
  id: string
  agent_id: string
  triggered_by: string | null
  celery_task_id: string | null
  status: 'pending' | 'running' | 'completed' | 'failed'
  items_count: number
  output_file: string | null
  stdout: string | null
  stderr: string | null
  started_at: string | null
  finished_at: string | null
  duration_sec: number | null
  created_at: string | null
}

export interface AuditLogEntry {
  id: string
  agent_id: string
  item_id: string | null
  action: string
  performed_by: string | null
  performed_by_username: string | null
  diff: Record<string, { before: unknown; after: unknown }> | null
  created_at: string | null
}

export interface AuditLogList {
  items: AuditLogEntry[]
  total: number
  page: number
  per_page: number
}

export interface ChatMessage {
  recipient_id?: string
  text?: string
  image?: string
}

// ── 後端新端點型別（spec §13） ────────────────────────────────────────────

export interface SyncLogHistoryItem {
  id: string
  status: SyncLog['status']
  triggered_by_username: string | null
  started_at: string | null
  finished_at: string | null
  duration_sec: number | null
  items_count: number
  output_file: string | null
  stdout: string | null
  stderr: string | null
}

export interface TestConnectionResult {
  ok: boolean
  status_code: number | null
  latency_ms: number | null
  error: string | null
}

export interface ValidateScriptResult {
  exists: boolean
  executable: boolean
  size_bytes: number
  error: string | null
}
