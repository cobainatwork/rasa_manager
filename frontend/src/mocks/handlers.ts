// 對應 spec §13 端點清單（N12）
// I11：使用 factories.ts 共用 factory，並讓 submit/approve/reject/unapprove/rollback 回傳完整 Faq。
import { http, HttpResponse } from 'msw'
import { makeUser, makeAgent, makeCategory, makeFaq } from './factories'

const ok = <T>(data: T) => HttpResponse.json({ success: true, data })

export const handlers = [
  // Auth
  http.post('/api/v1/auth/login', () => ok(makeUser())),
  http.get('/api/v1/auth/me', () => ok(makeUser())),
  http.post('/api/v1/auth/logout', () => HttpResponse.json({ success: true })),

  // Agents
  http.get('/api/v1/agents', () => ok([makeAgent({ id: 'a1', name: 'Demo', txt_output_path: '/opt/sap' })])),
  http.post('/api/v1/agents', () => ok(makeAgent({ id: 'a-new', name: 'New Agent' }))),
  http.patch('/api/v1/agents/:id', () => ok(makeAgent({ name: 'Updated' }))),
  http.delete('/api/v1/agents/:id', () => HttpResponse.json({ success: true })),
  http.post('/api/v1/agents/:id/test-connection', () => ok({ ok: true, status_code: 200, latency_ms: 42, error: null })),
  http.post('/api/v1/agents/:id/validate-script', () => ok({ exists: true, executable: true, size_bytes: 1024, error: null })),

  // Stats（避免測試噪音）
  http.get('/api/v1/agents/:id/stats', () => ok({
    total_faqs: 0, pending_count: 0, approved_count: 0, synced_count: 0,
    draft_count: 0, rejected_count: 0, categories_count: 0,
  })),

  // Categories
  http.get('/api/v1/agents/:id/categories', () => ok([])),
  http.post('/api/v1/agents/:id/categories', () => ok(makeCategory({ name: '新分類' }))),
  http.patch('/api/v1/agents/:id/categories/:cid', () => ok(makeCategory({ name: '更新後' }))),
  http.delete('/api/v1/agents/:id/categories/:cid', () => HttpResponse.json({ success: true })),
  http.post('/api/v1/agents/:id/categories/:cid/sync', () => ok({ task_id: 't1', sync_log_id: 's1' })),
  http.post('/api/v1/agents/:id/categories/:cid/import', () => ok({
    imported: 0, skipped: 0, errors: [], new_categories: [],
  })),
  http.get('/api/v1/agents/:id/categories/:cid/export', () => new Response(new Blob(), {
    headers: { 'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' },
  })),

  // FAQs
  http.get('/api/v1/agents/:id/faqs', () => ok({ items: [], total: 0, page: 1, per_page: 20 })),
  // 注意：/faqs/ids 必須先於 /faqs/:faqId 註冊，否則會被 :faqId='ids' 貪婪攔截
  http.get('/api/v1/agents/:id/faqs/ids', () => ok([])),
  http.get('/api/v1/agents/:id/faqs/:faqId', ({ params }) =>
    ok(makeFaq({ id: String(params.faqId), agent_id: String(params.id) })),
  ),
  http.post('/api/v1/agents/:id/faqs', () => ok(makeFaq({ id: 'new-faq' }))),
  http.patch('/api/v1/agents/:id/faqs/:faqId', () => ok(makeFaq({ id: 'a-faq', version: 2 }))),
  http.delete('/api/v1/agents/:id/faqs/:faqId', () => HttpResponse.json({ success: true })),
  // FAQ 編輯鎖三動詞
  http.post('/api/v1/agents/:id/faqs/:faqId/lock', () => HttpResponse.json({ success: true })),
  http.put('/api/v1/agents/:id/faqs/:faqId/lock', () => HttpResponse.json({ success: true })),
  http.delete('/api/v1/agents/:id/faqs/:faqId/lock', () => HttpResponse.json({ success: true })),
  // FAQ 狀態轉移統一走 PATCH /status，body { status: 'pending'|'approved'|... }
  // 之前 submit/approve/reject/unapprove 4 個假 endpoint 與 backend 完全不一致，
  // 測試形同虛設（real frontend 走 PATCH /status，這些假 mock 永不被命中）。
  http.patch('/api/v1/agents/:id/faqs/:faqId/status', async ({ request }) => {
    const body = (await request.json()) as { status?: string }
    return ok(makeFaq({ status: (body?.status as 'draft' | 'pending' | 'approved' | 'rejected' | 'synced') ?? 'draft' }))
  }),
  http.get('/api/v1/agents/:id/faqs/:faqId/histories', () => ok([])),
  http.post('/api/v1/agents/:id/faqs/:faqId/rollback', () => ok(makeFaq({ version: 3 }))),

  // Audit logs
  http.get('/api/v1/agents/:id/audit-logs', () => ok({ items: [], total: 0, page: 1, per_page: 20 })),

  // Sync（移除多餘 status，符合 sync.ts TriggerSyncResult 型別）
  http.post('/api/v1/agents/:id/sync', () => ok({ task_id: 't1', sync_log_id: 's1' })),
  http.get('/api/v1/sync/tasks/:syncLogId', ({ params }) => ok({
    id: params.syncLogId, agent_id: 'a1', triggered_by: null, celery_task_id: 't1',
    status: 'completed', items_count: 0, output_file: null, stdout: null, stderr: null,
    started_at: null, finished_at: null, duration_sec: null, created_at: '2026-01-01T00:00:00Z',
  })),
  http.get('/api/v1/agents/:id/sync/history', () => ok([])),

  // Import / Export
  http.post('/api/v1/agents/:id/faqs/import', () => ok({
    imported: 0, skipped: 0, errors: [], new_categories: [],
  })),
  http.get('/api/v1/agents/:id/faqs/export', () => new Response(new Blob(), {
    headers: { 'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' },
  })),

  // Chat test
  http.post('/api/v1/agents/:id/chat/test', () => ok([{ text: '測試回覆' }])),

  // Users
  http.get('/api/v1/users', () => ok([makeUser()])),
  http.post('/api/v1/users', () => ok(makeUser({ id: 'u-new', username: 'new', is_superadmin: false, created_at: '2026-01-01T00:00:00Z' }))),
  http.patch('/api/v1/users/:userId', () => ok(makeUser({ is_superadmin: false, is_active: false, created_at: '2026-01-01T00:00:00Z' }))),
  http.delete('/api/v1/users/:userId', () => HttpResponse.json({ success: true })),
  http.patch('/api/v1/users/:userId/reset-password', () => HttpResponse.json({ success: true })),
  http.post('/api/v1/agents/:agentId/roles', () => HttpResponse.json({ success: true })),
  http.delete('/api/v1/agents/:agentId/roles/:userId', () => HttpResponse.json({ success: true })),
]
