import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { apiClient, extractErrorMessage } from '@/api/client'
import { useAuthStore } from '@/store/useAuthStore'
import type { Agent } from '@/api/types'

export function AgentSelect() {
  const navigate = useNavigate()
  const { user, logout, setCurrentAgent } = useAuthStore()
  const [agents, setAgents] = useState<Agent[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    apiClient
      .get('/api/v1/agents')
      .then((resp) => setAgents(resp.data?.data ?? []))
      .catch((err) => setError(extractErrorMessage(err)))
      .finally(() => setLoading(false))
  }, [])

  const handleSelect = (agent: Agent) => {
    setCurrentAgent(agent)
    navigate(`/agents/${agent.id}/dashboard`)
  }

  const handleLogout = async () => {
    await logout()
    navigate('/login')
  }

  return (
    <div className="min-h-screen p-8">
      <div className="max-w-5xl mx-auto">
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-2xl font-bold">選擇 Agent 專案</h1>
            <p className="text-slate-500 text-sm mt-1">
              歡迎，{user?.username}
              {user?.is_superadmin && (
                <span className="ml-2 badge bg-purple-100 text-purple-800">Superadmin</span>
              )}
            </p>
          </div>
          <div className="flex gap-2">
            {user?.is_superadmin && (
              <button onClick={() => navigate('/admin/users')} className="btn-secondary">
                使用者管理
              </button>
            )}
            <button onClick={handleLogout} className="btn-ghost">登出</button>
          </div>
        </div>

        {loading && <p className="text-slate-500">載入中...</p>}
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-md p-3 mb-4">
            {error}
          </div>
        )}

        {!loading && agents.length === 0 && (
          <div className="card p-8 text-center text-slate-500">
            目前沒有可存取的 Agent 專案
            {user?.is_superadmin && (
              <p className="mt-2 text-sm">請以 Superadmin 身分透過 API 建立 Agent。</p>
            )}
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {agents.map((agent) => (
            <button
              key={agent.id}
              onClick={() => handleSelect(agent)}
              className="card p-6 text-left hover:shadow-md transition-shadow"
            >
              <h3 className="font-semibold text-lg mb-2">{agent.name}</h3>
              <p className="text-xs text-slate-500 break-all">
                輸出路徑：{agent.txt_output_path}
              </p>
              {agent.rasa_rest_url && (
                <p className="text-xs text-slate-500 mt-1 break-all">
                  Rasa URL：{agent.rasa_rest_url}
                </p>
              )}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
