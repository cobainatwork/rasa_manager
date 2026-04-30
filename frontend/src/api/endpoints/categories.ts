import { apiClient } from '../client'
import type { CategoryNode } from '../types'

export async function listCategories(agentId: string): Promise<CategoryNode[]> {
  const resp = await apiClient.get(`/api/v1/agents/${agentId}/categories`)
  return resp.data.data ?? []
}

export async function createCategory(
  agentId: string,
  payload: { name: string; parent_id: string | null }
): Promise<CategoryNode> {
  const resp = await apiClient.post(`/api/v1/agents/${agentId}/categories`, payload)
  return resp.data.data as CategoryNode
}

export async function updateCategory(
  agentId: string,
  categoryId: string,
  payload: { name?: string; parent_id?: string | null }
): Promise<CategoryNode> {
  const resp = await apiClient.patch(`/api/v1/agents/${agentId}/categories/${categoryId}`, payload)
  return resp.data.data as CategoryNode
}

export async function deleteCategory(agentId: string, categoryId: string): Promise<void> {
  await apiClient.delete(`/api/v1/agents/${agentId}/categories/${categoryId}`)
}
