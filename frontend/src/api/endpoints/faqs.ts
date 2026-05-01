import { apiClient } from '../client'
import { unwrap } from '../request'
import type { Faq, FaqHistory } from '../types'
import type { PaginationParams, Paginated } from './_helpers'

export interface FaqListParams extends PaginationParams {
  status?: string
  category_id?: string
  q?: string
  tag?: string
}

export type FaqListResponse = Paginated<Faq>

export async function listFaqs(agentId: string, params: FaqListParams = {}): Promise<FaqListResponse> {
  return unwrap(apiClient.get(`/api/v1/agents/${agentId}/faqs`, { params }))
}

export async function getFaq(agentId: string, faqId: string): Promise<Faq> {
  return unwrap(apiClient.get(`/api/v1/agents/${agentId}/faqs/${faqId}`))
}

export async function createFaq(
  agentId: string,
  payload: { category_id: string; question: string; answer: string; tags: string[] }
): Promise<Faq> {
  return unwrap(apiClient.post(`/api/v1/agents/${agentId}/faqs`, payload))
}

export async function updateFaq(
  agentId: string,
  faqId: string,
  payload: Partial<Pick<Faq, 'question' | 'answer' | 'category_id' | 'tags'>>
): Promise<Faq> {
  return unwrap(apiClient.patch(`/api/v1/agents/${agentId}/faqs/${faqId}`, payload))
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
  return unwrap(apiClient.post(`/api/v1/agents/${agentId}/faqs/${faqId}/submit`))
}
export async function approve(agentId: string, faqId: string): Promise<Faq> {
  return unwrap(apiClient.post(`/api/v1/agents/${agentId}/faqs/${faqId}/approve`))
}
export async function reject(agentId: string, faqId: string, reason: string): Promise<Faq> {
  return unwrap(apiClient.post(`/api/v1/agents/${agentId}/faqs/${faqId}/reject`, { reason }))
}
export async function unapprove(agentId: string, faqId: string): Promise<Faq> {
  return unwrap(apiClient.post(`/api/v1/agents/${agentId}/faqs/${faqId}/unapprove`))
}

export async function getHistory(agentId: string, faqId: string): Promise<FaqHistory[]> {
  return unwrap(apiClient.get(`/api/v1/agents/${agentId}/faqs/${faqId}/history`), [])
}
export async function rollback(agentId: string, faqId: string, versionId: string): Promise<Faq> {
  return unwrap(apiClient.post(`/api/v1/agents/${agentId}/faqs/${faqId}/rollback`, { version_id: versionId }))
}
