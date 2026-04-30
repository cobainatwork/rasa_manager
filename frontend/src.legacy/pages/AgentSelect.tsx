import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { apiClient, extractErrorMessage } from '@/api/client'
import { useAuthStore } from '@/store/useAuthStore'
import { CreateAgentModal } from './CreateAgentModal'
import type { Agent } from '@/api/types'

export function AgentSelect() {
  const navigate = useNavigate()
  const { user, logout, setCurrentAgent } = useAuthStore()
  const [agents, setAgents] = useState<Agent[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showCreateModal, setShowCreateModal] = useState(false)

  const loadAgents = () => {
    setLoading(true)
    apiClient
      .get('/api/v1/agents')
      .then((resp) => setAgents(resp.data?.data ?? []))
      .catch((err) => setError(extractErrorMessage(err)))
      .finally(() => setLoading(false))
  }

  useEffect(() => { loadAgents() }, [])

  const handleSelectAgent = (agent: Agent) => {
    setCurrentAgent(agent)
    navigate(`/agents/${agent.id}/dashboard`)
  }

  const handleLogout = async () => {
    await logout()
    navigate('/login')
  }

  const handleAgentCreated = () => {
    setShowCreateModal(false)
    loadAgents()
  }

  const isSuperadmin = user?.is_superadmin ?? false

  return (
    <div className="min-h-screen p-8">
      <div className="max-w-5xl mx-auto">
        <PageHeader
          username={user?.username ?? ''}
          isSuperadmin={isSuperadmin}
          onCreateAgent={() => setShowCreateModal(true)}
          onManageUsers={() => navigate('/admin/users')}
          onLogout={handleLogout}
        />

        {loading && <p className="text-slate-500">載入中...</p>}

        {error && <ErrorBanner message={error} />}

        {!loading && agents.length === 0 && (
          <EmptyState
            isSuperadmin={isSuperadmin}
            onCreateAgent={() => setShowCreateModal(true)}
          />
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {agents.map((agent) => (
            <AgentCard key={agent.id} agent={agent} onSelect={handleSelectAgent} />
          ))}
        </div>
      </div>

      {showCreateModal && (
        <CreateAgentModal
          onClose={() => setShowCreateModal(false)}
          onCreated={handleAgentCreated}
        />
      )}
    </div>
  )
}

// ── 子元件 ──────────────────────────────────────────────────────────────────

interface PageHeaderProps {
  username: string
  isSuperadmin: boolean
  onCreateAgent: () => void
  onManageUsers: () => void
  onLogout: () => void
}

function PageHeader({ username, isSuperadmin, onCreateAgent, onManageUsers, onLogout }: PageHeaderProps) {
  return (
    <div className="flex justify-between items-center mb-8">
      <div>
        <h1 className="text-2xl font-bold">選擇 Agent 專案</h1>
        <p className="text-slate-500 text-sm mt-1">
          歡迎，{username}
          {isSuperadmin && (
            <span className="ml-2 badge bg-purple-100 text-purple-800">Superadmin</span>
          )}
        </p>
      </div>
      <div className="flex gap-2">
        {isSuperadmin && (
          <>
            <button onClick={onCreateAgent} className="btn-primary">+ 建立 Agent</button>
            <button onClick={onManageUsers} className="btn-secondary">使用者管理</button>
          </>
        )}
        <button onClick={onLogout} className="btn-ghost">登出</button>
      </div>
    </div>
  )
}

function ErrorBanner({ message }: { message: string }) {
  return (
    <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-md p-3 mb-4">
      {message}
    </div>
  )
}

function EmptyState({ isSuperadmin, onCreateAgent }: { isSuperadmin: boolean; onCreateAgent: () => void }) {
  return (
    <div className="card p-8 text-center text-slate-500">
      <p>目前沒有可存取的 Agent 專案</p>
      {isSuperadmin && (
        <button onClick={onCreateAgent} className="btn-primary mt-4">
          + 建立第一個 Agent
        </button>
      )}
    </div>
  )
}

function AgentCard({ agent, onSelect }: { agent: Agent; onSelect: (a: Agent) => void }) {
  return (
    <button
      onClick={() => onSelect(agent)}
      className="card p-6 text-left hover:shadow-md transition-shadow"
    >
      <h3 className="font-semibold text-lg mb-2">{agent.name}</h3>
      <p className="text-xs text-slate-500 break-all">輸出路徑：{agent.txt_output_path}</p>
      {agent.rasa_rest_url && (
        <p className="text-xs text-slate-500 mt-1 break-all">Rasa URL：{agent.rasa_rest_url}</p>
      )}
    </button>
  )
}
