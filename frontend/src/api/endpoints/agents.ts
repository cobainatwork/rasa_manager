import { apiClient } from '../client'
import { unwrap } from '../request'
import type { Agent, AgentStats, TestConnectionResult, ValidateScriptResult } from '../types'

export async function listAgents(): Promise<Agent[]> {
  return unwrap(apiClient.get('/api/v1/agents'), [])
}

export async function createAgent(payload: Omit<Agent, 'id' | 'created_at'>): Promise<Agent> {
  return unwrap(apiClient.post('/api/v1/agents', payload))
}

export async function updateAgent(id: string, payload: Partial<Agent>): Promise<Agent> {
  return unwrap(apiClient.patch(`/api/v1/agents/${id}`, payload))
}

export async function deleteAgent(id: string): Promise<void> {
  await apiClient.delete(`/api/v1/agents/${id}`)
}

export async function getAgentStats(id: string): Promise<AgentStats> {
  return unwrap(apiClient.get(`/api/v1/agents/${id}/stats`))
}

export async function testConnection(id: string): Promise<TestConnectionResult> {
  return unwrap(apiClient.post(`/api/v1/agents/${id}/test-connection`))
}

export async function validateScript(id: string): Promise<ValidateScriptResult> {
  return unwrap(apiClient.post(`/api/v1/agents/${id}/validate-script`))
}
