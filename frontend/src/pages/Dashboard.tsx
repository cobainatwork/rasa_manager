import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { apiClient, extractErrorMessage } from '@/api/client'
import type { AgentStats } from '@/api/types'

export function Dashboard() {
  const { id } = useParams<{ id: string }>()
  const [stats, setStats] = useState<AgentStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!id) return
    apiClient
      .get(`/api/v1/agents/${id}/stats`)
      .then((resp) => setStats(resp.data?.data ?? null))
      .catch((err) => setError(extractErrorMessage(err)))
      .finally(() => setLoading(false))
  }, [id])

  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold mb-6">儀表板</h1>

      {loading && <p className="text-slate-500">載入中...</p>}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-md p-3 mb-4">
          {error}
        </div>
      )}

      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard label="FAQ 總數" value={stats.total_faqs} color="bg-slate-600" />
          <StatCard label="待審核" value={stats.pending_count} color="bg-yellow-600" />
          <StatCard label="已核准" value={stats.approved_count} color="bg-green-600" />
          <StatCard label="已同步" value={stats.synced_count} color="bg-blue-600" />
          <StatCard label="草稿" value={stats.draft_count} color="bg-slate-400" />
          <StatCard label="已退回" value={stats.rejected_count} color="bg-red-500" />
          <StatCard label="分類數量" value={stats.categories_count} color="bg-purple-500" />
        </div>
      )}
    </div>
  )
}

function StatCard({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className="card p-5">
      <div className={`w-2 h-8 ${color} rounded-full mb-2`} />
      <p className="text-sm text-slate-500">{label}</p>
      <p className="text-3xl font-bold mt-1">{value}</p>
    </div>
  )
}
