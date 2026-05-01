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
