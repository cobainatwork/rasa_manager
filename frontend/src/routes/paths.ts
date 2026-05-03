// N4：集中管理路由路徑常數，避免在多個檔案散落字串。
// 動態路徑（含 :id）以函式形式提供，呼叫端傳入 agentId 取得實際 URL。

export const ROUTE_PATHS = {
  login: '/login',
  agents: '/agents',
  adminUsers: '/admin/users',

  // Agent 內頁（需傳入 agentId）
  agentRoot: (agentId: string) => `/agents/${agentId}`,
  dashboard: (agentId: string) => `/agents/${agentId}/dashboard`,
  knowledge: (agentId: string) => `/agents/${agentId}/knowledge`,
  sync: (agentId: string) => `/agents/${agentId}/sync`,
  importExport: (agentId: string) => `/agents/${agentId}/import-export`,
  testChat: (agentId: string) => `/agents/${agentId}/test-chat`,
  audit: (agentId: string) => `/agents/${agentId}/audit`,
  settings: (agentId: string) => `/agents/${agentId}/settings`,
} as const

// Sidebar 用的子路徑（相對 /agents/:id/）
export const AGENT_SUBPATHS = {
  dashboard: 'dashboard',
  knowledge: 'knowledge',
  sync: 'sync',
  importExport: 'import-export',
  testChat: 'test-chat',
  audit: 'audit',
  settings: 'settings',
} as const
