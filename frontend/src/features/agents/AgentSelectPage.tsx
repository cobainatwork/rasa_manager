import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus, FolderOpen } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { EmptyState } from '@/components/EmptyState'
import { AppLogo } from '@/components/AppLogo'
import { useAuthStore } from '@/store/useAuthStore'
import { useAgentContext } from '@/store/useAgentContext'
import { ROUTE_PATHS } from '@/routes/paths'
import { useAgentList } from './useAgentList'
import { AgentCard } from './AgentCard'
import { CreateAgentInlinePanel } from './CreateAgentInlinePanel'
import type { Agent } from '@/api/types'

export function AgentSelectPage() {
  const navigate = useNavigate()
  const isSuper = useAuthStore((s) => s.user?.is_superadmin ?? false)
  const username = useAuthStore((s) => s.user?.username)
  const logout = useAuthStore((s) => s.logout)
  const setCurrent = useAgentContext((s) => s.setCurrent)
  const { agents, loading, error, reload } = useAgentList()
  const [showCreate, setShowCreate] = useState(false)

  function handleSelect(agent: Agent) {
    setCurrent(agent)
    navigate(ROUTE_PATHS.dashboard(agent.id))
  }

  async function handleLogout() {
    await logout()
    setCurrent(null)
    navigate(ROUTE_PATHS.login)
  }

  return (
    <div className="min-h-screen bg-canvas">
      <header className="h-11 bg-[#F2F2F7]/80 backdrop-blur-xl border-b border-black/[0.08] flex items-center px-6 justify-between sticky top-0 z-sticky shrink-0">
        <AppLogo />
        <div className="flex items-center gap-2">
          <span className="text-[13px] text-text-secondary">{username}</span>
          {isSuper && <Button variant="outline" size="sm" className="h-7 text-[13px]" onClick={() => navigate(ROUTE_PATHS.adminUsers)}>使用者管理</Button>}
          <Button variant="ghost" size="sm" className="h-7 text-[13px]" onClick={handleLogout}>登出</Button>
        </div>
      </header>

      <main className="p-8 max-w-6xl mx-auto">
        <div className="flex justify-between items-center mb-6">
          <div>
            <h1 className="text-2xl font-bold">選擇 Agent 專案</h1>
            <p className="text-sm text-text-secondary mt-1">選一個 Agent 進入管理介面</p>
          </div>
          {isSuper && !showCreate && (
            <Button onClick={() => setShowCreate(true)}>
              <Plus className="w-4 h-4 mr-1" strokeWidth={1.5} /> 建立 Agent
            </Button>
          )}
        </div>

        {showCreate && (
          <CreateAgentInlinePanel
            onCreated={() => { setShowCreate(false); reload() }}
            onCancel={() => setShowCreate(false)}
          />
        )}

        {error && (
          <Alert variant="destructive" className="mb-4">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {loading && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {[1, 2, 3].map((i) => <Skeleton key={i} className="h-48" />)}
          </div>
        )}

        {!loading && agents.length === 0 && (
          <EmptyState
            icon={FolderOpen}
            title="尚未建立任何 Agent"
            description={isSuper ? '建立第一個 Agent 開始管理您的知識庫' : '請聯絡 Superadmin 建立 Agent'}
            action={isSuper
              ? (
                <Button onClick={() => setShowCreate(true)}>
                  <Plus className="w-4 h-4 mr-1" strokeWidth={1.5} /> 建立 Agent
                </Button>
              )
              : undefined}
          />
        )}

        {!loading && agents.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {agents.map((agent) => (
              <AgentCard key={agent.id} agent={agent} onClick={handleSelect} />
            ))}
          </div>
        )}
      </main>
    </div>
  )
}
