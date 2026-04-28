import { useEffect, useState, useCallback } from 'react'
import { useParams } from 'react-router-dom'
import { apiClient, extractErrorMessage } from '@/api/client'
import { formatDate, ACTION_LABELS } from '@/lib/utils'
import type { AuditLogList } from '@/api/types'

export function AuditLog() {
  const { id: agentId } = useParams<{ id: string }>()
  const [list, setList] = useState<AuditLogList | null>(null)
  const [actionFilter, setActionFilter] = useState('')
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(() => {
    if (!agentId) return
    setLoading(true)
    const params: Record<string, string | number> = { page, per_page: 50 }
    if (actionFilter) params.action = actionFilter
    apiClient
      .get(`/api/v1/agents/${agentId}/audit-logs`, { params })
      .then((resp) => setList(resp.data?.data ?? null))
      .catch((err) => setError(extractErrorMessage(err)))
      .finally(() => setLoading(false))
  }, [agentId, page, actionFilter])

  useEffect(load, [load])

  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold mb-6">軌跡追蹤</h1>

      <div className="card p-4 mb-4">
        <select
          value={actionFilter}
          onChange={(e) => { setActionFilter(e.target.value); setPage(1) }}
          className="input max-w-[200px]"
        >
          <option value="">全部操作</option>
          <option value="create">建立</option>
          <option value="update">修改</option>
          <option value="delete">刪除</option>
          <option value="approved">核准</option>
          <option value="rejected">退回</option>
          <option value="rollback">版本還原</option>
        </select>
      </div>

      {loading && <p className="text-slate-500">載入中...</p>}
      {error && <div className="bg-red-50 border border-red-200 text-red-700 p-3 rounded">{error}</div>}

      {list && (
        <div className="card overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-100 border-b">
              <tr>
                <th className="text-left px-4 py-2 font-medium w-40">時間</th>
                <th className="text-left px-4 py-2 font-medium w-24">操作</th>
                <th className="text-left px-4 py-2 font-medium w-32">執行者</th>
                <th className="text-left px-4 py-2 font-medium">FAQ ID</th>
                <th className="text-left px-4 py-2 font-medium">變更內容</th>
              </tr>
            </thead>
            <tbody>
              {list.items.map((log) => (
                <tr key={log.id} className="border-b last:border-b-0">
                  <td className="px-4 py-2 text-slate-500 text-xs">{formatDate(log.created_at)}</td>
                  <td className="px-4 py-2">{ACTION_LABELS[log.action] || log.action}</td>
                  <td className="px-4 py-2">{log.performed_by_username || '-'}</td>
                  <td className="px-4 py-2 text-xs text-slate-500">
                    {log.item_id ? log.item_id.slice(0, 8) + '...' : '-'}
                  </td>
                  <td className="px-4 py-2 text-xs">
                    {log.diff ? (
                      <details>
                        <summary className="cursor-pointer text-blue-600">查看 diff</summary>
                        <pre className="bg-slate-50 p-2 mt-1 text-xs overflow-auto max-h-40">
{JSON.stringify(log.diff, null, 2)}
                        </pre>
                      </details>
                    ) : (
                      <span className="text-slate-400">-</span>
                    )}
                  </td>
                </tr>
              ))}
              {list.items.length === 0 && (
                <tr>
                  <td colSpan={5} className="text-center text-slate-400 py-8">無資料</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {list && list.total > 50 && (
        <div className="flex justify-between items-center mt-4 text-sm">
          <span className="text-slate-500">
            第 {page} 頁 / 共 {Math.ceil(list.total / 50)} 頁
          </span>
          <div className="flex gap-2">
            <button disabled={page <= 1} onClick={() => setPage((p) => p - 1)} className="btn-secondary">上一頁</button>
            <button disabled={page * 50 >= list.total} onClick={() => setPage((p) => p + 1)} className="btn-secondary">下一頁</button>
          </div>
        </div>
      )}
    </div>
  )
}
