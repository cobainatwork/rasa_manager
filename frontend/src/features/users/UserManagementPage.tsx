import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Users, ArrowLeft } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { EmptyState } from '@/components/EmptyState'
import { UserListPanel } from './UserListPanel'
import { UserDetailPanel } from './UserDetailPanel'
import { useUserManagement } from './useUserManagement'

interface UserAgentRoleEntry { agent_id: string; role: 'editor' | 'reviewer' }

export function UserManagementPage() {
  const navigate = useNavigate()
  const { users, loading, selectedId, selected, select, reload } = useUserManagement()
  const [userRoles] = useState<UserAgentRoleEntry[]>([])

  useEffect(() => {
    // 若選中使用者變更，可在此 fetch userRoles
  }, [selectedId])

  return (
    <div className="min-h-screen bg-canvas flex flex-col">
      <header className="bg-surface border-b border-border-default px-6 py-3 flex items-center gap-3">
        <Button variant="ghost" size="icon" onClick={() => navigate('/agents')} aria-label="返回">
          <ArrowLeft className="w-4 h-4" strokeWidth={1.5} />
        </Button>
        <h1 className="font-semibold">使用者管理</h1>
      </header>

      <div className="flex-1 flex overflow-hidden">
        <UserListPanel
          users={users}
          loading={loading}
          selectedId={selectedId}
          onSelect={select}
          onUserCreated={reload}
        />

        <main className="flex-1 overflow-hidden">
          {selected ? (
            <UserDetailPanel user={selected} userRoles={userRoles} onChanged={reload} />
          ) : (
            <div className="h-full flex items-center justify-center">
              <EmptyState icon={Users} title="選擇一位使用者" description="從左側列表選一位使用者以檢視詳情" />
            </div>
          )}
        </main>
      </div>
    </div>
  )
}
