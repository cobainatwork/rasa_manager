import { apiClient } from '../client'
import type { User } from '../types'

export async function listUsers(): Promise<User[]> {
  const resp = await apiClient.get('/api/v1/users')
  return resp.data.data ?? []
}

export async function createUser(payload: { username: string; password: string }): Promise<User> {
  const resp = await apiClient.post('/api/v1/users', payload)
  return resp.data.data as User
}

export async function updateUser(userId: string, payload: { is_active?: boolean }): Promise<User> {
  const resp = await apiClient.patch(`/api/v1/users/${userId}`, payload)
  return resp.data.data as User
}

export async function deleteUser(userId: string): Promise<void> {
  await apiClient.delete(`/api/v1/users/${userId}`)
}

export async function resetPassword(userId: string, newPassword: string): Promise<void> {
  await apiClient.post(`/api/v1/users/${userId}/reset-password`, { new_password: newPassword })
}

export async function assignRole(
  userId: string,
  agentId: string,
  role: 'editor' | 'reviewer'
): Promise<void> {
  await apiClient.put(`/api/v1/users/${userId}/agents/${agentId}/role`, { role })
}

export async function removeRole(userId: string, agentId: string): Promise<void> {
  await apiClient.delete(`/api/v1/users/${userId}/agents/${agentId}/role`)
}
