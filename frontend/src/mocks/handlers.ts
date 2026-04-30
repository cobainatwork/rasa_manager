import { http, HttpResponse } from 'msw'

const ok = <T>(data: T) => HttpResponse.json({ success: true, data })

export const handlers = [
  // Auth
  http.post('/api/v1/auth/login', () => ok({
    id: 'u1', username: 'admin', is_superadmin: true, is_active: true, created_at: '2026-01-01T00:00:00Z',
  })),
  http.get('/api/v1/auth/me', () => ok({
    id: 'u1', username: 'admin', is_superadmin: true, is_active: true, created_at: '2026-01-01T00:00:00Z',
  })),
  http.post('/api/v1/auth/logout', () => HttpResponse.json({ success: true })),

  // Agents
  http.get('/api/v1/agents', () => ok([
    { id: 'a1', name: 'Demo', txt_output_path: '/opt/sap', rasa_rest_url: null, ingest_script_path: null, created_at: null },
  ])),
  http.post('/api/v1/agents', () => ok({
    id: 'a-new', name: 'New Agent', txt_output_path: '/opt/test', rasa_rest_url: null, ingest_script_path: null, created_at: null,
  })),
  http.patch('/api/v1/agents/:id', () => ok({
    id: 'a1', name: 'Updated', txt_output_path: '/opt/test', rasa_rest_url: null, ingest_script_path: null, created_at: null,
  })),
  http.delete('/api/v1/agents/:id', () => HttpResponse.json({ success: true })),
  http.post('/api/v1/agents/:id/test-connection', () => ok({ ok: true, status_code: 200, latency_ms: 42, error: null })),
  http.post('/api/v1/agents/:id/validate-script', () => ok({ exists: true, executable: true, size_bytes: 1024 })),

  // Stats（避免測試噪音）
  http.get('/api/v1/agents/:id/stats', () => ok({
    total_faqs: 0, pending_count: 0, approved_count: 0, synced_count: 0,
    draft_count: 0, rejected_count: 0, categories_count: 0,
  })),

  // Categories
  http.get('/api/v1/agents/:id/categories', () => ok([])),
  http.post('/api/v1/agents/:id/categories', () => ok({
    id: 'c1', name: '新分類', parent_id: null, sort_order: 0, created_at: null, updated_at: null, children: [],
  })),
  http.patch('/api/v1/agents/:id/categories/:cid', () => ok({
    id: 'c1', name: '更新後', parent_id: null, sort_order: 0, created_at: null, updated_at: null, children: [],
  })),
  http.delete('/api/v1/agents/:id/categories/:cid', () => HttpResponse.json({ success: true })),

  // FAQs
  http.get('/api/v1/agents/:id/faqs', () => ok({
    items: [], total: 0, page: 1, per_page: 20,
  })),
  http.get('/api/v1/agents/:id/faqs/:faqId', ({ params }) => ok({
    id: params.faqId, agent_id: params.id, category_id: 'c1', question: 'Q', answer: 'A',
    tags: [], status: 'draft', version: 1, locked_by: null, locked_by_username: null,
    locked_at: null, created_by: 'u1', created_at: null, updated_at: null,
  })),
  http.post('/api/v1/agents/:id/faqs', () => ok({
    id: 'new-faq', agent_id: 'a1', category_id: 'c1', question: 'Q', answer: 'A',
    tags: [], status: 'draft', version: 1, locked_by: null, locked_by_username: null,
    locked_at: null, created_by: 'u1', created_at: null, updated_at: null,
  })),
  http.patch('/api/v1/agents/:id/faqs/:faqId', () => ok({
    id: 'a-faq', agent_id: 'a1', category_id: 'c1', question: 'Q', answer: 'A',
    tags: [], status: 'draft', version: 2, locked_by: null, locked_by_username: null,
    locked_at: null, created_by: 'u1', created_at: null, updated_at: null,
  })),
  http.delete('/api/v1/agents/:id/faqs/:faqId', () => HttpResponse.json({ success: true })),
  http.post('/api/v1/agents/:id/faqs/:faqId/submit', () => ok({})),
  http.post('/api/v1/agents/:id/faqs/:faqId/approve', () => ok({})),
  http.post('/api/v1/agents/:id/faqs/:faqId/reject', () => ok({})),
  http.post('/api/v1/agents/:id/faqs/:faqId/unapprove', () => ok({})),
  http.get('/api/v1/agents/:id/faqs/:faqId/history', () => ok([])),
  http.post('/api/v1/agents/:id/faqs/:faqId/rollback', () => ok({})),

  // Audit logs
  http.get('/api/v1/agents/:id/audit-logs', () => ok({
    items: [], total: 0, page: 1, per_page: 20,
  })),

  // Sync
  http.post('/api/v1/agents/:id/sync', () => ok({ task_id: 't1', sync_log_id: 's1', status: 'pending' })),
  http.get('/api/v1/sync/tasks/:syncLogId', ({ params }) => ok({
    id: params.syncLogId, agent_id: 'a1', triggered_by: null, celery_task_id: 't1',
    status: 'completed', items_count: 0, output_file: null, stdout: null, stderr: null,
    started_at: null, finished_at: null, duration_sec: null, created_at: null,
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
  http.get('/api/v1/users', () => ok([
    { id: 'u1', username: 'admin', is_superadmin: true, is_active: true, created_at: '2026-01-01T00:00:00Z' },
  ])),
  http.post('/api/v1/users', () => ok({
    id: 'u-new', username: 'new', is_superadmin: false, is_active: true, created_at: null,
  })),
  http.patch('/api/v1/users/:userId', () => ok({
    id: 'u1', username: 'admin', is_superadmin: false, is_active: false, created_at: null,
  })),
  http.delete('/api/v1/users/:userId', () => HttpResponse.json({ success: true })),
  http.post('/api/v1/users/:userId/reset-password', () => HttpResponse.json({ success: true })),
  http.put('/api/v1/users/:userId/agents/:agentId/role', () => HttpResponse.json({ success: true })),
  http.delete('/api/v1/users/:userId/agents/:agentId/role', () => HttpResponse.json({ success: true })),
]
