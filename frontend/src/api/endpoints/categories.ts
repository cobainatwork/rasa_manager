import { apiClient } from '../client'
import { unwrap } from '../request'
import type { CategoryNode } from '../types'

export async function listCategories(agentId: string): Promise<CategoryNode[]> {
  return unwrap(apiClient.get(`/api/v1/agents/${agentId}/categories`), [])
}

export async function createCategory(
  agentId: string,
  payload: { name: string; parent_id: string | null }
): Promise<CategoryNode> {
  return unwrap(apiClient.post(`/api/v1/agents/${agentId}/categories`, payload))
}

export async function updateCategory(
  agentId: string,
  categoryId: string,
  payload: { name?: string; parent_id?: string | null }
): Promise<CategoryNode> {
  return unwrap(apiClient.patch(`/api/v1/agents/${agentId}/categories/${categoryId}`, payload))
}

export async function deleteCategory(agentId: string, categoryId: string): Promise<void> {
  await apiClient.delete(`/api/v1/agents/${agentId}/categories/${categoryId}`)
}

// ── 分類匯入/匯出 ─────────────────────────────────────────────────────────────

export interface CategoryImportResult {
  imported: number
  skipped: number
  errors: Array<{ row: number; reason: string }>
}

export async function exportCategoryFaqs(
  agentId: string,
  categoryId: string
): Promise<Blob> {
  const res = await apiClient.get(
    `/api/v1/agents/${agentId}/categories/${categoryId}/export`,
    { responseType: 'blob' }
  )
  return res.data as Blob
}

export async function importCategoryFaqs(
  agentId: string,
  categoryId: string,
  file: File,
  mode: 'append' | 'replace' = 'append'
): Promise<CategoryImportResult> {
  const form = new FormData()
  form.append('file', file)
  return unwrap(
    apiClient.post(
      `/api/v1/agents/${agentId}/categories/${categoryId}/import?mode=${mode}`,
      form
    )
  )
}

export interface CategorySyncResult {
  task_id: string | null
  sync_log_id: string
  status: string
}

export async function syncCategory(
  agentId: string,
  categoryId: string
): Promise<CategorySyncResult> {
  return unwrap(
    apiClient.post(`/api/v1/agents/${agentId}/categories/${categoryId}/sync`)
  )
}
