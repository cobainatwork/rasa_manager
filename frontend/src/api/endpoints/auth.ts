import { apiClient } from '../client'
import { unwrap } from '../request'
import type { User } from '../types'

export async function login(username: string, password: string): Promise<User> {
  return unwrap(apiClient.post('/api/v1/auth/login', { username, password }))
}

export async function logout(): Promise<void> {
  await apiClient.post('/api/v1/auth/logout')
}

export async function me(): Promise<User> {
  return unwrap(apiClient.get('/api/v1/auth/me'))
}
