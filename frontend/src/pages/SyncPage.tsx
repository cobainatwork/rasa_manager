import { useEffect, useState, useCallback } from 'react'
import { useParams } from 'react-router-dom'
import { apiClient, extractErrorMessage } from '@/api/client'
import { formatDate } from '@/lib/utils'
import { SYNC_POLL_INTERVAL_MS } from '@/lib/constants'
import type { SyncLog } from '@/api/types'

export function SyncPage() {
  const { id: agentId } = useParams<{ id: string }>()
  const [activeLog, setActiveLog] = useState<SyncLog | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [triggering, setTriggering] = useState(false)

  const trigger = async () => {
    if (!agentId) return
    setError(null)
    setTriggering(true)
    try {
      const resp = await apiClient.post(`/api/v1/agents/${agentId}/sync`)
      const data = resp.data?.data
      if (data?.sync_log_id) {
        // 立即查一次取得初始狀態
        const detail = await apiClient.get(`/api/v1/sync/tasks/${data.sync_log_id}`)
        setActiveLog(detail.data?.data ?? null)
      }
    } catch (err) {
      setError(extractErrorMessage(err))
    } finally {
      setTriggering(false)
    }
  }

  // 輪詢
  const poll = useCallback(async () => {
    if (!activeLog || activeLog.status === 'completed' || activeLog.status === 'failed') return
    try {
      const resp = await apiClient.get(`/api/v1/sync/tasks/${activeLog.id}`)
      setActiveLog(resp.data?.data ?? null)
    } catch {
      // ignore
    }
  }, [activeLog])

  useEffect(() => {
    if (!activeLog) return
    if (activeLog.status === 'completed' || activeLog.status === 'failed') return
    const timer = window.setInterval(poll, SYNC_POLL_INTERVAL_MS)
    return () => window.clearInterval(timer)
  }, [activeLog, poll])

  return (
    <div className="p-8 max-w-4xl">
      <h1 className="text-2xl font-bold mb-6">一鍵同步</h1>

      <div className="card p-6 mb-6">
        <p className="text-sm text-slate-600 mb-4">
          觸發一鍵同步將取出所有狀態為「已核准」與「已同步」的 FAQ 項目，
          匯出至 Agent 設定的 <code className="bg-slate-100 px-1">txt_output_path</code> 並執行 ingestion script。
        </p>
        <button onClick={trigger} disabled={triggering} className="btn-primary">
          {triggering ? '觸發中...' : '立即觸發同步'}
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-md p-3 mb-4">
          {error}
        </div>
      )}

      {activeLog && (
        <div className="card p-6">
          <h2 className="font-bold mb-3">當前同步任務</h2>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <span className="text-slate-500">狀態：</span>
              <StatusBadge status={activeLog.status} />
            </div>
            <div>
              <span className="text-slate-500">處理項目：</span>
              {activeLog.items_count}
            </div>
            <div>
              <span className="text-slate-500">開始時間：</span>
              {formatDate(activeLog.started_at)}
            </div>
            <div>
              <span className="text-slate-500">完成時間：</span>
              {formatDate(activeLog.finished_at)}
            </div>
            {activeLog.duration_sec != null && (
              <div>
                <span className="text-slate-500">耗時：</span>
                {activeLog.duration_sec} 秒
              </div>
            )}
            {activeLog.output_file && (
              <div className="col-span-2">
                <span className="text-slate-500">輸出檔：</span>
                <code className="bg-slate-100 px-1 text-xs">{activeLog.output_file}</code>
              </div>
            )}
          </div>

          {activeLog.stdout && (
            <div className="mt-4">
              <p className="text-sm font-medium mb-1">標準輸出</p>
              <pre className="bg-slate-900 text-slate-100 text-xs p-3 rounded overflow-auto max-h-60">
{activeLog.stdout}
              </pre>
            </div>
          )}
          {activeLog.stderr && (
            <div className="mt-4">
              <p className="text-sm font-medium mb-1 text-red-700">錯誤輸出</p>
              <pre className="bg-red-50 text-red-900 text-xs p-3 rounded overflow-auto max-h-60">
{activeLog.stderr}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function StatusBadge({ status }: { status: SyncLog['status'] }) {
  const labels: Record<SyncLog['status'], { text: string; cls: string }> = {
    pending: { text: '等待中', cls: 'bg-slate-100 text-slate-700' },
    running: { text: '執行中', cls: 'bg-blue-100 text-blue-800 animate-pulse' },
    completed: { text: '完成', cls: 'bg-green-100 text-green-800' },
    failed: { text: '失敗', cls: 'bg-red-100 text-red-800' },
  }
  const info = labels[status]
  return <span className={`badge ${info.cls}`}>{info.text}</span>
}
