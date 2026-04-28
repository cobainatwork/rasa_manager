import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { apiClient, extractErrorMessage } from '@/api/client'
import type { Agent } from '@/api/types'

export function AgentSettings() {
  const { id: agentId } = useParams<{ id: string }>()
  const [agent, setAgent] = useState<Agent | null>(null)
  const [name, setName] = useState('')
  const [txtOutputPath, setTxtOutputPath] = useState('')
  const [rasaUrl, setRasaUrl] = useState('')
  const [ingestPath, setIngestPath] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    if (!agentId) return
    apiClient
      .get(`/api/v1/agents/${agentId}`)
      .then((resp) => {
        const a: Agent = resp.data?.data
        setAgent(a)
        setName(a.name)
        setTxtOutputPath(a.txt_output_path)
        setRasaUrl(a.rasa_rest_url || '')
        setIngestPath(a.ingest_script_path || '')
      })
      .catch((err) => setError(extractErrorMessage(err)))
      .finally(() => setLoading(false))
  }, [agentId])

  const save = async () => {
    if (!agentId) return
    setError(null)
    setSaved(false)
    try {
      await apiClient.put(`/api/v1/agents/${agentId}`, {
        name,
        txt_output_path: txtOutputPath,
        rasa_rest_url: rasaUrl || null,
        ingest_script_path: ingestPath || null,
      })
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    } catch (err) {
      setError(extractErrorMessage(err))
    }
  }

  if (loading) return <div className="p-8 text-slate-500">載入中...</div>
  if (!agent) return <div className="p-8 text-red-600">{error}</div>

  return (
    <div className="p-8 max-w-2xl">
      <h1 className="text-2xl font-bold mb-6">Agent 設定</h1>
      <p className="text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded p-3 mb-4">
        僅 Superadmin 可修改。<code className="bg-white px-1">ingest_script_path</code> 為敏感設定，影響 Worker 容器內執行的指令。
      </p>

      <div className="card p-6 space-y-4">
        <div>
          <label className="label">Agent 名稱</label>
          <input value={name} onChange={(e) => setName(e.target.value)} className="input" />
        </div>
        <div>
          <label className="label">.txt 輸出路徑（容器內絕對路徑）</label>
          <input
            value={txtOutputPath}
            onChange={(e) => setTxtOutputPath(e.target.value)}
            placeholder="/opt/rasa_docs/{agent_id}/"
            className="input"
          />
        </div>
        <div>
          <label className="label">Rasa REST URL（用於對話測試）</label>
          <input
            value={rasaUrl}
            onChange={(e) => setRasaUrl(e.target.value)}
            placeholder="http://localhost:5005"
            className="input"
          />
        </div>
        <div>
          <label className="label">Ingest Script 相對路徑（相對於 ./scripts/）</label>
          <input
            value={ingestPath}
            onChange={(e) => setIngestPath(e.target.value)}
            placeholder="customer_service/ingest.py"
            className="input"
          />
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-md p-3">{error}</div>
        )}
        {saved && (
          <div className="bg-green-50 border border-green-200 text-green-700 text-sm rounded-md p-3">
            儲存成功
          </div>
        )}

        <button onClick={save} className="btn-primary">儲存設定</button>
      </div>
    </div>
  )
}
