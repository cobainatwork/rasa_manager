import { apiClient } from '../client'
import { unwrap } from '../request'
import type { User } from '../types'

export async function listUsers(): Promise<User[]> {
  return unwrap(apiClient.get('/api/v1/users'), [])
}

export async function createUser(payload: { username: string; password: string }): Promise<User> {
  return unwrap(apiClient.post('/api/v1/users', payload))
}

export async function updateUser(userId: string, payload: { is_active?: boolean }): Promise<User> {
  return unwrap(apiClient.patch(`/api/v1/users/${userId}`, payload))
}

export async function deleteUser(userId: string): Promise<void> {
  await apiClient.delete(`/api/v1/users/${userId}`)
}

export async function resetPassword(userId: string, newPassword: string): Promise<void> {
  await apiClient.patch(`/api/v1/users/${userId}/reset-password`, { new_password: newPassword })
}

export async function assignRole(
  userId: string,
  agentId: string,
  role: 'editor' | 'reviewer'
): Promise<void> {
  await apiClient.post(`/api/v1/agents/${agentId}/roles`, { user_id: userId, role })
}

export async function removeRole(userId: string, agentId: string): Promise<void> {
  await apiClient.delete(`/api/v1/agents/${agentId}/roles/${userId}`)
}
