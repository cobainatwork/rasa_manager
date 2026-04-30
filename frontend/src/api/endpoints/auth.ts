import { apiClient } from '../client'
import type { User } from '../types'

export async function login(username: string, password: string): Promise<User> {
  const resp = await apiClient.post('/api/v1/auth/login', { username, password })
  return resp.data.data as User
}

export async function logout(): Promise<void> {
  await apiClient.post('/api/v1/auth/logout')
}

export async function me(): Promise<User> {
  const resp = await apiClient.get('/api/v1/auth/me')
  return resp.data.data as User
}
