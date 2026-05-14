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
      <header className="h-11 bg-[#F2F2F7]/80 backdrop-blur-xl border-b border-black/[0.08] flex items-center px-4 gap-2 sticky top-0 z-sticky shrink-0">
        <Button variant="ghost" size="icon" className="w-7 h-7" onClick={() => navigate('/agents')} aria-label="返回">
          <ArrowLeft className="w-4 h-4" strokeWidth={1.5} />
        </Button>
        <span className="h-4 w-px bg-black/[0.12]" />
        <h1 className="font-medium text-[13px] text-text-primary">使用者管理</h1>
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
