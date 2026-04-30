import { apiClient } from '../client'
import type { Faq, FaqListResponse, FaqHistory } from '../types'

export interface FaqListParams {
  page?: number
  per_page?: number
  status?: string
  category_id?: string
  q?: string
  tag?: string
}

export async function listFaqs(agentId: string, params: FaqListParams = {}): Promise<FaqListResponse> {
  const resp = await apiClient.get(`/api/v1/agents/${agentId}/faqs`, { params })
  return resp.data.data as FaqListResponse
}

export async function getFaq(agentId: string, faqId: string): Promise<Faq> {
  const resp = await apiClient.get(`/api/v1/agents/${agentId}/faqs/${faqId}`)
  return resp.data.data as Faq
}

export async function createFaq(
  agentId: string,
  payload: { category_id: string; question: string; answer: string; tags: string[] }
): Promise<Faq> {
  const resp = await apiClient.post(`/api/v1/agents/${agentId}/faqs`, payload)
  return resp.data.data as Faq
}

export async function updateFaq(
  agentId: string,
  faqId: string,
  payload: Partial<Pick<Faq, 'question' | 'answer' | 'category_id' | 'tags'>>
): Promise<Faq> {
  const resp = await apiClient.patch(`/api/v1/agents/${agentId}/faqs/${faqId}`, payload)
  return resp.data.data as Faq
}

export async function deleteFaq(agentId: string, faqId: string): Promise<void> {
  await apiClient.delete(`/api/v1/agents/${agentId}/faqs/${faqId}`)
}

export async function acquireLock(agentId: string, faqId: string): Promise<void> {
  await apiClient.post(`/api/v1/agents/${agentId}/faqs/${faqId}/lock`)
}
export async function refreshLock(agentId: string, faqId: string): Promise<void> {
  await apiClient.put(`/api/v1/agents/${agentId}/faqs/${faqId}/lock`)
}
export async function releaseLock(agentId: string, faqId: string): Promise<void> {
  await apiClient.delete(`/api/v1/agents/${agentId}/faqs/${faqId}/lock`)
}

export async function submit(agentId: string, faqId: string): Promise<Faq> {
  const resp = await apiClient.post(`/api/v1/agents/${agentId}/faqs/${faqId}/submit`)
  return resp.data.data as Faq
}
export async function approve(agentId: string, faqId: string): Promise<Faq> {
  const resp = await apiClient.post(`/api/v1/agents/${agentId}/faqs/${faqId}/approve`)
  return resp.data.data as Faq
}
export async function reject(agentId: string, faqId: string, reason: string): Promise<Faq> {
  const resp = await apiClient.post(`/api/v1/agents/${agentId}/faqs/${faqId}/reject`, { reason })
  return resp.data.data as Faq
}
export async function unapprove(agentId: string, faqId: string): Promise<Faq> {
  const resp = await apiClient.post(`/api/v1/agents/${agentId}/faqs/${faqId}/unapprove`)
  return resp.data.data as Faq
}

export async function getHistory(agentId: string, faqId: string): Promise<FaqHistory[]> {
  const resp = await apiClient.get(`/api/v1/agents/${agentId}/faqs/${faqId}/history`)
  return resp.data.data ?? []
}
export async function rollback(agentId: string, faqId: string, versionId: string): Promise<Faq> {
  const resp = await apiClient.post(`/api/v1/agents/${agentId}/faqs/${faqId}/rollback`, { version_id: versionId })
  return resp.data.data as Faq
}
