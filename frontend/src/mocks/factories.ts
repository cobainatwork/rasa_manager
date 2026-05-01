// I11：mock 共用 factory，避免 handlers 內 inline 巨量物件且維持與 spec 型別一致。
import type { Faq, User, Agent, CategoryNode } from '@/api/types'

export function makeUser(over: Partial<User> = {}): User {
  return {
    id: 'u1',
    username: 'admin',
    is_superadmin: true,
    is_active: true,
    created_at: '2026-01-01T00:00:00Z',
    ...over,
  }
}

export function makeAgent(over: Partial<Agent> = {}): Agent {
  return {
    id: 'a1',
    name: 'Demo',
    txt_output_path: '/opt/test',
    rasa_rest_url: null,
    ingest_script_path: null,
    created_at: null,
    ...over,
  }
}

export function makeCategory(over: Partial<CategoryNode> = {}): CategoryNode {
  return {
    id: 'c1',
    name: '預設分類',
    parent_id: null,
    sort_order: 0,
    created_at: null,
    updated_at: null,
    children: [],
    ...over,
  }
}

export function makeFaq(over: Partial<Faq> = {}): Faq {
  return {
    id: 'faq-1',
    agent_id: 'a1',
    category_id: 'c1',
    question: 'Q',
    answer: 'A',
    tags: [],
    status: 'draft',
    version: 1,
    locked_by: null,
    locked_by_username: null,
    locked_at: null,
    created_by: 'u1',
    created_at: null,
    updated_at: null,
    ...over,
  }
}
