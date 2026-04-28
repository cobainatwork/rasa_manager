import { useEffect, useState, useCallback } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { apiClient, extractErrorMessage } from '@/api/client'
import { STATUS_LABELS, formatDate } from '@/lib/utils'
import { FAQ_PER_PAGE } from '@/lib/constants'
import { useToastStore } from '@/store/useToastStore'
import { useDialogStore } from '@/store/useDialogStore'
import type { Faq, FaqListResponse, CategoryNode } from '@/api/types'

const STATUS_OPTIONS: Array<{ value: string; label: string }> = [
  { value: '', label: '全部狀態' },
  { value: 'draft', label: '草稿' },
  { value: 'pending', label: '待審核' },
  { value: 'approved', label: '已核准' },
  { value: 'rejected', label: '已退回' },
  { value: 'synced', label: '已同步' },
]

function flattenCategories(nodes: CategoryNode[], prefix = ''): Array<{ id: string; path: string }> {
  const result: Array<{ id: string; path: string }> = []
  for (const n of nodes) {
    const path = prefix ? `${prefix}/${n.name}` : n.name
    result.push({ id: n.id, path })
    if (n.children.length > 0) {
      result.push(...flattenCategories(n.children, path))
    }
  }
  return result
}

export function KnowledgeBase() {
  const { id: agentId } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [list, setList] = useState<FaqListResponse | null>(null)
  const [categories, setCategories] = useState<Array<{ id: string; path: string }>>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const { addToast } = useToastStore()
  const { showPrompt } = useDialogStore()

  const [statusFilter, setStatusFilter] = useState('')
  const [categoryFilter, setCategoryFilter] = useState('')
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const perPage = FAQ_PER_PAGE

  const load = useCallback(() => {
    if (!agentId) return
    setLoading(true)
    const params: Record<string, string | number> = { page, per_page: perPage }
    if (statusFilter) params.status = statusFilter
    if (categoryFilter) params.category_id = categoryFilter
    if (search) params.q = search
    apiClient
      .get(`/api/v1/agents/${agentId}/faqs`, { params })
      .then((resp) => setList(resp.data?.data ?? null))
      .catch((err) => setError(extractErrorMessage(err)))
      .finally(() => setLoading(false))
  }, [agentId, page, perPage, statusFilter, categoryFilter, search])

  useEffect(() => {
    load()
  }, [load])

  useEffect(() => {
    if (!agentId) return
    apiClient
      .get(`/api/v1/agents/${agentId}/categories`)
      .then((resp) => setCategories(flattenCategories(resp.data?.data ?? [])))
      .catch(() => setCategories([]))
  }, [agentId])

  const handleNew = async () => {
    if (categories.length === 0) {
      addToast('請先建立分類', 'info')
      return
    }
    const categoryId = await showPrompt(
      '請選擇分類 ID（複製貼上）：\n' + categories.map((c) => `${c.id} → ${c.path}`).join('\n'),
      categories[0].id
    )
    if (!categoryId) return
    const question = await showPrompt('問題')
    if (!question) return
    const answer = await showPrompt('答案')
    if (!answer) return
    try {
      const resp = await apiClient.post(`/api/v1/agents/${agentId}/faqs`, {
        category_id: categoryId,
        question,
        answer,
        tags: [],
      })
      const faq: Faq = resp.data?.data
      navigate(`/agents/${agentId}/faqs/${faq.id}`)
    } catch (err) {
      addToast(extractErrorMessage(err), 'error')
    }
  }

  return (
    <div className="p-8">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">知識庫 FAQ</h1>
        <button onClick={handleNew} className="btn-primary">新增 FAQ</button>
      </div>

      {/* Filters */}
      <div className="card p-4 mb-4 flex flex-wrap gap-3">
        <select
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value); setPage(1) }}
          className="input max-w-[150px]"
        >
          {STATUS_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>

        <select
          value={categoryFilter}
          onChange={(e) => { setCategoryFilter(e.target.value); setPage(1) }}
          className="input max-w-[200px]"
        >
          <option value="">全部分類</option>
          {categories.map((c) => <option key={c.id} value={c.id}>{c.path}</option>)}
        </select>

        <input
          placeholder="搜尋問題或答案..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && setPage(1)}
          className="input flex-1 min-w-[200px]"
        />
        <button onClick={() => { setPage(1); load() }} className="btn-secondary">搜尋</button>
      </div>

      {loading && <p className="text-slate-500">載入中...</p>}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-md p-3 mb-4">
          {error}
        </div>
      )}

      {list && (
        <>
          <div className="card overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-slate-100 border-b">
                <tr>
                  <th className="text-left px-4 py-2 font-medium">問題</th>
                  <th className="text-left px-4 py-2 font-medium w-24">狀態</th>
                  <th className="text-left px-4 py-2 font-medium w-20">版本</th>
                  <th className="text-left px-4 py-2 font-medium w-40">最後更新</th>
                  <th className="text-left px-4 py-2 font-medium w-32">編輯鎖</th>
                </tr>
              </thead>
              <tbody>
                {list.items.map((faq) => (
                  <tr
                    key={faq.id}
                    onClick={() => navigate(`/agents/${agentId}/faqs/${faq.id}`)}
                    className="border-b last:border-b-0 hover:bg-slate-50 cursor-pointer"
                  >
                    <td className="px-4 py-3 max-w-md truncate">{faq.question}</td>
                    <td className="px-4 py-3">
                      <span className={`badge-${faq.status}`}>{STATUS_LABELS[faq.status]}</span>
                    </td>
                    <td className="px-4 py-3">v{faq.version}</td>
                    <td className="px-4 py-3 text-slate-500">{formatDate(faq.updated_at)}</td>
                    <td className="px-4 py-3 text-xs">
                      {faq.locked_by_username ? (
                        <span className="text-amber-700">{faq.locked_by_username}</span>
                      ) : (
                        <span className="text-slate-400">-</span>
                      )}
                    </td>
                  </tr>
                ))}
                {list.items.length === 0 && (
                  <tr>
                    <td colSpan={5} className="text-center text-slate-500 py-8">
                      無資料
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="flex justify-between items-center mt-4 text-sm">
            <p className="text-slate-500">
              第 {page} 頁 / 共 {Math.max(1, Math.ceil(list.total / perPage))} 頁，總計 {list.total} 筆
            </p>
            <div className="flex gap-2">
              <button
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
                className="btn-secondary"
              >
                上一頁
              </button>
              <button
                disabled={page * perPage >= list.total}
                onClick={() => setPage((p) => p + 1)}
                className="btn-secondary"
              >
                下一頁
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
