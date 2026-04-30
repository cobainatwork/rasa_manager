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

  // FAQs
  http.get('/api/v1/agents/:id/faqs', () => ok({
    items: [], total: 0, page: 1, per_page: 20,
  })),

  // Audit logs
  http.get('/api/v1/agents/:id/audit-logs', () => ok({
    items: [], total: 0, page: 1, per_page: 20,
  })),
]
