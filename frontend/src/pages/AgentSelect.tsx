import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { apiClient, extractErrorMessage } from '@/api/client'
import { useAuthStore } from '@/store/useAuthStore'
import type { Agent } from '@/api/types'

interface CreateAgentForm {
  name: string
  txt_output_path: string
  rasa_rest_url: string
  ingest_script_path: string
}

const EMPTY_FORM: CreateAgentForm = {
  name: '',
  txt_output_path: '',
  rasa_rest_url: '',
  ingest_script_path: '',
}

export function AgentSelect() {
  const navigate = useNavigate()
  const { user, logout, setCurrentAgent } = useAuthStore()
  const [agents, setAgents] = useState<Agent[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // 建立 Agent Modal 狀態
  const [showCreate, setShowCreate] = useState(false)
  const [form, setForm] = useState<CreateAgentForm>(EMPTY_FORM)
  const [creating, setCreating] = useState(false)
  const [createError, setCreateError] = useState<string | null>(null)

  const fetchAgents = () => {
    setLoading(true)
    apiClient
      .get('/api/v1/agents')
      .then((resp) => setAgents(resp.data?.data ?? []))
      .catch((err) => setError(extractErrorMessage(err)))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    fetchAgents()
  }, [])

  const handleSelect = (agent: Agent) => {
    setCurrentAgent(agent)
    navigate(`/agents/${agent.id}/dashboard`)
  }

  const handleLogout = async () => {
    await logout()
    navigate('/login')
  }

  const handleOpenCreate = () => {
    setForm(EMPTY_FORM)
    setCreateError(null)
    setShowCreate(true)
  }

  const handleCreate = async () => {
    if (!form.name.trim() || !form.txt_output_path.trim()) {
      setCreateError('Agent 名稱與輸出路徑為必填欄位。')
      return
    }
    setCreating(true)
    setCreateError(null)
    try {
      await apiClient.post('/api/v1/agents', {
        name: form.name.trim(),
        txt_output_path: form.txt_output_path.trim(),
        rasa_rest_url: form.rasa_rest_url.trim() || null,
        ingest_script_path: form.ingest_script_path.trim() || null,
      })
      setShowCreate(false)
      fetchAgents()
    } catch (err) {
      setCreateError(extractErrorMessage(err))
    } finally {
      setCreating(false)
    }
  }

  return (
    <div className="min-h-screen p-8">
      <div className="max-w-5xl mx-auto">
        {/* ── 頁首 ── */}
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
              <>
                <button onClick={handleOpenCreate} className="btn-primary">
                  + 建立 Agent
                </button>
                <button onClick={() => navigate('/admin/users')} className="btn-secondary">
                  使用者管理
                </button>
              </>
            )}
            <button onClick={handleLogout} className="btn-ghost">登出</button>
          </div>
        </div>

        {/* ── 錯誤訊息 ── */}
        {loading && <p className="text-slate-500">載入中...</p>}
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-md p-3 mb-4">
            {error}
          </div>
        )}

        {/* ── 空狀態 ── */}
        {!loading && agents.length === 0 && (
          <div className="card p-8 text-center text-slate-500">
            <p>目前沒有可存取的 Agent 專案</p>
            {user?.is_superadmin && (
              <button onClick={handleOpenCreate} className="btn-primary mt-4">
                + 建立第一個 Agent
              </button>
            )}
          </div>
        )}

        {/* ── Agent 卡片列表 ── */}
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

      {/* ── 建立 Agent Modal ── */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-lg">
            <div className="p-6 border-b">
              <h2 className="text-xl font-bold">建立新 Agent</h2>
            </div>

            <div className="p-6 space-y-4">
              {createError && (
                <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded p-3">
                  {createError}
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Agent 名稱 <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  className="input w-full"
                  placeholder="例如：客服機器人"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  TXT 輸出路徑 <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  className="input w-full"
                  placeholder="例如：/opt/rasa_docs/agent-001"
                  value={form.txt_output_path}
                  onChange={(e) => setForm({ ...form, txt_output_path: e.target.value })}
                />
                <p className="text-xs text-slate-400 mt-1">容器內部路徑，同步時 .txt 檔案寫入此目錄。</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Rasa Webhook URL <span className="text-slate-400 font-normal">（選填）</span>
                </label>
                <input
                  type="text"
                  className="input w-full"
                  placeholder="例如：http://10.2.66.88:5555/webhooks/myio/webhook"
                  value={form.rasa_rest_url}
                  onChange={(e) => setForm({ ...form, rasa_rest_url: e.target.value })}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Ingestion Script 路徑 <span className="text-slate-400 font-normal">（選填）</span>
                </label>
                <input
                  type="text"
                  className="input w-full"
                  placeholder="例如：/opt/rasa_integration/ingest_kb.py"
                  value={form.ingest_script_path}
                  onChange={(e) => setForm({ ...form, ingest_script_path: e.target.value })}
                />
                <p className="text-xs text-slate-400 mt-1">容器內部路徑，需已透過 volume 掛載。</p>
              </div>
            </div>

            <div className="p-6 border-t flex justify-end gap-3">
              <button
                onClick={() => setShowCreate(false)}
                disabled={creating}
                className="btn-ghost"
              >
                取消
              </button>
              <button
                onClick={handleCreate}
                disabled={creating}
                className="btn-primary disabled:opacity-50"
              >
                {creating ? '建立中...' : '建立 Agent'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
