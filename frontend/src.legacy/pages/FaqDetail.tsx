import { useEffect, useRef, useState, useCallback } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { apiClient, extractErrorMessage } from '@/api/client'
import { useAuthStore } from '@/store/useAuthStore'
import { useToastStore } from '@/store/useToastStore'
import { useDialogStore } from '@/store/useDialogStore'
import { STATUS_LABELS, formatDate, ACTION_LABELS } from '@/lib/utils'
import { LOCK_HEARTBEAT_INTERVAL_MS } from '@/lib/constants'
import type { Faq, FaqHistory, FaqStatus } from '@/api/types'

export function FaqDetail() {
  const { id: agentId, faq_id } = useParams<{ id: string; faq_id: string }>()
  const navigate = useNavigate()
  const { user } = useAuthStore()

  const [faq, setFaq] = useState<Faq | null>(null)
  const [histories, setHistories] = useState<FaqHistory[]>([])
  const [editing, setEditing] = useState(false)
  const [question, setQuestion] = useState('')
  const [answer, setAnswer] = useState('')
  const [tagsStr, setTagsStr] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [userRole, setUserRole] = useState<string | null>(null)
  const heartbeatRef = useRef<number | null>(null)
  const { addToast } = useToastStore()
  const { showConfirm, showPrompt } = useDialogStore()

  const load = useCallback(async () => {
    if (!agentId || !faq_id) return
    setLoading(true)
    try {
      const [faqResp, histResp, roleResp] = await Promise.all([
        apiClient.get(`/api/v1/agents/${agentId}/faqs/${faq_id}`),
        apiClient.get(`/api/v1/agents/${agentId}/faqs/${faq_id}/histories`),
        apiClient.get(`/api/v1/agents/${agentId}/my-role`),
      ])
      setUserRole(roleResp.data?.data?.role ?? null)
      const f: Faq = faqResp.data?.data
      setFaq(f)
      setQuestion(f.question)
      setAnswer(f.answer)
      setTagsStr((f.tags || []).join(', '))
      setHistories(histResp.data?.data ?? [])
    } catch (err) {
      setError(extractErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }, [agentId, faq_id])

  useEffect(() => { load() }, [load])

  // 元件卸載時釋放鎖
  useEffect(() => {
    return () => {
      if (heartbeatRef.current) window.clearInterval(heartbeatRef.current)
      if (editing && agentId && faq_id) {
        apiClient.delete(`/api/v1/agents/${agentId}/faqs/${faq_id}/lock`).catch(() => {})
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const startEditing = async () => {
    if (!agentId || !faq_id) return
    try {
      await apiClient.post(`/api/v1/agents/${agentId}/faqs/${faq_id}/lock`)
      setEditing(true)
      // 啟動心跳
      heartbeatRef.current = window.setInterval(() => {
        apiClient.put(`/api/v1/agents/${agentId}/faqs/${faq_id}/lock`).catch(() => {})
      }, LOCK_HEARTBEAT_INTERVAL_MS)
    } catch (err) {
      addToast(extractErrorMessage(err), 'error')
    }
  }

  const cancelEditing = async () => {
    if (heartbeatRef.current) window.clearInterval(heartbeatRef.current)
    heartbeatRef.current = null
    if (agentId && faq_id) {
      await apiClient.delete(`/api/v1/agents/${agentId}/faqs/${faq_id}/lock`).catch(() => {})
    }
    setEditing(false)
    if (faq) {
      setQuestion(faq.question)
      setAnswer(faq.answer)
      setTagsStr((faq.tags || []).join(', '))
    }
  }

  const saveEdit = async () => {
    if (!agentId || !faq_id) return
    try {
      const tags = tagsStr.split(',').map((s) => s.trim()).filter(Boolean)
      await apiClient.patch(`/api/v1/agents/${agentId}/faqs/${faq_id}`, {
        question, answer, tags,
      })
      if (heartbeatRef.current) window.clearInterval(heartbeatRef.current)
      heartbeatRef.current = null
      await apiClient.delete(`/api/v1/agents/${agentId}/faqs/${faq_id}/lock`).catch(() => {})
      setEditing(false)
      load()
    } catch (err) {
      addToast(extractErrorMessage(err), 'error')
    }
  }

  const changeStatus = async (status: FaqStatus, reason?: string) => {
    if (!agentId || !faq_id) return
    try {
      await apiClient.patch(`/api/v1/agents/${agentId}/faqs/${faq_id}/status`, {
        status, reason: reason || null,
      })
      load()
    } catch (err) {
      addToast(extractErrorMessage(err), 'error')
    }
  }

  const handleReject = async () => {
    const reason = await showPrompt('退回理由（必填）')
    if (!reason) return
    changeStatus('rejected', reason)
  }

  const handleRollback = async (version: number) => {
    const confirmed = await showConfirm(`確定回復至版本 v${version}？目前內容將被覆蓋。`)
    if (!confirmed) return
    if (!agentId || !faq_id) return
    try {
      await apiClient.post(`/api/v1/agents/${agentId}/faqs/${faq_id}/rollback`, { version })
      load()
    } catch (err) {
      addToast(extractErrorMessage(err), 'error')
    }
  }

  const handleDelete = async () => {
    const confirmed = await showConfirm('確定刪除此 FAQ？')
    if (!confirmed) return
    if (!agentId || !faq_id) return
    try {
      await apiClient.delete(`/api/v1/agents/${agentId}/faqs/${faq_id}`)
      navigate(`/agents/${agentId}/faqs`)
    } catch (err) {
      addToast(extractErrorMessage(err), 'error')
    }
  }

  if (loading) return <div className="p-8 text-slate-500">載入中...</div>
  if (error) return <div className="p-8 text-red-600">{error}</div>
  if (!faq) return <div className="p-8 text-slate-500">FAQ 不存在</div>

  const isLockedByOther = faq.locked_by && faq.locked_by !== user?.id
  const canApprove = user?.is_superadmin || userRole === 'reviewer'

  return (
    <div className="p-8 max-w-5xl">
      <button
        onClick={() => navigate(`/agents/${agentId}/faqs`)}
        className="text-sm text-blue-600 hover:underline mb-4"
      >
        ← 返回 FAQ 清單
      </button>

      <div className="flex items-center gap-3 mb-6">
        <h1 className="text-2xl font-bold">FAQ 詳細</h1>
        <span className={`badge-${faq.status}`}>{STATUS_LABELS[faq.status]}</span>
        <span className="text-sm text-slate-500">v{faq.version}</span>
        {isLockedByOther && (
          <span className="text-amber-700 text-sm">
            🔒 正在被 {faq.locked_by_username} 編輯中
          </span>
        )}
      </div>

      {/* 主內容 */}
      <div className="card p-6 mb-6">
        <div className="mb-4">
          <label className="label">問題</label>
          {editing ? (
            <textarea
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              rows={2}
              className="input"
            />
          ) : (
            <p className="text-slate-800 whitespace-pre-wrap">{faq.question}</p>
          )}
        </div>

        <div className="mb-4">
          <label className="label">答案</label>
          {editing ? (
            <textarea
              value={answer}
              onChange={(e) => setAnswer(e.target.value)}
              rows={6}
              className="input"
            />
          ) : (
            <p className="text-slate-800 whitespace-pre-wrap">{faq.answer}</p>
          )}
        </div>

        <div className="mb-4">
          <label className="label">標籤（逗號分隔）</label>
          {editing ? (
            <input value={tagsStr} onChange={(e) => setTagsStr(e.target.value)} className="input" />
          ) : (
            <div className="flex gap-1 flex-wrap">
              {faq.tags.length === 0 && <span className="text-slate-400 text-sm">-</span>}
              {faq.tags.map((t) => (
                <span key={t} className="badge bg-slate-100 text-slate-700">{t}</span>
              ))}
            </div>
          )}
        </div>

        <div className="text-xs text-slate-500 grid grid-cols-2 gap-2 mt-4 pt-4 border-t">
          <div>建立時間：{formatDate(faq.created_at)}</div>
          <div>最後更新：{formatDate(faq.updated_at)}</div>
        </div>
      </div>

      {/* 操作列 */}
      <div className="flex flex-wrap gap-2 mb-6">
        {!editing && !isLockedByOther && (
          <button onClick={startEditing} className="btn-primary">編輯</button>
        )}
        {editing && (
          <>
            <button onClick={saveEdit} className="btn-primary">儲存</button>
            <button onClick={cancelEditing} className="btn-secondary">取消</button>
          </>
        )}

        {!editing && faq.status === 'draft' && (
          <button onClick={() => changeStatus('pending')} className="btn-secondary">送審</button>
        )}
        {!editing && faq.status === 'pending' && canApprove && (
          <>
            <button onClick={() => changeStatus('approved')} className="btn-primary">核准</button>
            <button onClick={handleReject} className="btn-danger">退回</button>
            <button onClick={() => changeStatus('draft')} className="btn-secondary">撤回</button>
          </>
        )}
        {!editing && faq.status === 'rejected' && (
          <button onClick={() => changeStatus('pending')} className="btn-secondary">重新送審</button>
        )}
        {!editing && (faq.status === 'approved' || faq.status === 'synced') && user?.is_superadmin && (
          <button onClick={() => changeStatus('draft')} className="btn-secondary">降回草稿</button>
        )}
        {!editing && (
          <button onClick={handleDelete} className="btn-ghost text-red-600 ml-auto">刪除</button>
        )}
      </div>

      {/* 版本歷史 */}
      <h2 className="text-lg font-bold mb-3">版本歷史</h2>
      <div className="card divide-y">
        {histories.length === 0 && (
          <p className="p-4 text-sm text-slate-500">尚無歷史紀錄</p>
        )}
        {histories.map((h) => (
          <div key={h.id} className="p-4 text-sm">
            <div className="flex items-center gap-2 mb-1">
              <span className="badge bg-slate-100 text-slate-700">v{h.version}</span>
              <span className="font-medium">{ACTION_LABELS[h.action] || h.action}</span>
              <span className="text-slate-500 text-xs">{formatDate(h.created_at)}</span>
              {h.action_reason && (
                <span className="text-amber-700 text-xs">理由：{h.action_reason}</span>
              )}
              <button
                onClick={() => handleRollback(h.version)}
                className="ml-auto text-blue-600 hover:underline text-xs"
              >
                回復至此版本
              </button>
            </div>
            <p className="text-slate-600 truncate text-xs">Q: {h.question}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
