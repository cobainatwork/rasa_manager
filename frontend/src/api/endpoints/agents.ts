import { apiClient } from '../client'
import type { Agent, AgentStats, TestConnectionResult, ValidateScriptResult } from '../types'

export async function listAgents(): Promise<Agent[]> {
  const resp = await apiClient.get('/api/v1/agents')
  return resp.data.data ?? []
}

export async function createAgent(payload: Omit<Agent, 'id' | 'created_at'>): Promise<Agent> {
  const resp = await apiClient.post('/api/v1/agents', payload)
  return resp.data.data as Agent
}

export async function updateAgent(id: string, payload: Partial<Agent>): Promise<Agent> {
  const resp = await apiClient.patch(`/api/v1/agents/${id}`, payload)
  return resp.data.data as Agent
}

export async function deleteAgent(id: string): Promise<void> {
  await apiClient.delete(`/api/v1/agents/${id}`)
}

export async function getAgentStats(id: string): Promise<AgentStats> {
  const resp = await apiClient.get(`/api/v1/agents/${id}/stats`)
  return resp.data.data as AgentStats
}

export async function testConnection(id: string): Promise<TestConnectionResult> {
  const resp = await apiClient.post(`/api/v1/agents/${id}/test-connection`)
  return resp.data.data as TestConnectionResult
}

export async function validateScript(id: string): Promise<ValidateScriptResult> {
  const resp = await apiClient.post(`/api/v1/agents/${id}/validate-script`)
  return resp.data.data as ValidateScriptResult
}
