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

export async function listFaqIds(
  agentId: string,
  params: Omit<FaqListParams, 'page' | 'per_page'> = {},
): Promise<string[]> {
  const resp = await apiClient.get(`/api/v1/agents/${agentId}/faqs/ids`, { params })
  return (resp.data?.data?.ids as string[]) ?? []
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

// 後端統一使用 PATCH /status 處理狀態轉移，避免 URL 字串重複
function patchStatus(agentId: string, faqId: string, body: object): Promise<Faq> {
  return unwrap(apiClient.patch(`/api/v1/agents/${agentId}/faqs/${faqId}/status`, body))
}

export async function submit(agentId: string, faqId: string): Promise<Faq> {
  return patchStatus(agentId, faqId, { status: 'pending' })
}
export async function approve(agentId: string, faqId: string): Promise<Faq> {
  return patchStatus(agentId, faqId, { status: 'approved' })
}
export async function reject(agentId: string, faqId: string, reason: string): Promise<Faq> {
  return patchStatus(agentId, faqId, { status: 'rejected', reason })
}
export async function unapprove(agentId: string, faqId: string): Promise<Faq> {
  return patchStatus(agentId, faqId, { status: 'pending' })
}

export async function getHistory(agentId: string, faqId: string): Promise<FaqHistory[]> {
  return unwrap(apiClient.get(`/api/v1/agents/${agentId}/faqs/${faqId}/histories`), [])
}
export async function rollback(agentId: string, faqId: string, version: number): Promise<Faq> {
  return unwrap(apiClient.post(`/api/v1/agents/${agentId}/faqs/${faqId}/rollback`, { version }))
}

export interface ImportResult {
  imported: number
  skipped: number
  errors: { row: number; reason: string }[]
  new_categories: string[]
}

export async function importFaqs(
  agentId: string,
  file: File,
  mode: 'append' | 'replace' = 'append',
): Promise<ImportResult> {
  const form = new FormData()
  form.append('file', file)
  const resp = await apiClient.post(
    `/api/v1/agents/${agentId}/faqs/import?mode=${mode}`,
    form,
    { headers: { 'Content-Type': 'multipart/form-data' } },
  )
  return resp.data?.data as ImportResult
}
