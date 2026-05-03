import { useEffect, useState } from 'react'
import { ShieldCheck } from 'lucide-react'
import { Card } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { ScrollArea } from '@/components/ui/scroll-area'
import { listAgents } from '@/api/endpoints/agents'
import * as userApi from '@/api/endpoints/users'
import { extractErrorMessage } from '@/api/client'
import { toast } from 'sonner'
import { formatDate } from '@/lib/format'
import { AgentRoleRow } from './AgentRoleRow'
import { UserDangerZone } from './UserDangerZone'
import type { Agent, User } from '@/api/types'

interface UserAgentRoleEntry { agent_id: string; role: 'editor' | 'reviewer' }

interface Props {
  user: User
  userRoles: UserAgentRoleEntry[]
  onChanged: () => void
}

export function UserDetailPanel({ user, userRoles, onChanged }: Props) {
  const [agents, setAgents] = useState<Agent[]>([])

  useEffect(() => {
    listAgents().then(setAgents).catch(() => setAgents([]))
  }, [])

  async function toggleActive(checked: boolean) {
    try {
      await userApi.updateUser(user.id, { is_active: checked })
      toast.success(checked ? '已啟用' : '已停用')
      onChanged()
    } catch (err) {
      toast.error(extractErrorMessage(err))
    }
  }

  function roleOf(agentId: string): 'editor' | 'reviewer' | 'none' {
    return userRoles.find((r) => r.agent_id === agentId)?.role ?? 'none'
  }

  return (
    <ScrollArea className="flex-1">
      <div className="p-6 space-y-6 max-w-2xl">
        <Card className="p-5 space-y-3">
          <h2 className="font-semibold flex items-center gap-2">
            {user.is_superadmin && <ShieldCheck className="w-4 h-4 text-purple-600" strokeWidth={1.5} />}
            基本資訊
          </h2>
          <Field label="帳號" value={user.username} />
          <Field label="角色" value={user.is_superadmin ? 'Superadmin' : '一般使用者'} />
          <Field label="建立時間" value={formatDate(user.created_at)} />
          <div className="flex items-center justify-between">
            <Label htmlFor="active">啟用狀態</Label>
            <Switch id="active" checked={user.is_active} onCheckedChange={toggleActive} disabled={user.is_superadmin} />
          </div>
        </Card>

        {!user.is_superadmin && (
          <Card className="p-5">
            <h2 className="font-semibold mb-3">各 Agent 角色</h2>
            {agents.length === 0 ? (
              <p className="text-sm text-text-muted">尚未建立任何 Agent</p>
            ) : (
              agents.map((a) => (
                <AgentRoleRow
                  key={a.id}
                  user_id={user.id}
                  agent={a}
                  currentRole={roleOf(a.id)}
                  onChanged={onChanged}
                />
              ))
            )}
          </Card>
        )}

        <UserDangerZone user={user} onChanged={onChanged} />
      </div>
    </ScrollArea>
  )
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between text-sm">
      <span className="text-text-secondary">{label}</span>
      <span className="font-medium">{value}</span>
    </div>
  )
}
