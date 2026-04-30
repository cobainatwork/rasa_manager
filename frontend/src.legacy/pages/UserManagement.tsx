import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { apiClient, extractErrorMessage } from '@/api/client'
import { formatDate } from '@/lib/utils'
import { useToastStore } from '@/store/useToastStore'
import { useDialogStore } from '@/store/useDialogStore'
import type { User } from '@/api/types'

export function UserManagement() {
  const navigate = useNavigate()
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const { addToast } = useToastStore()
  const { showConfirm, showPrompt } = useDialogStore()

  const load = useCallback(() => {
    setLoading(true)
    apiClient
      .get('/api/v1/users')
      .then((resp) => setUsers(resp.data?.data ?? []))
      .catch((err) => setError(extractErrorMessage(err)))
      .finally(() => setLoading(false))
  }, [])

  useEffect(load, [load])

  const handleCreate = async () => {
    const username = await showPrompt('帳號')
    if (!username) return
    const password = await showPrompt('密碼（最少 8 字元，含大小寫與數字）')
    if (!password) return
    const isSuperadmin = await showConfirm('是否為 Superadmin？')
    try {
      await apiClient.post('/api/v1/users', { username, password, is_superadmin: isSuperadmin })
      load()
    } catch (err) {
      addToast(extractErrorMessage(err), 'error')
    }
  }

  const toggleActive = async (u: User) => {
    try {
      await apiClient.patch(`/api/v1/users/${u.id}`, { is_active: !u.is_active })
      load()
    } catch (err) {
      addToast(extractErrorMessage(err), 'error')
    }
  }

  const resetPassword = async (u: User) => {
    const pwd = await showPrompt(`重設 ${u.username} 的密碼`)
    if (!pwd) return
    try {
      await apiClient.patch(`/api/v1/users/${u.id}/reset-password`, { new_password: pwd })
      addToast('密碼重設成功', 'success')
    } catch (err) {
      addToast(extractErrorMessage(err), 'error')
    }
  }

  return (
    <div className="p-8 max-w-5xl">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">使用者管理</h1>
        <div className="flex gap-2">
          <button onClick={() => navigate('/agents')} className="btn-ghost">返回</button>
          <button onClick={handleCreate} className="btn-primary">新增使用者</button>
        </div>
      </div>

      {loading && <p className="text-slate-500">載入中...</p>}
      {error && <div className="bg-red-50 border border-red-200 text-red-700 p-3 rounded mb-4">{error}</div>}

      <div className="card overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-100 border-b">
            <tr>
              <th className="text-left px-4 py-2 font-medium">帳號</th>
              <th className="text-left px-4 py-2 font-medium w-28">角色</th>
              <th className="text-left px-4 py-2 font-medium w-24">狀態</th>
              <th className="text-left px-4 py-2 font-medium w-40">建立時間</th>
              <th className="text-right px-4 py-2 font-medium w-48">操作</th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id} className="border-b last:border-b-0">
                <td className="px-4 py-2 font-medium">{u.username}</td>
                <td className="px-4 py-2">
                  {u.is_superadmin ? (
                    <span className="badge bg-purple-100 text-purple-800">Superadmin</span>
                  ) : (
                    <span className="text-slate-500">一般</span>
                  )}
                </td>
                <td className="px-4 py-2">
                  {u.is_active ? (
                    <span className="badge bg-green-100 text-green-800">啟用</span>
                  ) : (
                    <span className="badge bg-slate-200 text-slate-700">停用</span>
                  )}
                </td>
                <td className="px-4 py-2 text-slate-500 text-xs">{formatDate(u.created_at)}</td>
                <td className="px-4 py-2 text-right">
                  <button onClick={() => resetPassword(u)} className="text-blue-600 hover:underline text-xs mr-3">
                    重設密碼
                  </button>
                  <button onClick={() => toggleActive(u)} className="text-amber-600 hover:underline text-xs">
                    {u.is_active ? '停用' : '啟用'}
                  </button>
                </td>
              </tr>
            ))}
            {users.length === 0 && !loading && (
              <tr><td colSpan={5} className="text-center text-slate-400 py-8">無使用者</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
